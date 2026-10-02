from __future__ import annotations

from datetime import date

from domain.calendars import build_cambridge_calendar, default_calendar
from domain.models import PeriodKind


def test_default_calendar_has_expected_instances():
    calendar = default_calendar()
    assert calendar.name == "Cambridge"
    assert calendar.years() == ["2025-26", "2026-27"]
    assert len(calendar.of_kind(PeriodKind.TERM)) == 12
    assert len(calendar.of_kind(PeriodKind.CHRISTMAS)) == 2


def test_labels_are_unique():
    labels = default_calendar().labels()
    assert len(labels) == len(set(labels))


def test_christmas_dates():
    christmas = default_calendar().of_kind(PeriodKind.CHRISTMAS)[0]
    assert christmas.start == date(2025, 12, 22)
    assert christmas.end == date(2026, 1, 2)
    assert christmas.n_days == 12


def test_summer_holiday_is_present():
    summer = default_calendar().of_kind(PeriodKind.SUMMER)
    assert {i.academic_year for i in summer} == {"2025-26", "2026-27"}
    first = next(i for i in summer if i.academic_year == "2025-26")
    assert first.start == date(2026, 7, 21)
    assert first.end == date(2026, 8, 31)
    assert first.kind.is_holiday


def test_calendar_can_be_filtered_by_year():
    calendar = build_cambridge_calendar(["2025-26"])
    assert all(i.academic_year == "2025-26" for i in calendar.instances)


def test_holiday_and_term_flags():
    calendar = default_calendar()
    assert all(i.kind.is_holiday for i in calendar.of_kind(PeriodKind.EASTER))
    assert all(i.kind.is_term for i in calendar.of_kind(PeriodKind.TERM))
    assert not calendar.of_kind(PeriodKind.TERM)[0].kind.is_holiday
