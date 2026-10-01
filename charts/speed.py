"""Speed distribution chart."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts.theme import period_colour_map


def plot_speed_distribution(
    speed_df: pd.DataFrame,
    unit: str = "mph",
    height: int = 420,
) -> go.Figure:
    """Grouped bars of speed-bin percentages per period."""
    if speed_df is None or speed_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    groups = list(dict.fromkeys(speed_df["period_label"]))
    colours = period_colour_map(groups)
    bin_cols = [c for c in speed_df.columns if c != "period_label"]

    fig = go.Figure()
    for group in groups:
        row = speed_df[speed_df["period_label"] == group].iloc[0]
        fig.add_trace(
            go.Bar(
                x=bin_cols,
                y=[row[c] for c in bin_cols],
                name=group,
                marker_color=colours[group],
            )
        )

    fig.update_layout(
        title="Car speed distribution",
        xaxis_title=f"Speed bin ({unit})",
        yaxis_title="Share (%)",
        barmode="group",
        height=height,
    )
    return fig
