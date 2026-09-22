"""Aggregation functions (pure: DataFrame in, DataFrame out)."""

from __future__ import annotations

import json

import pandas as pd

from analysis.filters import get_speed_hist_columns

# ---------------------------------------------------------------------------
# Basic aggregations
# ---------------------------------------------------------------------------

def compute_hourly_profile(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Mean value per (period, hour of day) for each modality."""
    return (
        df.groupby(["period_label", "period_kind", "hour"])[modalities]
        .mean()
        .reset_index()
    )


def compute_daily_totals(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Sum per (period, day) for each modality."""
    return (
        df.groupby(["period_label", "day"])[modalities]
        .sum()
        .reset_index()
    )


def compute_modal_split(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Percentage share of each modality per period."""
    totals = df.groupby("period_label")[modalities].sum()
    row_sums = totals.sum(axis=1)
    percentages = totals.div(row_sums, axis=0) * 100
    return percentages.reset_index()


def compute_period_totals(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Total counts per period per modality, plus a combined total."""
    totals = df.groupby("period_label")[modalities].sum().reset_index()
    totals["total"] = totals[modalities].sum(axis=1)
    return totals


def period_mean_daily(
    df: pd.DataFrame, modalities: list[str]
) -> pd.Series:
    """Mean daily count per period, indexed by period label.

    Use this — not raw totals — to compare periods of different lengths
    (a one-week half term vs a six-week term), otherwise shorter periods
    always appear smaller.
    """
    daily = compute_daily_totals(df, modalities)
    if daily.empty:
        return pd.Series(dtype=float, name="mean_daily")
    daily = daily.assign(total=daily[modalities].sum(axis=1))
    return daily.groupby("period_label")["total"].mean().rename("mean_daily")


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


def compute_speed_distribution(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Parse speed histogram JSON strings and average per period.

    Returns a DataFrame with one column per speed bin, or None when no
    speed data is available. Both histograms use 5 km/h bins.
    """
    hist_col = get_speed_hist_columns(df)
    if hist_col is None:
        return None

    parsed = df[hist_col].apply(_parse_hist)
    valid = parsed.dropna()
    if valid.empty:
        return None

    max_bins = max(len(v) for v in valid)
    factor = 0.621371 if unit == "mph" else 1.0
    labels = []
    for i in range(max_bins - 1):
        lo = round(i * 5 * factor)
        hi = round((i + 1) * 5 * factor)
        labels.append(f"{lo}-{hi}")
    labels.append(f"{round((max_bins - 1) * 5 * factor)}+")

    expanded = pd.DataFrame(valid.tolist(), index=valid.index, columns=labels)
    expanded["period_label"] = df.loc[expanded.index, "period_label"]

    return expanded.groupby("period_label")[labels].mean().reset_index()


def compute_speed_summary(
    df: pd.DataFrame, unit: str = "mph"
) -> pd.DataFrame | None:
    """Compute V85 and estimated mean speed per period."""
    factor = 0.621371 if unit == "mph" else 1.0
    hist_col = get_speed_hist_columns(df)
    has_v85 = "v85" in df.columns
    if not has_v85 and hist_col is None:
        return None

    rows = []
    for label, group in df.groupby("period_label"):
        row: dict = {"period_label": label}

        if has_v85:
            v85_vals = pd.to_numeric(group["v85"], errors="coerce").dropna()
            if not v85_vals.empty:
                row[f"V85 ({unit})"] = round(v85_vals.mean() * factor, 1)

        if hist_col is not None:
            parsed = group[hist_col].apply(_parse_hist).dropna()
            if not parsed.empty:
                avg_hist = pd.DataFrame(parsed.tolist()).mean()
                n_bins = len(avg_hist)
                midpoints = [(i + 0.5) * 5 for i in range(n_bins - 1)] + [
                    (n_bins - 1) * 5
                ]
                mean_kmh = sum(m * p / 100 for m, p in zip(midpoints, avg_hist))
                row[f"Est. mean ({unit})"] = round(mean_kmh * factor, 1)

        rows.append(row)

    return pd.DataFrame(rows) if rows else None
