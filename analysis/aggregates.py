"""Aggregation functions (pure: DataFrame in, DataFrame out)."""

from __future__ import annotations

import json

import pandas as pd

from analysis.filters import add_time_columns, get_speed_hist_columns

# ---------------------------------------------------------------------------
# Basic aggregations
# ---------------------------------------------------------------------------

def compute_hourly_profile(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Mean value per (group, hour of day) for each modality."""
    return (
        df.groupby([group_col, "hour"], observed=True)[modalities]
        .mean()
        .reset_index()
    )


def compute_daily_totals(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Sum per (group, day) for each modality."""
    return (
        df.groupby([group_col, "day"], observed=True)[modalities]
        .sum()
        .reset_index()
    )


def compute_modal_split(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Percentage share of each modality per comparison group."""
    totals = df.groupby(group_col, observed=True)[modalities].sum()
    row_sums = totals.sum(axis=1)
    percentages = totals.div(row_sums, axis=0) * 100
    return percentages.reset_index()


def compute_period_totals(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Total counts per group per modality, plus a combined total."""
    totals = df.groupby(group_col, observed=True)[modalities].sum().reset_index()
    totals["total"] = totals[modalities].sum(axis=1)
    return totals


def period_mean_daily(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.Series:
    """Mean daily count per group, indexed by the group label.

    Use this — not raw totals — to compare periods of different lengths
    (a one-week half term vs a six-week term), otherwise shorter periods
    always appear smaller.
    """
    daily = compute_daily_totals(df, modalities, group_col=group_col)
    if daily.empty:
        return pd.Series(dtype=float, name="mean_daily")
    daily = daily.assign(total=daily[modalities].sum(axis=1))
    return daily.groupby(group_col, observed=True)["total"].mean().rename("mean_daily")


def compute_daily_values(
    df: pd.DataFrame, modality: str, group_col: str | None = None
) -> pd.DataFrame:
    """One row per day (or per group and day) with a single daily total."""
    columns = ([group_col] if group_col else []) + ["day", modality]
    if df is None or df.empty or modality not in df.columns:
        return pd.DataFrame(columns=columns)
    if "day" not in df.columns:
        df = add_time_columns(df)
    keys = [group_col, "day"] if group_col else ["day"]
    daily = df.groupby(keys, observed=True)[modality].sum().reset_index()
    return daily.dropna(subset=[modality])


def daily_value_series(df: pd.DataFrame, modality: str) -> pd.Series:
    """Total of one column per day, indexed by day."""
    daily = compute_daily_values(df, modality)
    if daily.empty:
        return pd.Series(dtype=float, name=modality)
    return daily.set_index("day")[modality].rename(modality)


_HISTOGRAM_COLUMNS = ["low", "high", "label", "days", "at_or_above"]


def _histogram_rows(binned: pd.Series) -> list[dict]:
    counts = binned.value_counts(sort=False)
    rows = []
    for interval in binned.cat.categories:
        low = int(interval.left)
        high = int(interval.right) - 1
        rows.append(
            {
                "low": low,
                "high": high,
                "label": f"{low:,}–{high:,}",
                "days": int(counts.get(interval, 0)),
            }
        )

    total = 0
    for row in reversed(rows):
        total += row["days"]
        row["at_or_above"] = total
    return rows


def compute_daily_histogram(
    df: pd.DataFrame,
    modality: str,
    bin_width: int = 100,
    group_col: str | None = None,
) -> pd.DataFrame:
    """Count days whose daily total falls into each fixed-width range.

    Bins always start at zero, so labels read as ranges of counts (for
    example ``200–299``) rather than arbitrary boundaries. Empty bins are
    kept so the shape of the distribution is visible. When *group_col* is
    given, every group shares the same bins so the counts are comparable.
    """
    if bin_width <= 0:
        raise ValueError("bin_width must be positive")

    daily = compute_daily_values(df, modality, group_col=group_col)
    columns = ([group_col] if group_col else []) + _HISTOGRAM_COLUMNS
    if daily.empty:
        return pd.DataFrame(columns=columns)

    # Make the last edge strictly above the busiest day so every value falls
    # into a [low, high) bin.
    upper = (int(daily[modality].max()) // bin_width + 1) * bin_width
    edges = list(range(0, upper + 1, bin_width))

    if group_col:
        rows = []
        for group, subset in daily.groupby(group_col, observed=True, sort=False):
            binned = pd.cut(
                subset[modality], bins=edges, right=False, include_lowest=True
            )
            rows.extend({group_col: group, **row} for row in _histogram_rows(binned))
        return pd.DataFrame(rows, columns=columns)

    binned = pd.cut(
        daily[modality], bins=edges, right=False, include_lowest=True
    )
    return pd.DataFrame(_histogram_rows(binned), columns=columns)


_DAILY_SUMMARY_COLUMNS = ["days", "median", "mean", "std"]


def compute_daily_summary(
    df: pd.DataFrame,
    modality: str,
    group_col: str | None = None,
) -> pd.DataFrame:
    """Day counts, typical daily levels and their spread, optionally per group.

    The standard deviation treats the selected days as the full population.
    """
    daily = compute_daily_values(df, modality, group_col=group_col)
    columns = ([group_col] if group_col else []) + _DAILY_SUMMARY_COLUMNS
    if daily.empty:
        return pd.DataFrame(columns=columns)

    def stats(values: pd.Series) -> dict:
        return {
            "days": int(values.size),
            "median": float(values.median()),
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
        }

    if group_col:
        rows = []
        for group, subset in daily.groupby(group_col, observed=True, sort=False):
            rows.append({group_col: group, **stats(subset[modality])})
        return pd.DataFrame(rows, columns=columns)

    return pd.DataFrame([stats(daily[modality])], columns=columns)


# ---------------------------------------------------------------------------
# Speed
# ---------------------------------------------------------------------------

def _parse_hist(value):
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):  # numpy array
        return value.tolist()
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _speed_bins(
    df: pd.DataFrame, unit: str
) -> tuple[pd.DataFrame, list[str]] | tuple[None, None]:
    """Expand the speed histogram into one column per bin, with labels."""
    hist_col = get_speed_hist_columns(df)
    if hist_col is None:
        return None, None

    parsed = df[hist_col].apply(_parse_hist)
    valid = parsed.dropna()
    if valid.empty:
        return None, None

    max_bins = max(len(v) for v in valid)
    factor = 0.621371 if unit == "mph" else 1.0
    labels = []
    for i in range(max_bins - 1):
        lo = round(i * 5 * factor)
        hi = round((i + 1) * 5 * factor)
        labels.append(f"{lo}-{hi}")
    labels.append(f"{round((max_bins - 1) * 5 * factor)}+")

    expanded = pd.DataFrame(valid.tolist(), index=valid.index, columns=labels)
    return expanded, labels


def compute_speed_distribution(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Average speed-bin shares across the whole selection.

    Returns a single-row DataFrame with one column per speed bin, or None
    when no speed data is available. Both histograms use 5 km/h bins.
    """
    expanded, labels = _speed_bins(df, unit)
    if expanded is None:
        return None
    return pd.DataFrame([expanded[labels].mean().to_dict()])


def compute_speed_summary(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Compute the overall V85 and estimated mean speed for the selection."""
    factor = 0.621371 if unit == "mph" else 1.0
    hist_col = get_speed_hist_columns(df)
    has_v85 = "v85" in df.columns
    if not has_v85 and hist_col is None:
        return None

    row: dict = {}

    if has_v85:
        v85_vals = pd.to_numeric(df["v85"], errors="coerce").dropna()
        if not v85_vals.empty:
            row[f"V85 ({unit})"] = round(v85_vals.mean() * factor, 1)

    if hist_col is not None:
        parsed = df[hist_col].apply(_parse_hist).dropna()
        if not parsed.empty:
            avg_hist = pd.DataFrame(parsed.tolist()).mean()
            n_bins = len(avg_hist)
            midpoints = [(i + 0.5) * 5 for i in range(n_bins - 1)] + [
                (n_bins - 1) * 5
            ]
            mean_kmh = sum(m * p / 100 for m, p in zip(midpoints, avg_hist))
            row[f"Est. mean ({unit})"] = round(mean_kmh * factor, 1)

    if not row:
        return None
    days_source = "v85" if has_v85 else hist_col
    row["Days"] = int(
        df[days_source].notna().groupby(df.index.normalize()).any().sum()
    )
    return pd.DataFrame([row])


def compute_speed_trend(
    df: pd.DataFrame, unit: str = "mph", window: int = 7
) -> pd.DataFrame | None:
    """Daily mean V85 plus a trailing rolling mean, indexed by day.

    Returns None when the frame has no ``v85`` column or no valid values.
    """
    if "v85" not in df.columns:
        return None

    factor = 0.621371 if unit == "mph" else 1.0
    values = pd.to_numeric(df["v85"], errors="coerce").dropna()
    if values.empty:
        return None

    daily = values.groupby(values.index.normalize()).mean() * factor
    trend = daily.rename("v85").to_frame()
    trend["rolling"] = trend["v85"].rolling(window, min_periods=1).mean()
    return trend.reset_index(names="day")
