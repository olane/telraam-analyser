"""Hourly profile chart."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts.theme import modality_colour, period_colour_map

_DASH_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
_MARKER_SYMBOLS = ["circle", "square", "diamond", "cross", "x", "triangle-up"]


def plot_hourly_profile(
    profile_df: pd.DataFrame,
    modalities: list[str],
    height: int = 440,
) -> go.Figure:
    """Line chart: hour on x-axis, one trace per (period, modality)."""
    if profile_df is None or profile_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    fig = go.Figure()
    groups = list(dict.fromkeys(profile_df["period_label"]))
    period_colours = period_colour_map(groups)
    single_group = len(groups) == 1

    for mi, modality in enumerate(modalities):
        dash = _DASH_STYLES[mi % len(_DASH_STYLES)]
        marker = _MARKER_SYMBOLS[mi % len(_MARKER_SYMBOLS)]
        for group in groups:
            subset = profile_df[profile_df["period_label"] == group]
            colour = (
                modality_colour(modality) if single_group else period_colours[group]
            )
            fig.add_trace(
                go.Scatter(
                    x=subset["hour"],
                    y=subset[modality],
                    mode="lines+markers",
                    name=f"{group} — {modality}",
                    line=dict(color=colour, dash=dash, width=2),
                    marker=dict(symbol=marker, size=6),
                    legendgroup=f"{group} — {modality}",
                )
            )

    fig.update_layout(
        title="Average hour of day",
        xaxis_title="Hour of day",
        yaxis_title="Average count",
        xaxis=dict(dtick=1),
        height=height,
    )
    return fig
