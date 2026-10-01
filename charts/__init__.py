"""Chart builders for traffic comparison."""

from charts.heatmap import plot_typical_week
from charts.hourly import plot_hourly_profile
from charts.modal import plot_modal_split
from charts.speed import plot_speed_distribution
from charts.theme import (
    KIND_COLOURS,
    MODALITY_COLOURS,
    PERIOD_COLOURS,
    empty_figure,
    modality_colour,
    period_colour_map,
    register_template,
)
from charts.trend import plot_daily_trend, plot_weekday_adjusted_trend
from charts.weekday import plot_weekday_comparison, plot_weekday_occurrence

__all__ = [
    "KIND_COLOURS",
    "MODALITY_COLOURS",
    "PERIOD_COLOURS",
    "empty_figure",
    "modality_colour",
    "period_colour_map",
    "plot_daily_trend",
    "plot_hourly_profile",
    "plot_modal_split",
    "plot_speed_distribution",
    "plot_typical_week",
    "plot_weekday_adjusted_trend",
    "plot_weekday_comparison",
    "plot_weekday_occurrence",
    "register_template",
]
