"""Weekday-aligned comparison helpers (pure: DataFrame in, DataFrame out).

The default comparison method is *weekday alignment*: like weekdays are
compared with like. A Mon–Fri half term has one of each weekday, while a
two-week Christmas holiday has two — so the primary output is the mean per
weekday, with an optional occurrence breakdown for long periods.
"""

from __future__ import annotations

import pandas as pd

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def compute_weekday_totals(
    daily_df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Mean daily total per (period, weekday) — the core comparison view.

    *daily_df* is the output of :func:`analysis.aggregates.compute_daily_totals`.
    """
    df = daily_df.copy()
    df["weekday"] = pd.to_datetime(df["day"]).dt.dayofweek
    return (
        df.groupby(["period_label", "weekday"])[modalities]
        .mean()
        .reset_index()
    )


def compute_weekday_occurrence_totals(
    daily_df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Mean daily total per (period, weekday, occurrence within period)."""
    df = daily_df.copy()
    df["weekday"] = pd.to_datetime(df["day"]).dt.dayofweek
    df = df.sort_values(["period_label", "weekday", "day"])
    df["weekday_occurrence"] = (
        df.groupby(["period_label", "weekday"]).cumcount() + 1
    )
    return (
        df.groupby(["period_label", "weekday", "weekday_occurrence"])[modalities]
        .mean()
        .reset_index()
    )


def compute_typical_week(
    df: pd.DataFrame, modalities: list[str]
) -> pd.DataFrame:
    """Mean count per (period, weekday, hour) — for typical-week heatmaps."""
    return (
        df.groupby(["period_label", "weekday", "hour"])[modalities]
        .mean()
        .reset_index()
    )


def weekday_hour_matrix(
    typical_week_df: pd.DataFrame, period_label: str, modality: str
) -> pd.DataFrame:
    """Pivot a typical week into a weekday × hour matrix for one period."""
    subset = typical_week_df[typical_week_df["period_label"] == period_label]
    matrix = subset.pivot_table(
        index="weekday", columns="hour", values=modality, aggfunc="mean"
    )
    matrix = matrix.reindex(range(7))
    matrix.index = [WEEKDAY_LABELS[d] for d in matrix.index]
    return matrix
