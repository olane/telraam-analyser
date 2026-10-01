"""Shared chart theme, palettes and small helpers."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

PERIOD_COLOURS = [
    "#0b6e99",
    "#c46210",
    "#2e8b57",
    "#9b59b6",
    "#d62728",
    "#7f8c8d",
    "#e377c2",
    "#17becf",
]

MODALITY_COLOURS = {
    "pedestrian": "#2ca02c",
    "bike": "#ff7f0e",
    "car": "#1f77b4",
    "heavy": "#d62728",
    "night": "#4c4c8a",
    "pedestrian_lft": "#98df8a",
    "pedestrian_rgt": "#2ca02c",
    "bike_lft": "#ffbb78",
    "bike_rgt": "#ff7f0e",
    "car_lft": "#aec7e8",
    "car_rgt": "#1f77b4",
    "heavy_lft": "#ff9896",
    "heavy_rgt": "#d62728",
    "night_lft": "#8a8ac4",
    "night_rgt": "#4c4c8a",
}

KIND_COLOURS = {
    "term": "#1f77b4",
    "autumn_half_term": "#ff7f0e",
    "christmas": "#d62728",
    "feb_half_term": "#9467bd",
    "easter": "#2ca02c",
    "may_half_term": "#8c564b",
    "summer": "#e377c2",
    "custom": "#7f7f7f",
    "intervention_before": "#17becf",
    "intervention_after": "#bcbd22",
}

_TEMPLATE_NAME = "telraam"


def register_template() -> None:
    """Register (once) and activate the app-wide Plotly template."""
    if _TEMPLATE_NAME not in pio.templates:
        template = go.layout.Template()
        template.layout = go.Layout(
            font=dict(
                family="Inter, system-ui, -apple-system, sans-serif", size=13
            ),
            colorway=PERIOD_COLOURS,
            hovermode="x unified",
            margin=dict(l=48, r=24, t=56, b=44),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(gridcolor="#eceff1", zeroline=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        pio.templates[_TEMPLATE_NAME] = template
    pio.templates.default = _TEMPLATE_NAME


def period_colour_map(labels: list[str]) -> dict[str, str]:
    return {
        label: PERIOD_COLOURS[i % len(PERIOD_COLOURS)]
        for i, label in enumerate(labels)
    }


def modality_colour(modality: str) -> str:
    return MODALITY_COLOURS.get(modality, "#7f7f7f")


def empty_figure(message: str = "No data for the current selection") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        font=dict(size=14, color="#78909c"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(height=300)
    return fig
