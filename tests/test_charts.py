from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from analysis.aggregates import (
    compute_daily_totals,
    compute_hourly_profile,
    compute_modal_split,
)
from analysis.align import (
    compute_typical_week,
    compute_weekday_occurrence_totals,
    compute_weekday_totals,
    weekday_hour_matrix,
)
from analysis.filters import keep_assigned, label_periods
from analysis.trends import compute_daily_trend, weekday_adjusted_trend
from charts import (
    plot_daily_trend,
    plot_hourly_profile,
    plot_modal_split,
    plot_speed_distribution,
    plot_typical_week,
    plot_weekday_adjusted_trend,
    plot_weekday_comparison,
    plot_weekday_occurrence,
)
from charts.theme import register_template
from domain.models import Exclusion, PeriodInstance, PeriodKind

MODALITIES = ["pedestrian", "bike", "car", "heavy"]

register_template()


def _instances() -> list[PeriodInstance]:
    return [
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
    return keep_assigned(label_periods(df, _instances()))


def _assert_renders(fig):
    assert isinstance(fig, go.Figure)
    fig.to_plotly_json()


def test_all_charts_render(make_df):
    df = _labelled(make_df)
    instances = _instances()
    exclusions = [Exclusion("Roadworks", ((date(2026, 1, 12), date(2026, 1, 16)),))]

    daily = compute_daily_totals(df, MODALITIES)
    weekday_df = compute_weekday_totals(daily, MODALITIES)
    occurrence = compute_weekday_occurrence_totals(daily, ["car"])
    typical = compute_typical_week(df, MODALITIES)
    matrix = weekday_hour_matrix(typical, "Christmas", "car")

    speed_df = __import__("pandas").DataFrame(
        {
            "period_label": ["Christmas", "February half term"],
            "0-10": [30.0, 25.0],
            "10-20": [50.0, 55.0],
            "20+": [20.0, 20.0],
        }
    )

    _assert_renders(plot_hourly_profile(compute_hourly_profile(df, MODALITIES), MODALITIES))
    _assert_renders(plot_weekday_comparison(weekday_df, "car"))
    _assert_renders(plot_weekday_occurrence(occurrence, "car"))
    _assert_renders(plot_typical_week(matrix))
    _assert_renders(plot_modal_split(compute_modal_split(df, MODALITIES), MODALITIES))
    _assert_renders(plot_speed_distribution(speed_df))
    _assert_renders(
        plot_daily_trend(
            compute_daily_trend(df, MODALITIES),
            instances=instances,
            exclusions=exclusions,
        )
    )
    _assert_renders(
        plot_weekday_adjusted_trend(
            weekday_adjusted_trend(df, MODALITIES),
            instances=instances,
            exclusions=exclusions,
        )
    )
