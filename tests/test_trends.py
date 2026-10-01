from __future__ import annotations

import math

from analysis.trends import (
    compute_daily_trend,
    daily_total_series,
    rolling_mean,
    weekday_adjusted_trend,
)

MODALITIES = ["pedestrian", "bike", "car", "heavy"]


def test_rolling_mean_of_constant_is_constant():
    import pandas as pd

    series = pd.Series([10.0] * 10)
    assert list(rolling_mean(series, 7)) == [10.0] * 10


def test_daily_total_series_sums_modalities(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00", base=10.0)
    series = daily_total_series(df, MODALITIES)
    # 24 hours * (10 + 2 + 3 + 0.5) = 372
    assert math.isclose(series.iloc[0], 372.0)
    assert len(series) == 7


def test_daily_trend_has_expected_columns(make_df):
    df = make_df("2026-02-16", "2026-02-22 23:00")
    trend = compute_daily_trend(df, MODALITIES, window=3)
    assert list(trend.columns) == ["day", "total", "rolling"]
    assert len(trend) == 7


def test_weekday_adjusted_residual_is_zero_for_flat_series(make_df):
    df = make_df("2026-02-16", "2026-03-01 23:00", base=10.0)
    adjusted = weekday_adjusted_trend(df, MODALITIES)
    assert adjusted["residual"].abs().max() < 1e-9
