"""Plotly chart builders for traffic data comparison."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Colour palettes — stable assignment per period group / modality
PERIOD_COLOURS = px.colors.qualitative.Set2
MODALITY_COLOURS = {
    "pedestrian": "#2ca02c",
    "bike": "#ff7f0e",
    "car": "#1f77b4",
    "heavy": "#d62728",
    "pedestrian_lft": "#98df8a",
    "pedestrian_rgt": "#2ca02c",
    "bike_lft": "#ffbb78",
    "bike_rgt": "#ff7f0e",
    "car_lft": "#aec7e8",
    "car_rgt": "#1f77b4",
    "heavy_lft": "#ff9896",
    "heavy_rgt": "#d62728",
}


def _period_colour(period_names: list[str]) -> dict[str, str]:
    return {
        name: PERIOD_COLOURS[i % len(PERIOD_COLOURS)]
        for i, name in enumerate(period_names)
    }


# ---------------------------------------------------------------------------
# Hourly profile
# ---------------------------------------------------------------------------

_DASH_STYLES = ["solid", "dash", "dot", "dashdot", "longdash", "longdashdot"]
_MARKER_SYMBOLS = ["circle", "square", "diamond", "cross", "x", "triangle-up"]


def plot_hourly_profile(
    profile_df: pd.DataFrame, modalities: list[str]
) -> go.Figure:
    """Line chart: hour on x-axis, one trace per (period_group, modality).

    Period groups are distinguished by colour; modalities are distinguished
    by line dash style, marker symbol, and their own fixed colour when there
    is only one period group.
    """
    fig = go.Figure()
    groups = profile_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)
    single_group = len(groups) == 1

    for mi, modality in enumerate(modalities):
        dash = _DASH_STYLES[mi % len(_DASH_STYLES)]
        marker = _MARKER_SYMBOLS[mi % len(_MARKER_SYMBOLS)]
        for group in groups:
            subset = profile_df[profile_df["period_group"] == group]
            # With one group, colour by modality; with multiple, colour by group
            colour = (
                MODALITY_COLOURS.get(modality, period_colours[group])
                if single_group
                else period_colours[group]
            )
            fig.add_trace(
                go.Scatter(
                    x=subset["hour"],
                    y=subset[modality],
                    mode="lines+markers",
                    name=f"{group} — {modality}",
                    line=dict(color=colour, dash=dash, width=2),
                    marker=dict(symbol=marker, size=7),
                    legendgroup=f"{group} — {modality}",
                )
            )

    fig.update_layout(
        title="Hourly Traffic Profile",
        xaxis_title="Hour of Day",
        yaxis_title="Average Count",
        xaxis=dict(dtick=1),
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Daily volume
# ---------------------------------------------------------------------------

def plot_daily_volume(
    daily_df: pd.DataFrame, modalities: list[str]
) -> go.Figure:
    """Stacked bar chart of daily totals, one subplot row per period group."""
    from plotly.subplots import make_subplots

    groups = daily_df["period_group"].unique().tolist()
    fig = make_subplots(
        rows=len(groups),
        cols=1,
        shared_xaxes=True,
        shared_yaxes=True,
        subplot_titles=groups,
        vertical_spacing=0.08,
    )

    for gi, group in enumerate(groups, 1):
        subset = daily_df[daily_df["period_group"] == group].sort_values("day")
        for modality in modalities:
            fig.add_trace(
                go.Bar(
                    x=subset["day"],
                    y=subset[modality],
                    name=modality,
                    marker_color=MODALITY_COLOURS.get(modality),
                    legendgroup=modality,
                    showlegend=(gi == 1),  # only show legend once per modality
                ),
                row=gi,
                col=1,
            )

    fig.update_layout(
        title="Daily Traffic Volume",
        barmode="stack",
        hovermode="x unified",
        height=350 * len(groups),
    )
    fig.update_yaxes(title_text="Count", row=1, col=1)
    return fig


def plot_daily_volume_grouped(
    daily_df: pd.DataFrame, modalities: list[str]
) -> go.Figure:
    """Grouped bar chart of daily totals, one bar per period group."""
    groups = daily_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)

    daily_df = daily_df.copy()
    daily_df["total"] = daily_df[modalities].sum(axis=1)

    fig = go.Figure()
    for group in groups:
        subset = daily_df[daily_df["period_group"] == group].sort_values("day")
        fig.add_trace(
            go.Bar(
                x=subset["day"],
                y=subset["total"],
                name=group,
                marker_color=period_colours[group],
            )
        )

    fig.update_layout(
        title="Daily Traffic Volume",
        xaxis_title="Date",
        yaxis_title="Total Count",
        barmode="group",
        hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Modal split
# ---------------------------------------------------------------------------

def plot_modal_split(
    split_df: pd.DataFrame, modalities: list[str]
) -> go.Figure:
    """Grouped bar chart: one bucket per modality, one bar per period group."""
    fig = go.Figure()
    groups = split_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)

    for group in groups:
        row = split_df[split_df["period_group"] == group].iloc[0]
        fig.add_trace(
            go.Bar(
                x=modalities,
                y=[row[m] for m in modalities],
                name=group,
                marker_color=period_colours[group],
            )
        )

    fig.update_layout(
        title="Modal Split (%)",
        xaxis_title="Modality",
        yaxis_title="Share (%)",
        barmode="group",
    )
    return fig


# ---------------------------------------------------------------------------
# Speed distribution
# ---------------------------------------------------------------------------

def plot_speed_distribution(speed_df: pd.DataFrame, unit: str = "mph") -> go.Figure:
    """Grouped bar chart of speed bin percentages per period group."""
    groups = speed_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)
    bin_cols = [c for c in speed_df.columns if c != "period_group"]

    fig = go.Figure()
    for group in groups:
        row = speed_df[speed_df["period_group"] == group].iloc[0]
        fig.add_trace(
            go.Bar(
                x=bin_cols,
                y=[row[c] for c in bin_cols],
                name=group,
                marker_color=period_colours[group],
            )
        )

    fig.update_layout(
        title="Car Speed Distribution",
        xaxis_title=f"Speed Bin ({unit})",
        yaxis_title="Share (%)",
        barmode="group",
    )
    return fig
