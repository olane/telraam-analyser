"""Comparison grouping (pure: DataFrame in, DataFrame out).

The comparison charts group rows by a single categorical ``group_label``
column rather than by every individual period. This module builds that column
from the chosen :class:`~domain.models.ComparisonMode`.
"""

from __future__ import annotations

import pandas as pd

from domain.models import (
    BASELINE_LABEL,
    EXCLUDED_LABEL,
    HOLIDAY_KINDS,
    HOLIDAY_LABEL,
    NOT_TERM_LABEL,
    TERM_LABEL,
    TIME_OF_DAY_BANDS,
    WEEKDAY_LABEL,
    WEEKEND_LABEL,
    ComparisonConfig,
    ComparisonMode,
    PeriodKind,
    time_of_day_band,
)

_HOLIDAY_VALUES = {kind.value for kind in HOLIDAY_KINDS}
_BEFORE_AFTER_ORDER = (
    "Before intervention",
    "After intervention",
    "Same window, previous year",
)


def _holiday_vs_term(df: pd.DataFrame) -> pd.Categorical:
    def classify(kind: object) -> str | None:
        if kind == PeriodKind.TERM.value:
            return TERM_LABEL
        if kind in _HOLIDAY_VALUES:
            return HOLIDAY_LABEL
        return None

    return pd.Categorical(
        df["period_kind"].map(classify),
        categories=[TERM_LABEL, HOLIDAY_LABEL],
        ordered=True,
    )


def term_status(df: pd.DataFrame) -> pd.Categorical:
    """Label every row as term time or not, from the period kind."""
    labels = df["period_kind"].map(
        lambda kind: TERM_LABEL if kind == PeriodKind.TERM.value else NOT_TERM_LABEL
    )
    return pd.Categorical(
        labels, categories=[TERM_LABEL, NOT_TERM_LABEL], ordered=True
    )


def _year_on_year(df: pd.DataFrame) -> pd.Categorical:
    years = sorted(df["academic_year"].dropna().unique())
    return pd.Categorical(df["academic_year"], categories=years, ordered=True)


def _before_after(df: pd.DataFrame) -> pd.Categorical:
    present = list(dict.fromkeys(df["period_label"].dropna()))
    order = [label for label in _BEFORE_AFTER_ORDER if label in present]
    order += [label for label in present if label not in order]
    return pd.Categorical(df["period_label"], categories=order, ordered=True)


def _weekday_vs_weekend(df: pd.DataFrame) -> pd.Categorical:
    labels = df["weekday"].map(
        lambda day: WEEKEND_LABEL if day >= 5 else WEEKDAY_LABEL
    )
    return pd.Categorical(
        labels, categories=[WEEKDAY_LABEL, WEEKEND_LABEL], ordered=True
    )


def _time_of_day(df: pd.DataFrame) -> pd.Categorical:
    order = [label for label, _, _ in TIME_OF_DAY_BANDS]
    return pd.Categorical(
        df["hour"].map(time_of_day_band), categories=order, ordered=True
    )


def _roadworks(df: pd.DataFrame) -> pd.Categorical:
    labels = df["is_excluded"].map(
        lambda excluded: EXCLUDED_LABEL if bool(excluded) else BASELINE_LABEL
    )
    return pd.Categorical(
        labels, categories=[BASELINE_LABEL, EXCLUDED_LABEL], ordered=True
    )


def _custom(df: pd.DataFrame, config: ComparisonConfig) -> pd.Categorical:
    present = set(df["period_label"].dropna())
    order = [label for label in config.period_labels if label in present]
    order += [label for label in dict.fromkeys(df["period_label"].dropna()) if label not in order]
    return pd.Categorical(df["period_label"], categories=order, ordered=True)


def add_comparison_group(
    df: pd.DataFrame, config: ComparisonConfig
) -> pd.DataFrame:
    """Add an ordered categorical ``group_label`` column for the chosen axis."""
    df = df.copy()
    mode = config.mode
    if mode is ComparisonMode.HOLIDAY_VS_TERM:
        df["group_label"] = _holiday_vs_term(df)
    elif mode is ComparisonMode.YEAR_ON_YEAR:
        df["group_label"] = _year_on_year(df)
    elif mode is ComparisonMode.BEFORE_AFTER:
        df["group_label"] = _before_after(df)
    elif mode is ComparisonMode.WEEKDAY_VS_WEEKEND:
        df["group_label"] = _weekday_vs_weekend(df)
    elif mode is ComparisonMode.TIME_OF_DAY:
        df["group_label"] = _time_of_day(df)
    elif mode is ComparisonMode.ROADWORKS:
        df["group_label"] = _roadworks(df)
    else:  # CUSTOM
        df["group_label"] = _custom(df, config)
    return df
