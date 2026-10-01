"""Weekday-aligned comparison charts."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from analysis.align import WEEKDAY_LABELS
from charts.theme import period_colour_map


def plot_weekday_comparison(
    weekday_df: pd.DataFrame,
    modality: str,
    value_label: str = "Mean daily count",
    height: int = 400,
) -> go.Figure:
    """Grouped bars: one bar per period for each weekday."""
    if weekday_df is None or weekday_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    groups = list(dict.fromkeys(weekday_df["period_label"]))
    colours = period_colour_map(groups)

    fig = go.Figure()
    for group in groups:
        subset = weekday_df[weekday_df["period_label"] == group]
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
    return fig


def plot_weekday_occurrence(
    occurrence_df: pd.DataFrame,
    modality: str,
    height: int = 400,
) -> go.Figure:
    """Lines: mean value by nth occurrence of each weekday within a period.

    Useful for long holidays where weekday alignment alone hides week 1 vs
    week 2 differences.
    """
    if occurrence_df is None or occurrence_df.empty:
        from charts.theme import empty_figure

        return empty_figure()

    groups = list(dict.fromkeys(occurrence_df["period_label"]))
    colours = period_colour_map(groups)

    fig = go.Figure()
    for group in groups:
        subset = occurrence_df[occurrence_df["period_label"] == group]
        for weekday, label in enumerate(WEEKDAY_LABELS):
            days = subset[subset["weekday"] == weekday].sort_values(
                "weekday_occurrence"
            )
            if days.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=days["weekday_occurrence"],
                    y=days[modality],
                    mode="lines+markers",
                    name=f"{group} — {label}",
                    line=dict(color=colours[group]),
                    legendgroup=group,
                )
            )

    fig.update_layout(
        title=f"{modality.title()} — weekday occurrence",
        xaxis_title="Occurrence of that weekday in the period",
        yaxis_title="Mean count",
        height=height,
    )
    return fig
