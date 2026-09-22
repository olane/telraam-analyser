"""Trend-over-time charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts.theme import KIND_COLOURS
from domain.models import Exclusion, PeriodInstance


def _add_bands(
    fig: go.Figure,
    instances: list[PeriodInstance] | None,
    exclusions: list[Exclusion] | None,
) -> None:
    annotated: set[str] = set()
    for instance in instances or []:
        colour = KIND_COLOURS.get(instance.kind.value, "#7f7f7f")
        for start, end in instance.ranges:
            fig.add_vrect(
                x0=pd.Timestamp(start),
                x1=pd.Timestamp(end),
                fillcolor=colour,
                opacity=0.10,
                line_width=0,
                layer="below",
            )
        if instance.label not in annotated:
            first = instance.ranges[0] if instance.ranges else None
            if first:
                fig.add_annotation(
                    x=pd.Timestamp(first[0]),
                    y=1.0,
                    yref="paper",
                    text=instance.label,
                    showarrow=False,
                    xanchor="left",
                    font=dict(size=10, color=colour),
                )
            annotated.add(instance.label)

    for exclusion in exclusions or []:
        for start, end in exclusion.ranges:
            fig.add_vrect(
                x0=pd.Timestamp(start),
                x1=pd.Timestamp(end),
                fillcolor="#b0bec5",
                opacity=0.35,
                line_width=0,
                layer="below",
            )
        if exclusion.label not in annotated and exclusion.ranges:
            start = exclusion.ranges[0][0]
            fig.add_annotation(
                x=pd.Timestamp(start),
                y=0.02,
                yref="paper",
                text=f"Excluded: {exclusion.label}",
                showarrow=False,
                xanchor="left",
                font=dict(size=10, color="#546e7a"),
            )
            annotated.add(exclusion.label)


def plot_daily_trend(
    trend_df: pd.DataFrame,
    instances: list[PeriodInstance] | None = None,
    exclusions: list[Exclusion] | None = None,
    title: str = "Traffic trend",
    rolling_label: str = "7-day average",
    height: int = 440,
) -> go.Figure:
    if trend_df is None or trend_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["total"],
            mode="lines",
            name="Daily total",
            line=dict(color="#b0bec5", width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["rolling"],
            mode="lines",
            name=rolling_label,
            line=dict(color="#0b6e99", width=3),
        )
    )

    _add_bands(fig, instances, exclusions)

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Count per day",
        height=height,
    )
    return fig


def plot_weekday_adjusted_trend(
    trend_df: pd.DataFrame,
    instances: list[PeriodInstance] | None = None,
    exclusions: list[Exclusion] | None = None,
    title: str = "Weekday-adjusted trend",
    rolling_label: str = "28-day average",
    height: int = 420,
) -> go.Figure:
    if trend_df is None or trend_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    fig = go.Figure()
    fig.add_hline(y=0, line_color="#cfd8dc", line_width=1)
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["residual"],
            mode="lines",
            name="Daily vs weekday norm",
            line=dict(color="#cfd8dc", width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["rolling_residual"],
            mode="lines",
            name=rolling_label,
            line=dict(color="#c46210", width=3),
        )
    )

    _add_bands(fig, instances, exclusions)

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Above / below typical weekday",
        height=height,
    )
    return fig
