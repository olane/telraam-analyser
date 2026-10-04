"""Frame preparation: the pure pipeline shared by every view.

Kept out of the UI layer so it can be tested without Streamlit.
"""

from __future__ import annotations

import pandas as pd

from analysis.filters import (
    add_derived_modalities,
    filter_days_of_week,
    filter_time_of_day,
    label_periods,
    mark_exclusions,
)
from analysis.grouping import add_comparison_group
from domain.models import (
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
    FilterSettings,
    PeriodInstance,
)


def prepare_frame(
    df: pd.DataFrame,
    filters: FilterSettings,
    exclusions: list[Exclusion],
    instances: list[PeriodInstance],
    comparison: ComparisonConfig,
    keep_only_assigned: bool = False,
) -> pd.DataFrame:
    """Apply exclusions, filters, period labels and the comparison group.

    The roadworks axis keeps excluded rows (flagging them) so they can be
    compared against the baseline; every other axis drops them.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = add_derived_modalities(df)
    df = mark_exclusions(df, exclusions)
    if comparison.mode is not ComparisonMode.ROADWORKS:
        df = df[~df["is_excluded"].astype(bool)]

    df = filter_time_of_day(df, filters.start_hour, filters.end_hour)
    df = filter_days_of_week(df, filters.selected_days)
    df = label_periods(df, instances)
    df = add_comparison_group(df, comparison)

    if keep_only_assigned:
        df = df[df["group_label"].notna()].copy()
    return df
