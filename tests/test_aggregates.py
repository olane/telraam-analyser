from __future__ import annotations

import math
from datetime import date

from analysis.aggregates import (
    compute_daily_totals,
    compute_modal_split,
    compute_period_totals,
    period_mean_daily,
)
from analysis.filters import keep_assigned, label_periods
from domain.models import PeriodInstance, PeriodKind

MODALITIES = ["pedestrian", "bike", "car", "heavy"]


def _fortnight() -> PeriodInstance:
    return PeriodInstance(
        label="Test period",
        kind=PeriodKind.CUSTOM,
        ranges=((date(2026, 2, 16), date(2026, 3, 1)),),
    )


def _labelled(make_df):
    df = make_df("2026-02-16", "2026-03-01 23:00", base=10.0)
    return keep_assigned(label_periods(df, [_fortnight()]))


def test_daily_totals_sum_hours(make_df):
    df = _labelled(make_df)
    daily = compute_daily_totals(df, MODALITIES)
    first = daily.iloc[0]
    assert math.isclose(first["car"], 240.0)
    assert math.isclose(first["heavy"], 12.0)


def test_modal_split_sums_to_100(make_df):
    df = _labelled(make_df)
    split = compute_modal_split(df, MODALITIES)
    assert len(split) == 1
    row = split.iloc[0]
    assert math.isclose(sum(row[m] for m in MODALITIES), 100.0)
    assert math.isclose(row["car"], 10 / 15.5 * 100, rel_tol=1e-6)


def test_period_totals_adds_total(make_df):
    df = _labelled(make_df)
    totals = compute_period_totals(df, MODALITIES)
    row = totals.iloc[0]
    expected = sum(row[m] for m in MODALITIES)
    assert math.isclose(row["total"], expected)


def test_period_mean_daily_ignores_period_length(make_df):
    short = PeriodInstance(
        "Short", PeriodKind.CUSTOM, ((date(2026, 2, 16), date(2026, 2, 20)),)
    )
    long = PeriodInstance(
        "Long", PeriodKind.CUSTOM, ((date(2026, 3, 2), date(2026, 3, 27)),)
    )
    df = make_df("2026-02-16", "2026-03-27 23:00", base=10.0)
    labelled = keep_assigned(label_periods(df, [short, long]))

    means = period_mean_daily(labelled, MODALITIES)
    assert math.isclose(means["Short"], means["Long"])

    totals = compute_period_totals(labelled, MODALITIES).set_index("period_label")
    assert totals.loc["Short", "total"] < totals.loc["Long", "total"]
