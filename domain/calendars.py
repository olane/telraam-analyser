"""Academic calendars, pluggable by year.

The calendar is data-driven: add an academic year to :data:`CAMBRIDGE_YEARS`
and it automatically becomes available to the UI. Year-on-year comparisons
light up as soon as more than one year is present.

The 2025-26 and 2026-27 Cambridge years are populated. Further years should be
added from the official source:
https://www.cambridgeshire.gov.uk/residents/children-and-families/schools-learning/school-term-dates-closures
"""

from __future__ import annotations

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
            PeriodKind.SUMMER: (date(2026, 7, 21), date(2026, 8, 31)),
        },
    },
    "2026-27": {
        "terms": {
            "Autumn 1": (date(2026, 9, 1), date(2026, 10, 23)),
            "Autumn 2": (date(2026, 11, 2), date(2026, 12, 18)),
            "Spring 1": (date(2027, 1, 4), date(2027, 2, 12)),
            "Spring 2": (date(2027, 2, 22), date(2027, 3, 25)),
            "Summer 1": (date(2027, 4, 12), date(2027, 5, 28)),
            "Summer 2": (date(2027, 6, 7), date(2027, 7, 21)),
        },
        "holidays": {
            PeriodKind.AUTUMN_HALF: (date(2026, 10, 26), date(2026, 10, 30)),
            PeriodKind.CHRISTMAS: (date(2026, 12, 21), date(2027, 1, 1)),
            PeriodKind.FEB_HALF: (date(2027, 2, 15), date(2027, 2, 19)),
            PeriodKind.EASTER: (date(2027, 3, 26), date(2027, 4, 9)),
            PeriodKind.MAY_HALF: (date(2027, 5, 31), date(2027, 6, 4)),
            PeriodKind.SUMMER: (date(2027, 7, 22), date(2027, 8, 31)),
        },
    },
}

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
                )
            )

        for kind, (start, end) in entry["holidays"].items():
            instances.append(
                PeriodInstance(
                    label=f"{kind.human} {academic_year}",
                    kind=kind,
                    ranges=((start, end),),
                    academic_year=academic_year,
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
