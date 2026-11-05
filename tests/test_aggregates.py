from __future__ import annotations

import math
from datetime import date

import pandas as pd

from analysis.aggregates import (
    compute_daily_histogram,
    compute_daily_summary,
    compute_daily_totals,
    compute_modal_split,
    compute_period_totals,
    compute_speed_distribution,
    compute_speed_summary,
    compute_speed_trend,
    daily_value_series,
    period_mean_daily,
)
from analysis.filters import (
    DAY_TYPE_COL,
    add_day_type,
    add_time_columns,
    keep_assigned,
    label_periods,
)
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


def test_speed_summary_and_distribution_are_overall(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00", base=10.0)
    df["v85"] = 30.0
    df["car_speed_hist_0to120plus"] = [[50.0, 50.0]] * len(df)

    summary = compute_speed_summary(df, unit="mph")
    assert len(summary) == 1
    assert "V85 (mph)" in summary.columns
    assert "Days" in summary.columns

    dist = compute_speed_distribution(df, unit="km/h")
    assert len(dist) == 1
    assert math.isclose(dist.iloc[0].sum(), 100.0)


def test_speed_summary_reports_days_without_v85(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00", base=10.0)
    df["car_speed_hist_0to120plus"] = [[50.0, 50.0]] * len(df)

    summary = compute_speed_summary(df, unit="km/h")
    assert "Days" in summary.columns
    assert summary.iloc[0]["Days"] == 7


def test_speed_trend_is_daily_with_rolling_mean(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00")
    df["v85"] = range(len(df))

    trend = compute_speed_trend(df, unit="km/h", window=3)
    assert list(trend.columns) == ["day", "v85", "rolling"]
    assert len(trend) == 7
    assert trend["rolling"].notna().all()


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


def test_daily_histogram_counts_days_per_range(make_df):
    df = add_time_columns(make_df("2026-02-16", "2026-02-18 23:00", base=10.0))

    hist = compute_daily_histogram(df, "car", bin_width=100)

    assert list(hist.columns) == [
        "low",
        "high",
        "label",
        "days",
        "at_or_above",
    ]
    assert hist["label"].tolist() == ["0–99", "100–199", "200–299"]
    assert hist["days"].tolist() == [0, 0, 3]
    assert hist["at_or_above"].tolist() == [3, 3, 3]


def test_daily_value_series_sums_one_category_per_day(make_df):
    df = add_time_columns(make_df("2026-02-16", "2026-02-18 23:00", base=10.0))

    daily = daily_value_series(df, "car")

    assert len(daily) == 3
    assert (daily == 240.0).all()


def test_daily_histogram_is_empty_without_the_category(make_df):
    df = add_time_columns(make_df("2026-02-16", "2026-02-18 23:00"))

    hist = compute_daily_histogram(df, "night", bin_width=100)

    assert hist.empty
    assert list(hist.columns) == [
        "low",
        "high",
        "label",
        "days",
        "at_or_above",
    ]


def _weekday_weekend_frame(make_df):
    df = make_df(
        "2026-02-16",
        "2026-02-22 23:00",
        base=10.0,
        by_weekday={5: 2.0, 6: 2.0},
    )
    return add_day_type(df)


def test_daily_histogram_can_split_weekday_and_weekend(make_df):
    hist = compute_daily_histogram(
        _weekday_weekend_frame(make_df),
        "car",
        bin_width=100,
        group_col=DAY_TYPE_COL,
    )
    by_type = hist.set_index([DAY_TYPE_COL, "label"])

    assert by_type.loc[("Weekday", "200–299"), "days"] == 5
    assert by_type.loc[("Weekend", "400–499"), "days"] == 2
    assert by_type.loc[("Weekday", "200–299"), "at_or_above"] == 5
    assert by_type.loc[("Weekday", "300–399"), "at_or_above"] == 0
    assert by_type.loc[("Weekend", "400–499"), "at_or_above"] == 2


def test_grouped_outputs_order_weekday_before_weekend(make_df):
    # Start on Saturday: the first-seen group is Weekend, but categorical
    # order should still put Weekday first.
    df = add_day_type(make_df("2026-02-21", "2026-02-23 23:00", base=10.0))

    hist = compute_daily_histogram(
        df, "car", bin_width=100, group_col=DAY_TYPE_COL
    )
    summary = compute_daily_summary(df, "car", group_col=DAY_TYPE_COL)

    expected = ["Weekday", "Weekend"]
    assert list(dict.fromkeys(hist[DAY_TYPE_COL])) == expected
    assert summary[DAY_TYPE_COL].tolist() == expected


def test_daily_summary_splits_weekday_and_weekend(make_df):
    df = _weekday_weekend_frame(make_df)
    summary = compute_daily_summary(
        df, "car", group_col=DAY_TYPE_COL
    ).set_index(DAY_TYPE_COL)

    assert summary.loc["Weekday", "days"] == 5
    assert summary.loc["Weekday", "total"] == 1200.0
    assert summary.loc["Weekday", "median"] == 240.0
    assert summary.loc["Weekday", "std"] == 0.0
    assert summary.loc["Weekend", "days"] == 2
    assert summary.loc["Weekend", "total"] == 960.0
    assert summary.loc["Weekend", "median"] == 480.0
    assert summary.loc["Weekend", "std"] == 0.0

    overall = compute_daily_summary(df, "car").iloc[0]
    assert overall["days"] == 7
    assert overall["total"] == 2160.0
    assert overall["median"] == 240.0
    assert overall["std"] > 0


def test_daily_summary_reports_population_standard_deviation():
    df = pd.DataFrame(
        {
            "day": pd.date_range("2026-02-16", periods=3, freq="D", tz="UTC"),
            "car": [100.0, 200.0, 300.0],
        }
    )

    summary = compute_daily_summary(df, "car").iloc[0]

    assert summary["total"] == 600.0
    assert math.isclose(summary["std"], 81.6497, rel_tol=1e-4)
