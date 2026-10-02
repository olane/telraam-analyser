"""Weekday-aligned comparison charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analysis.align import WEEKDAY_LABELS
from charts.theme import legend_below, period_colour_map


def plot_weekday_comparison(
    weekday_df: pd.DataFrame,
    modality: str,
    value_label: str = "Mean daily count",
    height: int = 440,
    group_col: str = "period_label",
) -> go.Figure:
    """Grouped bars: one bar per comparison group for each weekday."""
    if weekday_df is None or weekday_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    groups = list(dict.fromkeys(weekday_df[group_col]))
    colours = period_colour_map(groups)

    fig = go.Figure()
    for group in groups:
        subset = weekday_df[weekday_df[group_col] == group]
        values = (
            subset.set_index("weekday")[modality].reindex(range(7)).tolist()
        )
        fig.add_trace(
            go.Bar(
                x=WEEKDAY_LABELS,
                y=values,
                name=group,
                marker_color=colours[group],
            )
        )

    fig.update_layout(
        title=f"{modality.title()} by weekday",
        barmode="group",
        yaxis_title=value_label,
        xaxis_title="Weekday",
        height=height,
        hovermode="x unified",
    )
    return legend_below(fig)
