from __future__ import annotations

from datetime import date

from analysis.pipeline import prepare_frame
from domain.models import (
    BASELINE_LABEL,
    EXCLUDED_LABEL,
    HOLIDAY_LABEL,
    TERM_LABEL,
    WEEKDAY_LABEL,
    WEEKEND_LABEL,
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
    FilterSettings,
    PeriodInstance,
    PeriodKind,
)


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


def _exclusions() -> list[Exclusion]:
    return [Exclusion("Roadworks", ((date(2026, 1, 12), date(2026, 1, 16)),))]


def test_prepare_frame_holiday_vs_term_drops_unlabelled(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    out = prepare_frame(
        df,
        FilterSettings(),
        [],
        _instances(),
        ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM),
        keep_only_assigned=True,
    )
    assert set(out["group_label"].unique()) == {TERM_LABEL, HOLIDAY_LABEL}
    assert out["group_label"].notna().all()


def test_prepare_frame_weekday_axis_keeps_every_row(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    out = prepare_frame(
        df,
        FilterSettings(),
        [],
        _instances(),
        ComparisonConfig(mode=ComparisonMode.WEEKDAY_VS_WEEKEND),
        keep_only_assigned=True,
    )
    assert set(out["group_label"].unique()) == {WEEKDAY_LABEL, WEEKEND_LABEL}
    assert len(out) == len(df)


def test_prepare_frame_roadworks_keeps_excluded_rows(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    out = prepare_frame(
        df,
        FilterSettings(),
        _exclusions(),
        [],
        ComparisonConfig(mode=ComparisonMode.ROADWORKS),
        keep_only_assigned=True,
    )
    assert set(out["group_label"].unique()) == {BASELINE_LABEL, EXCLUDED_LABEL}
    assert out["is_excluded"].any()


def test_prepare_frame_drops_excluded_rows_for_other_axes(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    out = prepare_frame(
        df,
        FilterSettings(),
        _exclusions(),
        _instances(),
        ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM),
    )
    assert not out["is_excluded"].any()
