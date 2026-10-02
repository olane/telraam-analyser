from __future__ import annotations

from datetime import date

from analysis.aggregates import compute_daily_totals
from analysis.align import compute_weekday_totals
from analysis.filters import label_periods, mark_exclusions
from analysis.grouping import add_comparison_group
from domain.models import (
    BASELINE_LABEL,
    EXCLUDED_LABEL,
    HOLIDAY_LABEL,
    TERM_LABEL,
    TIME_OF_DAY_BANDS,
    WEEKDAY_LABEL,
    WEEKEND_LABEL,
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
    PeriodInstance,
    PeriodKind,
)

MODALITIES = ["pedestrian", "bike", "car", "heavy"]


def _instances() -> list[PeriodInstance]:
    return [
        PeriodInstance(
            "Spring term", PeriodKind.TERM,
            ((date(2026, 1, 5), date(2026, 1, 30)),),
        ),
        PeriodInstance(
            "Christmas", PeriodKind.CHRISTMAS,
            ((date(2025, 12, 22), date(2026, 1, 2)),),
        ),
        PeriodInstance(
            "February half term", PeriodKind.FEB_HALF,
            ((date(2026, 2, 16), date(2026, 2, 22)),),
        ),
    ]


def _labelled(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    return label_periods(df, _instances())


def test_holiday_vs_term_axis(make_df):
    df = _labelled(make_df)
    grouped = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM)
    )
    assert set(grouped["group_label"].dropna().unique()) == {
        TERM_LABEL,
        HOLIDAY_LABEL,
    }
    # Rows outside every period are left unlabelled.
    assert grouped["group_label"].isna().any()


def test_weekday_vs_weekend_axis_covers_every_row(make_df):
    df = _labelled(make_df)
    grouped = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.WEEKDAY_VS_WEEKEND)
    )
    assert set(grouped["group_label"].unique()) == {WEEKDAY_LABEL, WEEKEND_LABEL}
    assert not grouped["group_label"].isna().any()


def test_time_of_day_axis_uses_ordered_bands(make_df):
    df = _labelled(make_df)
    grouped = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.TIME_OF_DAY)
    )
    order = [label for label, _, _ in TIME_OF_DAY_BANDS]
    assert list(grouped["group_label"].cat.categories) == order
    assert set(grouped["group_label"].unique()) == set(order)


def test_roadworks_axis_splits_baseline_and_excluded(make_df):
    df = _labelled(make_df)
    exclusions = [
        Exclusion("Roadworks", ((date(2026, 1, 12), date(2026, 1, 16)),))
    ]
    marked = mark_exclusions(df, exclusions)
    grouped = add_comparison_group(
        marked, ComparisonConfig(mode=ComparisonMode.ROADWORKS)
    )
    assert set(grouped["group_label"].unique()) == {
        BASELINE_LABEL,
        EXCLUDED_LABEL,
    }


def test_group_col_preserves_category_order(make_df):
    df = _labelled(make_df)
    grouped = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM)
    )
    daily = compute_daily_totals(grouped, MODALITIES, group_col="group_label")
    weekday = compute_weekday_totals(
        daily, MODALITIES, group_col="group_label"
    )
    assert list(dict.fromkeys(weekday["group_label"])) == [
        TERM_LABEL,
        HOLIDAY_LABEL,
    ]
