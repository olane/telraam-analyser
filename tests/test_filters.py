from __future__ import annotations

from datetime import date

import pandas as pd

from analysis.filters import (
    add_weekday_occurrence,
    drop_exclusions,
    filter_days_of_week,
    filter_time_of_day,
    keep_assigned,
    label_periods,
)
from domain.models import Exclusion, PeriodInstance, PeriodKind


def _christmas() -> PeriodInstance:
    return PeriodInstance(
        label="Christmas 2025-26",
        kind=PeriodKind.CHRISTMAS,
        ranges=((date(2025, 12, 22), date(2026, 1, 2)),),
        academic_year="2025-26",
    )


def test_label_periods_marks_inside_and_outside(make_df):
    df = make_df("2025-12-20", "2026-01-05 23:00")
    labelled = label_periods(df, [_christmas()])

    inside = labelled.loc["2025-12-24 12:00"]
    assert inside["period_label"] == "Christmas 2025-26"
    assert inside["period_kind"] == PeriodKind.CHRISTMAS.value

    outside = labelled.loc["2025-12-20 12:00"]
    assert pd.isna(outside["period_label"])


def test_keep_assigned_drops_unlabelled(make_df):
    df = make_df("2025-12-20", "2026-01-05 23:00")
    labelled = keep_assigned(label_periods(df, [_christmas()]))
    assert labelled["period_label"].notna().all()
    assert labelled.index.min().date() >= date(2025, 12, 22)
    assert labelled.index.max().date() <= date(2026, 1, 2)


def test_drop_exclusions_removes_range(make_df):
    df = make_df("2025-12-20", "2026-01-05 23:00")
    exclusion = Exclusion("Roadworks", ((date(2025, 12, 24), date(2025, 12, 25)),))
    filtered = drop_exclusions(df, [exclusion])
    assert filtered.loc["2025-12-24"].empty
    assert filtered.loc["2025-12-23"].shape[0] == 24


def test_time_and_day_filters(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00")
    daytime = filter_time_of_day(df, 7, 9)
    assert set(daytime["hour"].unique()) == {7, 8, 9}

    weekdays = filter_days_of_week(df, [0, 1, 2, 3, 4])
    assert set(weekdays["weekday"].unique()) <= {0, 1, 2, 3, 4}


def test_weekday_occurrence_counts_second_monday(make_df):
    df = make_df("2025-12-22", "2026-01-02 23:00")
    labelled = label_periods(df, [_christmas()])
    with_occurrence = add_weekday_occurrence(labelled)

    mondays = with_occurrence[with_occurrence["weekday"] == 0]
    occurrences = sorted(mondays["weekday_occurrence"].unique())
    assert occurrences == [1, 2]
