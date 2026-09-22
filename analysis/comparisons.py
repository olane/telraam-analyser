"""Opinionated comparison recipes (pure: build period sets from a calendar)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from domain.models import (
    HOLIDAY_KINDS,
    Calendar,
    ComparisonConfig,
    ComparisonMode,
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
        out.append(aggregate("School holidays", PeriodKind.CUSTOM, holidays))
    return out


def year_on_year(
    calendar: Calendar, kind: PeriodKind = PeriodKind.CHRISTMAS
) -> list[PeriodInstance]:
    matches = [i for i in calendar.instances if i.kind is kind]
    return sorted(matches, key=lambda i: i.start or date.min)


def by_kind(
    calendar: Calendar,
    kinds: list[PeriodKind] | None = None,
    year: str | None = None,
) -> list[PeriodInstance]:
    kinds = kinds or list(HOLIDAY_KINDS)
    year = year or latest_year(calendar)
    matches = [
        i
        for i in calendar.instances
        if i.kind in kinds and (year is None or i.academic_year == year)
    ]
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


def resolve(
    calendar: Calendar, config: ComparisonConfig
) -> list[PeriodInstance]:
    """Turn a comparison configuration into concrete period instances."""
    mode = config.mode

    if mode is ComparisonMode.HOLIDAY_VS_TERM:
        return holiday_vs_term(calendar, config.years or None)

    if mode is ComparisonMode.YEAR_ON_YEAR:
        return year_on_year(calendar, config.kind or PeriodKind.CHRISTMAS)

    if mode is ComparisonMode.BY_KIND:
        kinds = config.kinds or ([config.kind] if config.kind else None)
        year = config.years[-1] if config.years else None
        return by_kind(calendar, kinds, year)

    if mode is ComparisonMode.TREND:
        # Label every period so trend bands are complete.
        instances = calendar.instances
        if config.years:
            instances = [i for i in instances if i.academic_year in config.years]
        return list(instances)

    if mode is ComparisonMode.BEFORE_AFTER:
        if config.cutover is None:
            return []
        return build_before_after(
            config.cutover,
            config.window_days,
            config.include_previous_year,
        )

    # CUSTOM: resolve explicit labels against the calendar.
    out: list[PeriodInstance] = []
    for label in config.period_labels:
        found = calendar.get(label)
        if found is not None:
            out.append(found)
    return out


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
