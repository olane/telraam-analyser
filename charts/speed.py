"""Speed charts: overall distribution and V85 trend."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

_DIST_COLOUR = "#0b6e99"
_TREND_COLOUR = "#c46210"
_TREND_FILL = "#b0bec5"


def plot_speed_distribution(
    speed_df: pd.DataFrame,
    unit: str = "mph",
    height: int = 420,
) -> go.Figure:
    """Single bar trace of speed-bin shares for the whole selection."""
    if speed_df is None or speed_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    bin_cols = list(speed_df.columns)
    row = speed_df.iloc[0]

    fig = go.Figure(
        go.Bar(
            x=bin_cols,
            y=[row[c] for c in bin_cols],
            name="All selected days",
            marker_color=_DIST_COLOUR,
        )
    )
    fig.update_layout(
        title="Car speed distribution",
        xaxis_title=f"Speed bin ({unit})",
        yaxis_title="Share (%)",
        height=height,
    )
    return fig


def plot_speed_trend(
    trend_df: pd.DataFrame,
    unit: str = "mph",
    rolling_label: str = "7-day average",
    height: int = 360,
) -> go.Figure:
    """Line chart: daily V85 with a trailing rolling mean."""
    if trend_df is None or trend_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["v85"],
            mode="lines",
            name=f"Daily V85 ({unit})",
            line=dict(color=_TREND_FILL, width=1),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_df["day"],
            y=trend_df["rolling"],
            mode="lines",
            name=rolling_label,
            line=dict(color=_TREND_COLOUR, width=3),
        )
    )
    fig.update_layout(
        title="V85 speed trend",
        xaxis_title="Date",
        yaxis_title=f"V85 ({unit})",
        height=height,
    )
    return fig
