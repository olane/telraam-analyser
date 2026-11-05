"""Daily distribution histogram with cumulative days at or above."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from charts.theme import (
    empty_figure,
    legend_below,
    modality_colour,
    period_colour_map,
)
from domain.models import modality_label


def _cumulative_line(
    subset: pd.DataFrame,
    name: str,
    colour: str,
    total: int,
) -> go.Scatter:
    share = (
        subset["at_or_above"] / total * 100 if total else subset["at_or_above"] * 0
    )
    return go.Scatter(
        x=subset["label"],
        y=subset["at_or_above"],
        mode="lines+markers",
        name=name,
        yaxis="y2",
        line=dict(color=colour, width=2, dash="dot"),
        marker=dict(size=5),
        customdata=share,
        hovertemplate="%{x}: %{y:,} days (%{customdata:.0f}%) "
        "at or above<extra></extra>",
    )


def plot_daily_histogram(
    hist_df: pd.DataFrame,
    modality: str,
    bin_width: int = 100,
    label: str | None = None,
    group_col: str | None = None,
    height: int = 440,
) -> go.Figure:
    """Bars per daily-total range, plus a cumulative "at or above" line."""
    if hist_df is None or hist_df.empty:
        return empty_figure()

    display = label or modality_label(modality)
    fig = go.Figure()

    if group_col:
        groups = list(dict.fromkeys(hist_df[group_col]))
        colours = period_colour_map([str(group) for group in groups])
        for group in groups:
            subset = hist_df[hist_df[group_col] == group]
            colour = colours[str(group)]
            fig.add_trace(
                go.Bar(
                    x=subset["label"],
                    y=subset["days"],
                    name=str(group),
                    marker_color=colour,
                    legendgroup=str(group),
                    hovertemplate="%{x} per day: %{y} days<extra>"
                    + str(group)
                    + "</extra>",
                )
            )
            fig.add_trace(
                _cumulative_line(
                    subset,
                    f"{group} at or above",
                    colour,
                    int(subset["days"].sum()),
                )
            )
        fig.update_layout(barmode="group")
        fig = legend_below(fig, margin_bottom=110)
    else:
        total = int(hist_df["days"].sum())
        fig.add_trace(
            go.Bar(
                x=hist_df["label"],
                y=hist_df["days"],
                name="Days per range",
                marker_color=modality_colour(modality),
                hovertemplate="%{x} per day: %{y} days<extra></extra>",
            )
        )
        fig.add_trace(
            _cumulative_line(
                hist_df,
                "Days at or above",
                "#c46210",
                total,
            )
        )

    fig.update_layout(
        title=f"Daily {display.lower()} — days per range",
        xaxis_title=f"{display} per day (bin width {bin_width:,})",
        yaxis_title="Number of days",
        yaxis2=dict(
            title="Days at or above",
            overlaying="y",
            side="right",
            rangemode="tozero",
            showgrid=False,
        ),
        height=height,
    )
    return fig
