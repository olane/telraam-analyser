"""Weekday-aligned comparison helpers (pure: DataFrame in, DataFrame out).

The default comparison method is *weekday alignment*: like weekdays are
compared with like. A Mon–Fri half term has one of each weekday, while a
two-week Christmas holiday has two — so the primary output is the mean per
weekday.
"""

from __future__ import annotations

import pandas as pd

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def compute_weekday_totals(
    daily_df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Mean daily total per (group, weekday) — the core comparison view.

    *daily_df* is the output of :func:`analysis.aggregates.compute_daily_totals`.
    """
    df = daily_df.copy()
    df["weekday"] = pd.to_datetime(df["day"]).dt.dayofweek
    return (
        df.groupby([group_col, "weekday"], observed=True)[modalities]
        .mean()
        .reset_index()
    )


def compute_typical_week(
    df: pd.DataFrame, modalities: list[str], group_col: str = "period_label"
) -> pd.DataFrame:
    """Mean count per (group, weekday, hour) — for typical-week heatmaps."""
    return (
        df.groupby([group_col, "weekday", "hour"], observed=True)[modalities]
        .mean()
        .reset_index()
    )


def weekday_hour_matrix(
    typical_week_df: pd.DataFrame,
    group: str,
    modality: str,
    group_col: str = "period_label",
) -> pd.DataFrame:
    """Pivot a typical week into a weekday × hour matrix for one group."""
    subset = typical_week_df[typical_week_df[group_col] == group]
    matrix = subset.pivot_table(
        index="weekday", columns="hour", values=modality, aggfunc="mean"
    )
    matrix = matrix.reindex(range(7))
    matrix.index = [WEEKDAY_LABELS[d] for d in matrix.index]
    return matrix
