"""Opinionated comparison recipes (pure: build period sets from a calendar)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd

from domain.models import (
    Calendar,
    ComparisonConfig,
    ComparisonMode,
    DateRange,
    InterventionFilter,
    PeriodInstance,
    PeriodKind,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def aggregate(
    label: str, kind: PeriodKind, instances: list[PeriodInstance]
) -> PeriodInstance:
    """Merge several instances into one multi-range synthetic period."""
    ranges = tuple(r for i in instances for r in i.ranges)
    return PeriodInstance(label=label, kind=kind, ranges=ranges)


def latest_year(calendar: Calendar) -> str | None:
    years = calendar.years()
    return years[-1] if years else None


# ---------------------------------------------------------------------------
# Recipes
# ---------------------------------------------------------------------------

def holiday_vs_term(
    calendar: Calendar, years: list[str] | None = None
) -> list[PeriodInstance]:
    instances = calendar.instances
    if years:
        instances = [i for i in instances if i.academic_year in years]

    terms = [i for i in instances if i.kind.is_term]
    holidays = [i for i in instances if i.kind.is_holiday]
    out: list[PeriodInstance] = []
    if terms:
        out.append(aggregate("Term time", PeriodKind.TERM, terms))
    if holidays:
        out.append(aggregate("School holidays", PeriodKind.HOLIDAY, holidays))
    return out


def year_on_year(
    calendar: Calendar, kind: PeriodKind = PeriodKind.CHRISTMAS
) -> list[PeriodInstance]:
    matches = [i for i in calendar.instances if i.kind is kind]
    return sorted(matches, key=lambda i: i.start or date.min)


def build_before_after(
    cutover: date,
    window_days: int = 56,
    include_previous_year: bool = False,
) -> list[PeriodInstance]:
    """Two windows either side of a cutover date, for intervention analysis."""
    before_start = cutover - timedelta(days=window_days)
    before_end = cutover - timedelta(days=1)
    after_start = cutover
    after_end = cutover + timedelta(days=window_days - 1)

    instances = [
        PeriodInstance(
            label="Before intervention",
            kind=PeriodKind.INTERVENTION_BEFORE,
            ranges=((before_start, before_end),),
            anchor=cutover,
        ),
        PeriodInstance(
            label="After intervention",
            kind=PeriodKind.INTERVENTION_AFTER,
            ranges=((after_start, after_end),),
            anchor=cutover,
        ),
    ]

    if include_previous_year:
        shift = timedelta(days=364)
        instances.append(
            PeriodInstance(
                label="Same window, previous year",
                kind=PeriodKind.CUSTOM,
                ranges=(
                    (before_start - shift, before_end - shift),
                    (after_start - shift, after_end - shift),
                ),
                anchor=cutover,
            )
        )
    return instances


def _merge_ranges(ranges: list[DateRange]) -> tuple[DateRange, ...]:
    """Sort and coalesce overlapping or adjacent date ranges."""
    if not ranges:
        return ()
    ordered = sorted(ranges)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1] + timedelta(days=1):
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((start, end) for start, end in merged)


def _calendar_periods(
    calendar: Calendar, date_filter: InterventionFilter
) -> list[PeriodInstance]:
    if date_filter is InterventionFilter.TERM_ONLY:
        return [i for i in calendar.instances if i.kind.is_term]
    return [i for i in calendar.instances if i.kind.is_holiday]


def _clip_ranges(
    window: DateRange,
    calendar: Calendar,
    date_filter: InterventionFilter,
) -> tuple[DateRange, ...]:
    """Intersect *window* with the calendar's term or holiday date ranges."""
    start, end = window
    overlaps: list[DateRange] = []
    for instance in _calendar_periods(calendar, date_filter):
        for period_start, period_end in instance.ranges:
            overlap_start = max(start, period_start)
            overlap_end = min(end, period_end)
            if overlap_start <= overlap_end:
                overlaps.append((overlap_start, overlap_end))
    return _merge_ranges(overlaps)


def _clip_instance(
    instance: PeriodInstance,
    calendar: Calendar,
    date_filter: InterventionFilter,
) -> PeriodInstance:
    """Clip each of the instance's ranges to the calendar, then coalesce."""
    clipped: list[DateRange] = []
    for window in instance.ranges:
        clipped.extend(_clip_ranges(window, calendar, date_filter))
    return replace(instance, ranges=_merge_ranges(clipped))


def resolve(
    calendar: Calendar, config: ComparisonConfig
) -> list[PeriodInstance]:
    """Turn a comparison configuration into concrete period instances."""
    mode = config.mode

    if mode is ComparisonMode.HOLIDAY_VS_TERM:
        return holiday_vs_term(calendar, config.years or None)

    if mode is ComparisonMode.YEAR_ON_YEAR:
        return year_on_year(calendar, config.kind or PeriodKind.CHRISTMAS)

    if mode is ComparisonMode.BEFORE_AFTER:
        if config.cutover is None:
            return []
        instances = build_before_after(
            config.cutover,
            config.window_days,
            config.include_previous_year,
        )
        if config.date_filter is not InterventionFilter.ALL:
            instances = [
                _clip_instance(i, calendar, config.date_filter)
                for i in instances
            ]
        return instances

    if mode is ComparisonMode.CUSTOM:
        out: list[PeriodInstance] = []
        for label in config.period_labels:
            found = calendar.get(label)
            if found is not None:
                out.append(found)
        return out

    # Axis-only modes (weekday/weekend, time of day, roadworks) still mark
    # every calendar period so trend charts have their usual context bands.
    instances = calendar.instances
    if config.years:
        instances = [i for i in instances if i.academic_year in config.years]
    return list(instances)


# ---------------------------------------------------------------------------
# Presentation helper
# ---------------------------------------------------------------------------

def describe_instances(instances: list[PeriodInstance]) -> pd.DataFrame:
    """Tabular summary of a set of periods, for display."""
    rows = []
    for inst in instances:
        rows.append(
            {
                "Period": inst.label,
                "Type": inst.kind.human,
                "Year": inst.academic_year or "",
                "Start": inst.start,
                "End": inst.end,
                "Days": inst.n_days,
            }
        )
    return pd.DataFrame(rows)
