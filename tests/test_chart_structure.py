"""Structural regression tests for the Plotly figures.

These assert the *shape* of the real chart output — trace counts, weekday
coverage, band types and heatmap dimensions — rather than pixels. This catches
regressions such as every period being shaded on the trend (which should only
happen for holidays), without brittle image snapshots.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
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
from analysis.trends import compute_daily_trend
from charts import (
    empty_figure,
    plot_daily_trend,
    plot_hourly_profile,
    plot_modal_split,
    plot_speed_distribution,
    plot_typical_week,
    plot_weekday_comparison,
    plot_weekday_occurrence,
)
from domain.calendars import default_calendar
from domain.models import Exclusion, PeriodInstance, PeriodKind

MODALITIES = ["pedestrian", "bike", "car", "heavy"]
CALENDAR = default_calendar()


def _two_periods() -> list[PeriodInstance]:
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
    df = make_df("2025-09-01", "2026-03-31 23:00")
    return keep_assigned(label_periods(df, _two_periods()))


def _shapes(fig: go.Figure, shape_type: str) -> list:
    return [s for s in (fig.layout.shapes or []) if s.type == shape_type]


# ---------------------------------------------------------------------------
# Trend bands
# ---------------------------------------------------------------------------

def test_terms_are_boundary_lines_and_holidays_are_bands(make_df):
    df = make_df("2025-09-01", "2026-07-20 23:00")
    trend = compute_daily_trend(df, MODALITIES)
    exclusion = Exclusion("Roadworks", ((date(2025, 10, 13), date(2025, 10, 17)),))

    fig = plot_daily_trend(
        trend,
        instances=CALENDAR.instances,
        exclusions=[exclusion],
    )

    holiday_ranges = sum(
        len(i.ranges) for i in CALENDAR.instances if i.kind.is_holiday
    )
    term_ranges = sum(
        len(i.ranges) for i in CALENDAR.instances if i.kind.is_term
    )

    # One rectangle per holiday range, plus one per exclusion; terms are lines.
    assert len(_shapes(fig, "rect")) == holiday_ranges + 1
    assert len(_shapes(fig, "line")) == term_ranges
    assert term_ranges > 0 and holiday_ranges > 0


def test_daily_trend_has_two_traces(make_df):
    df = make_df("2025-09-01", "2025-09-30 23:00")
    trend = compute_daily_trend(df, MODALITIES)
    fig = plot_daily_trend(trend)
    assert len(fig.data) == 2
    assert [t.name for t in fig.data] == ["Daily total", "7-day average"]


def test_empty_trend_renders_placeholder():
    fig = plot_daily_trend(pd.DataFrame())
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) == 1


# ---------------------------------------------------------------------------
# Comparison charts
# ---------------------------------------------------------------------------

def test_weekday_comparison_has_one_trace_per_period(make_df):
    df = _labelled(make_df)
    daily = compute_daily_totals(df, MODALITIES)
    weekday_df = compute_weekday_totals(daily, MODALITIES)

    fig = plot_weekday_comparison(weekday_df, "car")
    assert len(fig.data) == 2
    for trace in fig.data:
        assert len(trace.x) == 7
        assert len(trace.y) == 7


def test_hourly_profile_has_period_x_modality_traces(make_df):
    df = _labelled(make_df)
    profile = compute_hourly_profile(df, MODALITIES)
    fig = plot_hourly_profile(profile, MODALITIES)
    assert len(fig.data) == 2 * len(MODALITIES)
    assert [t.name.startswith(("Christmas", "February")) for t in fig.data] == [True] * 8


def test_modal_split_has_one_trace_per_period(make_df):
    df = _labelled(make_df)
    split = compute_modal_split(df, MODALITIES)
    fig = plot_modal_split(split, MODALITIES)
    assert len(fig.data) == 2
    for trace in fig.data:
        assert len(trace.x) == len(MODALITIES)


def test_typical_week_heatmap_shape(make_df):
    df = _labelled(make_df)
    typical = compute_typical_week(df, MODALITIES)
    matrix = weekday_hour_matrix(typical, "Christmas", "car")
    fig = plot_typical_week(matrix)
    assert len(fig.data) == 1
    assert len(fig.data[0].z) == 7
    assert len(fig.data[0].z[0]) == 24


def test_weekday_occurrence_traces_per_group(make_df):
    df = make_df("2025-12-15", "2026-02-28 23:00")
    daily = compute_daily_totals(keep_assigned(label_periods(df, _two_periods())), MODALITIES)
    occurrence = compute_weekday_occurrence_totals(daily, ["car"])
    fig = plot_weekday_occurrence(occurrence, "car")
    # One trace per (period, weekday): two periods, seven weekdays each.
    assert len(fig.data) == 14
    assert {trace.legendgroup for trace in fig.data} == {"Christmas", "February half term"}
    assert all(trace.name for trace in fig.data)


def test_speed_distribution_has_one_trace_per_period():
    speed_df = pd.DataFrame(
        {
            "period_label": ["Christmas", "February half term"],
            "0-10": [30.0, 25.0],
            "10-20": [50.0, 55.0],
            "20+": [20.0, 20.0],
        }
    )
    fig = plot_speed_distribution(speed_df)
    assert len(fig.data) == 2
    for trace in fig.data:
        assert len(trace.x) == 3


def test_empty_figure_has_placeholder_annotation():
    fig = empty_figure()
    assert len(fig.data) == 0
    assert len(fig.layout.annotations) == 1
