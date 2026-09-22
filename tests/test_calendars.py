from __future__ import annotations

from datetime import date

from domain.calendars import build_cambridge_calendar, default_calendar
from domain.models import PeriodKind


def test_default_calendar_has_expected_instances():
    calendar = default_calendar()
    assert calendar.name == "Cambridge"
    assert calendar.years() == ["2025-26"]
    assert len(calendar.of_kind(PeriodKind.TERM)) == 6
    assert len(calendar.of_kind(PeriodKind.CHRISTMAS)) == 1


def test_labels_are_unique():
    labels = default_calendar().labels()
    assert len(labels) == len(set(labels))


def test_christmas_dates_and_anchor():
    christmas = default_calendar().of_kind(PeriodKind.CHRISTMAS)[0]
    assert christmas.start == date(2025, 12, 22)
    assert christmas.end == date(2026, 1, 2)
    assert christmas.anchor == date(2025, 12, 25)
    assert christmas.n_days == 12


def test_calendar_can_be_filtered_by_year():
    calendar = build_cambridge_calendar(["2025-26"])
    assert all(i.academic_year == "2025-26" for i in calendar.instances)


def test_holiday_and_term_flags():
    calendar = default_calendar()
    assert all(i.kind.is_holiday for i in calendar.of_kind(PeriodKind.EASTER))
    assert all(i.kind.is_term for i in calendar.of_kind(PeriodKind.TERM))
    assert not calendar.of_kind(PeriodKind.TERM)[0].kind.is_holiday
