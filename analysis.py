"""Pure pandas functions for filtering and aggregating traffic data.

Every function here takes a DataFrame and returns a new DataFrame — no I/O.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from models import CLASSIC_MODALITIES, PeriodGroup


# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def get_available_modalities(df: pd.DataFrame) -> list[str]:
    """Return modality columns present in *df*, preserving a sensible order."""
    ordered = [
        "pedestrian", "bike", "car", "heavy",
        "pedestrian_lft", "pedestrian_rgt",
        "bike_lft", "bike_rgt",
        "car_lft", "car_rgt",
        "heavy_lft", "heavy_rgt",
    ]
    return [m for m in ordered if m in df.columns]


def get_speed_hist_columns(df: pd.DataFrame) -> list[str] | None:
    """Return the speed histogram column name if present, else None."""
    for col in ("car_speed_hist_0to120plus", "car_speed_hist_0to70plus"):
        if col in df.columns:
            return col  # type: ignore[return-value]
    return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_time_of_day(
    df: pd.DataFrame, start_hour: int, end_hour: int
) -> pd.DataFrame:
    """Keep only rows whose hour falls within [start_hour, end_hour]."""
    hours = df.index.hour
    return df[(hours >= start_hour) & (hours <= end_hour)]


def filter_days_of_week(df: pd.DataFrame, days: list[int]) -> pd.DataFrame:
    """Keep only rows whose weekday is in *days* (0=Monday … 6=Sunday)."""
    return df[df.index.dayofweek.isin(days)]


def assign_period_groups(
    df: pd.DataFrame, groups: list[PeriodGroup]
) -> pd.DataFrame:
    """Add a ``period_group`` column; rows outside all groups are dropped."""
    df = df.copy()
    df["period_group"] = None

    for group in groups:
        for range_start, range_end in group.ranges:
            start_ts = pd.Timestamp(range_start, tz="UTC")
            # Include the full end day
            end_ts = pd.Timestamp(range_end, tz="UTC") + pd.Timedelta(
                hours=23, minutes=59, seconds=59
            )
            mask = (df.index >= start_ts) & (df.index <= end_ts)
            df.loc[mask, "period_group"] = group.name

    return df[df["period_group"].notna()]


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def compute_hourly_profile(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Mean value per (period_group, hour_of_day) for each modality."""
    df = df.copy()
    df["hour"] = df.index.hour
    return (
        df.groupby(["period_group", "hour"])[modalities]
        .mean()
        .reset_index()
    )


def compute_daily_totals(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Sum per (period_group, day) for each modality."""
    df = df.copy()
    df["day"] = df.index.date
    return (
        df.groupby(["period_group", "day"])[modalities]
        .sum()
        .reset_index()
    )


def compute_modal_split(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Percentage share of each modality per period group."""
    totals = df.groupby("period_group")[modalities].sum()
    row_sums = totals.sum(axis=1)
    percentages = totals.div(row_sums, axis=0) * 100
    return percentages.reset_index()


def compute_speed_distribution(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Parse speed histogram JSON strings and average per period group.

    Speed histogram columns contain JSON-like lists of percentages for
    each speed bin. Returns a DataFrame with columns for each bin, or
    None if no speed data is available.

    *unit*: ``"mph"`` or ``"km/h"``
    """
    hist_col = get_speed_hist_columns(df)
    if hist_col is None:
        return None

    import json

    def parse_hist(val):
        if isinstance(val, list):
            return val
        if hasattr(val, "tolist"):  # numpy array
            return val.tolist()
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    df = df.copy()
    parsed = df[hist_col].apply(parse_hist)
    valid = parsed.dropna()
    if valid.empty:
        return None

    # Expand lists into columns
    # 0to70plus uses 5 km/h bins; 0to120plus uses 10 km/h bins
    max_bins = max(len(v) for v in valid)
    step_kmh = 5 if "0to70plus" in hist_col else 10
    if unit == "mph":
        factor = 0.621371
    else:
        factor = 1.0
    labels = []
    for i in range(max_bins - 1):
        lo = round(i * step_kmh * factor)
        hi = round((i + 1) * step_kmh * factor)
        labels.append(f"{lo}-{hi}")
    labels.append(f"{round((max_bins - 1) * step_kmh * factor)}+")

    expanded = pd.DataFrame(valid.tolist(), index=valid.index, columns=labels)
    expanded["period_group"] = df.loc[expanded.index, "period_group"]

    return expanded.groupby("period_group")[labels].mean().reset_index()


def compute_speed_summary(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Compute V85 and estimated mean speed per period group.

    Uses the ``v85`` column if available, and estimates mean speed from
    the speed histogram bins.
    """
    KMH_TO_MPH = 0.621371
    factor = KMH_TO_MPH if unit == "mph" else 1.0

    hist_col = get_speed_hist_columns(df)
    has_v85 = "v85" in df.columns
    if not has_v85 and hist_col is None:
        return None

    rows = []
    for group_name, gdf in df.groupby("period_group"):
        row: dict = {"period_group": group_name}

        if has_v85:
            v85_vals = pd.to_numeric(gdf["v85"], errors="coerce").dropna()
            if not v85_vals.empty:
                row[f"V85 ({unit})"] = round(v85_vals.mean() * factor, 1)

        if hist_col is not None:
            import json

            def _parse(val):
                if isinstance(val, list):
                    return val
                if hasattr(val, "tolist"):  # numpy array
                    return val.tolist()
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        return None
                return None

            parsed = gdf[hist_col].apply(_parse).dropna()
            if not parsed.empty:
                step_kmh = 5 if "0to70plus" in hist_col else 10
                # Estimate mean from bin midpoints
                avg_hist = pd.DataFrame(parsed.tolist()).mean()
                n_bins = len(avg_hist)
                midpoints = [
                    (i + 0.5) * step_kmh for i in range(n_bins - 1)
                ] + [(n_bins - 1) * step_kmh]  # last bin: use lower bound
                mean_kmh = sum(m * p / 100 for m, p in zip(midpoints, avg_hist))
                row[f"Est. mean ({unit})"] = round(mean_kmh * factor, 1)

        rows.append(row)

    if not rows:
        return None
    return pd.DataFrame(rows)
