"""Typical-week heatmap."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def plot_typical_week(
    matrix: pd.DataFrame,
    title: str = "Typical week",
    height: int = 320,
) -> go.Figure:
    """Heatmap of weekday (rows) × hour (cols) average counts."""
    if matrix is None or matrix.empty:
        from charts.theme import empty_figure

        return empty_figure()

    fig = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=[str(c) for c in matrix.columns],
            y=list(matrix.index),
            colorscale="Blues",
            colorbar=dict(title="Mean"),
            hovertemplate="%{y} %{x}:00 — %{z:.1f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Hour of day",
        yaxis_title="",
        height=height,
    )
    return fig
