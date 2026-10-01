from __future__ import annotations

from datetime import date

from analysis.aggregates import compute_daily_totals
from analysis.align import (
    compute_typical_week,
    compute_weekday_totals,
    weekday_hour_matrix,
)
from analysis.filters import keep_assigned, label_periods
from domain.models import PeriodInstance, PeriodKind

MODALITIES = ["pedestrian", "bike", "car", "heavy"]


def _labelled(make_df, by_weekday=None):
    instance = PeriodInstance(
        label="Test period",
        kind=PeriodKind.CUSTOM,
        ranges=((date(2026, 2, 16), date(2026, 3, 1)),),
    )
    df = make_df("2026-02-16", "2026-03-01 23:00", by_weekday=by_weekday)
    return keep_assigned(label_periods(df, [instance]))


def test_weekday_totals_covers_seven_days(make_df):
    df = _labelled(make_df)
    daily = compute_daily_totals(df, MODALITIES)
    weekday_df = compute_weekday_totals(daily, MODALITIES)
    assert sorted(weekday_df["weekday"].unique()) == list(range(7))


def test_weekday_alignment_reflects_weekday_multiplier(make_df):
    df = _labelled(make_df, by_weekday={5: 2.0, 6: 3.0})
    daily = compute_daily_totals(df, MODALITIES)
    weekday_df = compute_weekday_totals(daily, MODALITIES).set_index("weekday")

    monday = weekday_df.loc[0, "car"]
    saturday = weekday_df.loc[5, "car"]
    sunday = weekday_df.loc[6, "car"]
    assert saturday == monday * 2
    assert sunday == monday * 3


def test_typical_week_matrix_shape(make_df):
    df = _labelled(make_df)
    typical = compute_typical_week(df, MODALITIES)
    matrix = weekday_hour_matrix(typical, "Test period", "car")
    assert matrix.shape == (7, 24)
