"""Pure analysis layer: filtering, aggregation, alignment and comparisons."""

from analysis.aggregates import (
    compute_daily_totals,
    compute_hourly_profile,
    compute_modal_split,
    compute_period_totals,
    compute_speed_distribution,
    compute_speed_summary,
    compute_speed_trend,
    period_mean_daily,
)
from analysis.align import (
    WEEKDAY_LABELS,
    compute_typical_week,
    compute_weekday_totals,
    weekday_hour_matrix,
)
from analysis.comparisons import (
    describe_instances,
    holiday_vs_term,
    resolve,
)
from analysis.filters import (
    add_derived_modalities,
    add_time_columns,
    dedupe_modalities,
    get_available_groups,
    get_available_modalities,
    keep_assigned,
    label_periods,
    redistribute_night,
)
from analysis.grouping import add_comparison_group
from analysis.pipeline import prepare_frame
from analysis.trends import (
    compute_daily_trend,
    daily_total_series,
    weekday_adjusted_trend,
)

__all__ = [
    "WEEKDAY_LABELS",
    "add_comparison_group",
    "add_derived_modalities",
    "add_time_columns",
    "compute_daily_totals",
    "compute_daily_trend",
    "compute_hourly_profile",
    "compute_modal_split",
    "compute_period_totals",
    "compute_speed_distribution",
    "compute_speed_summary",
    "compute_speed_trend",
    "compute_typical_week",
    "compute_weekday_totals",
    "daily_total_series",
    "dedupe_modalities",
    "describe_instances",
    "get_available_groups",
    "get_available_modalities",
    "holiday_vs_term",
    "keep_assigned",
    "label_periods",
    "period_mean_daily",
    "prepare_frame",
    "redistribute_night",
    "resolve",
    "weekday_adjusted_trend",
    "weekday_hour_matrix",
]
