"""Academic calendars, pluggable by year.

The calendar is data-driven: add an academic year to :data:`CAMBRIDGE_YEARS`
and it automatically becomes available to the UI. Year-on-year comparisons
light up as soon as more than one year is present.

Only the 2025-26 Cambridge year is populated today. Prior years should be
added from the official source:
https://www.cambridgeshire.gov.uk/residents/children-and-families/schools-learning/school-term-dates-closures
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from domain.models import Calendar, PeriodInstance, PeriodKind

# ---------------------------------------------------------------------------
# Cambridge term and holiday dates, keyed by academic year.
#
# To add a year, copy the "2025-26" block, change the key and the dates. Both
# "terms" and "holidays" are required; holiday keys are PeriodKind members.
# ---------------------------------------------------------------------------

CAMBRIDGE_YEARS: dict[str, dict] = {
    "2025-26": {
        "terms": {
            "Autumn 1": (date(2025, 9, 1), date(2025, 10, 24)),
            "Autumn 2": (date(2025, 11, 3), date(2025, 12, 19)),
            "Spring 1": (date(2026, 1, 5), date(2026, 2, 13)),
            "Spring 2": (date(2026, 2, 23), date(2026, 3, 27)),
            "Summer 1": (date(2026, 4, 13), date(2026, 5, 22)),
            "Summer 2": (date(2026, 6, 1), date(2026, 7, 20)),
        },
        "holidays": {
            PeriodKind.AUTUMN_HALF: (date(2025, 10, 27), date(2025, 10, 31)),
            PeriodKind.CHRISTMAS: (date(2025, 12, 22), date(2026, 1, 2)),
            PeriodKind.FEB_HALF: (date(2026, 2, 16), date(2026, 2, 20)),
            PeriodKind.EASTER: (date(2026, 3, 30), date(2026, 4, 10)),
            PeriodKind.MAY_HALF: (date(2026, 5, 25), date(2026, 5, 29)),
        },
    },
    # Example of a second year (dates to be confirmed before enabling):
    # "2024-25": {
    #     "terms": {...},
    #     "holidays": {...},
    # },
}

# Anchors used by anchor-relative alignment, where the exact date matters.
HOLIDAY_ANCHORS: dict[PeriodKind, Callable[[date, date], date]] = {
    PeriodKind.CHRISTMAS: lambda start, end: date(start.year, 12, 25),
}


def _anchor_for(kind: PeriodKind, start: date, end: date) -> date:
    builder = HOLIDAY_ANCHORS.get(kind)
    if builder is not None:
        return builder(start, end)
    return start


def build_cambridge_calendar(years: list[str] | None = None) -> Calendar:
    """Build the Cambridge calendar for the requested academic years.

    *years* defaults to every year present in :data:`CAMBRIDGE_YEARS`.
    """
    selected = years or sorted(CAMBRIDGE_YEARS)
    instances: list[PeriodInstance] = []

    for academic_year in selected:
        entry = CAMBRIDGE_YEARS.get(academic_year)
        if entry is None:
            continue

        for name, (start, end) in entry["terms"].items():
            instances.append(
                PeriodInstance(
                    label=f"{name} term {academic_year}",
                    kind=PeriodKind.TERM,
                    ranges=((start, end),),
                    academic_year=academic_year,
                    anchor=start,
                )
            )

        for kind, (start, end) in entry["holidays"].items():
            instances.append(
                PeriodInstance(
                    label=f"{kind.human} {academic_year}",
                    kind=kind,
                    ranges=((start, end),),
                    academic_year=academic_year,
                    anchor=_anchor_for(kind, start, end),
                )
            )

    return Calendar(
        name="Cambridge",
        region="Cambridgeshire, UK",
        instances=instances,
    )


def default_calendar() -> Calendar:
    """Calendar used by the app on first load."""
    return build_cambridge_calendar()
