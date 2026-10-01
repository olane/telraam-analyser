"""Modal split chart."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts.theme import period_colour_map


def plot_modal_split(
    split_df: pd.DataFrame,
    modalities: list[str],
    height: int = 400,
) -> go.Figure:
    """Grouped bars: one bar per period for each modality share."""
    if split_df is None or split_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    groups = list(dict.fromkeys(split_df["period_label"]))
    colours = period_colour_map(groups)

    fig = go.Figure()
    for group in groups:
        row = split_df[split_df["period_label"] == group].iloc[0]
        fig.add_trace(
            go.Bar(
                x=modalities,
                y=[row[m] for m in modalities],
                name=group,
                marker_color=colours[group],
                hovertemplate="%{x}: %{y:.1f}%<extra>" + group + "</extra>",
            )
        )

    fig.update_layout(
        title="Modal split",
        xaxis_title="Modality",
        yaxis_title="Share (%)",
        barmode="group",
        height=height,
    )
    return fig
