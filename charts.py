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

def plot_hourly_profile(
    profile_df: pd.DataFrame, modalities: list[str]
) -> go.Figure:
    """Line chart: hour on x-axis, one trace per (period_group, modality)."""
    fig = go.Figure()
    groups = profile_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)

    for modality in modalities:
        for group in groups:
            subset = profile_df[profile_df["period_group"] == group]
            fig.add_trace(
                go.Scatter(
                    x=subset["hour"],
                    y=subset[modality],
                    mode="lines+markers",
                    name=f"{group} — {modality}",
                    line=dict(
                        color=period_colours[group],
                        dash="solid" if modality == modalities[0] else "dot",
                    ),
                    legendgroup=group,
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
    """Time series bar chart of daily totals, coloured by period group."""
    fig = go.Figure()
    groups = daily_df["period_group"].unique().tolist()
    period_colours = _period_colour(groups)

    daily_df = daily_df.copy()
    daily_df["total"] = daily_df[modalities].sum(axis=1)

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
    """Grouped bar chart of modal split percentages per period group."""
    fig = go.Figure()

    for modality in modalities:
        fig.add_trace(
            go.Bar(
                x=split_df["period_group"],
                y=split_df[modality],
                name=modality,
                marker_color=MODALITY_COLOURS.get(modality),
            )
        )

    fig.update_layout(
        title="Modal Split (%)",
        xaxis_title="Period Group",
        yaxis_title="Share (%)",
        barmode="group",
    )
    return fig


# ---------------------------------------------------------------------------
# Speed distribution
# ---------------------------------------------------------------------------

def plot_speed_distribution(speed_df: pd.DataFrame) -> go.Figure:
    """Overlaid bar chart of speed bin percentages per period group."""
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
                opacity=0.7,
            )
        )

    fig.update_layout(
        title="Car Speed Distribution",
        xaxis_title="Speed Bin (km/h)",
        yaxis_title="Share (%)",
        barmode="overlay",
    )
    return fig
