from __future__ import annotations

from datetime import date

from analysis.comparisons import (
    build_before_after,
    by_kind,
    holiday_vs_term,
    latest_year,
    resolve,
    year_on_year,
)
from domain.calendars import default_calendar
from domain.models import (
    Alignment,
    ComparisonConfig,
    ComparisonMode,
    PeriodKind,
)


def test_before_after_windows_are_adjacent():
    instances = build_before_after(date(2025, 6, 1), window_days=28)
    before, after = instances
    assert before.end == date(2025, 5, 31)
    assert after.start == date(2025, 6, 1)
    assert after.end == date(2025, 6, 28)
    assert before.n_days == 28
    assert after.n_days == 28


def test_before_after_previous_year_option():
    instances = build_before_after(
        date(2025, 6, 1), window_days=28, include_previous_year=True
    )
    assert len(instances) == 3
    baseline = instances[2]
    assert len(baseline.ranges) == 2


def test_holiday_vs_term_groups():
    calendar = default_calendar()
    instances = holiday_vs_term(calendar)
    labels = [i.label for i in instances]
    assert labels == ["Term time", "School holidays"]
    assert len(instances[1].ranges) == len(
        [i for i in calendar.instances if i.kind.is_holiday]
    )


def test_year_on_year_single_year_returns_one():
    instances = year_on_year(default_calendar(), PeriodKind.CHRISTMAS)
    assert len(instances) == 1
    assert instances[0].kind is PeriodKind.CHRISTMAS


def test_by_kind_returns_holidays_for_year():
    instances = by_kind(default_calendar(), [PeriodKind.EASTER, PeriodKind.MAY_HALF])
    assert {i.kind for i in instances} == {PeriodKind.EASTER, PeriodKind.MAY_HALF}
    assert all(i.academic_year == "2025-26" for i in instances)


def test_latest_year():
    assert latest_year(default_calendar()) == "2025-26"


def test_resolve_dispatches_by_mode():
    calendar = default_calendar()

    trend = resolve(
        calendar,
        ComparisonConfig(mode=ComparisonMode.TREND),
    )
    assert len(trend) == len(calendar.instances)

    before_after = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.BEFORE_AFTER,
            cutover=date(2025, 6, 1),
            window_days=14,
            alignment=Alignment.WEEKDAY,
        ),
    )
    assert len(before_after) == 2

    custom = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.CUSTOM,
            period_labels=["Christmas holiday 2025-26"],
        ),
    )
    assert [i.label for i in custom] == ["Christmas holiday 2025-26"]
