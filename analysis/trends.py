"""Trend computations (pure: DataFrame in, DataFrame out)."""

from __future__ import annotations

import pandas as pd

from analysis.filters import add_time_columns


def daily_total_series(df: pd.DataFrame, modalities: list[str]) -> pd.Series:
    """Return a Series of daily totals (sum over hours) indexed by day."""
    if "day" not in df.columns:
        df = add_time_columns(df)
    daily = df.groupby("day")[modalities].sum()
    return daily.sum(axis=1).rename("total")


def rolling_mean(series: pd.Series, window: int = 7) -> pd.Series:
    """Trailing rolling mean with min_periods=1."""
    return series.rolling(window=window, min_periods=1).mean().rename("rolling")


def compute_daily_trend(
    df: pd.DataFrame, modalities: list[str], window: int = 7
) -> pd.DataFrame:
    """Daily totals plus a trailing rolling mean, indexed by day."""
    total = daily_total_series(df, modalities)
    trend = pd.DataFrame({"total": total})
    trend["rolling"] = rolling_mean(total, window)
    return trend.reset_index()


def weekday_adjusted_trend(
    df: pd.DataFrame, modalities: list[str], window: int = 28
) -> pd.DataFrame:
    """Removes the weekly cycle so underlying trends are visible.

    Each day is expressed as a residual from the mean of the same weekday
    across the whole series. A rolling mean of that residual is returned.
    """
    total = daily_total_series(df, modalities)
    frame = pd.DataFrame({"total": total})
    frame["weekday"] = frame.index.dayofweek
    frame["weekday_mean"] = frame.groupby("weekday")["total"].transform("mean")
    frame["residual"] = frame["total"] - frame["weekday_mean"]
    frame["rolling_residual"] = rolling_mean(frame["residual"], window)
    return frame.reset_index()
