from __future__ import annotations

from datetime import date

from analysis.comparisons import (
    build_before_after,
    holiday_vs_term,
    resolve,
    year_on_year,
)
from domain.calendars import default_calendar
from domain.models import (
    ComparisonConfig,
    ComparisonMode,
    InterventionFilter,
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


def test_before_after_term_filter_clips_each_window():
    calendar = default_calendar()
    before, after = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.BEFORE_AFTER,
            cutover=date(2026, 2, 23),
            window_days=28,
            date_filter=InterventionFilter.TERM_ONLY,
        ),
    )
    # The before window stops at the start of the February half term.
    assert before.ranges == ((date(2026, 1, 26), date(2026, 2, 13)),)
    # The after window sits entirely inside Spring 2 term time.
    assert after.ranges == ((date(2026, 2, 23), date(2026, 3, 22)),)


def test_before_after_holiday_filter_isolates_holidays():
    calendar = default_calendar()
    before, after = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.BEFORE_AFTER,
            cutover=date(2026, 2, 23),
            window_days=28,
            date_filter=InterventionFilter.HOLIDAYS_ONLY,
        ),
    )
    assert before.ranges == ((date(2026, 2, 16), date(2026, 2, 20)),)
    # No holiday falls in the after window, so it has no compared dates.
    assert after.ranges == ()


def test_before_after_previous_year_is_clipped_per_year():
    calendar = default_calendar()
    instances = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.BEFORE_AFTER,
            cutover=date(2026, 12, 14),
            window_days=14,
            include_previous_year=True,
            date_filter=InterventionFilter.HOLIDAYS_ONLY,
        ),
    )
    assert len(instances) == 3
    # The baseline is clipped against the previous year's calendar.
    assert instances[2].ranges == ((date(2025, 12, 22), date(2025, 12, 28)),)


def test_holiday_vs_term_groups():
    calendar = default_calendar()
    instances = holiday_vs_term(calendar)
    labels = [i.label for i in instances]
    assert labels == ["Term time", "School holidays"]
    assert len(instances[1].ranges) == len(
        [i for i in calendar.instances if i.kind.is_holiday]
    )


def test_year_on_year_returns_one_per_year():
    instances = year_on_year(default_calendar(), PeriodKind.CHRISTMAS)
    assert len(instances) == 2
    assert all(i.kind is PeriodKind.CHRISTMAS for i in instances)
    assert [i.academic_year for i in instances] == ["2025-26", "2026-27"]


def test_axis_modes_mark_every_period():
    """Time/weekday/roadworks axes need no calendar subset: mark them all."""
    calendar = default_calendar()
    for mode in (
        ComparisonMode.WEEKDAY_VS_WEEKEND,
        ComparisonMode.TIME_OF_DAY,
        ComparisonMode.ROADWORKS,
    ):
        instances = resolve(calendar, ComparisonConfig(mode=mode))
        assert len(instances) == len(calendar.instances)


def test_axis_modes_can_filter_by_year():
    calendar = default_calendar()
    instances = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.TIME_OF_DAY, years=["2025-26"]
        ),
    )
    assert all(i.academic_year == "2025-26" for i in instances)


def test_resolve_dispatches_by_mode():
    calendar = default_calendar()

    before_after = resolve(
        calendar,
        ComparisonConfig(
            mode=ComparisonMode.BEFORE_AFTER,
            cutover=date(2025, 6, 1),
            window_days=14,
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
