"""In-page comparison-axis control.

The comparison axis only changes how the comparison charts group the loaded
data, so it lives inside the pages that use it (Compare and Detail) rather than
the sidebar's global filters. Each page passes a distinct *key_prefix* so the
two pages keep independent choices.
"""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from analysis import resolve
from domain.models import (
    HOLIDAY_KINDS,
    Calendar,
    ComparisonConfig,
    ComparisonMode,
    InterventionFilter,
    PeriodInstance,
)


def comparison_axis(
    calendar: Calendar, key_prefix: str
) -> tuple[ComparisonConfig, list[PeriodInstance]]:
    """Render the grouping controls inline and resolve the chosen periods."""
    mode = st.selectbox(
        "Group charts by",
        list(ComparisonMode),
        format_func=lambda m: m.human,
        key=f"{key_prefix}_comparison_mode",
        help="How rows are grouped in the comparison charts. Changing this "
        "does not re-download data.",
    )
    config = ComparisonConfig(mode=mode)

    # Every academic year is always included; the loaded time range, not a
    # year picker, decides which dates are actually analysed.
    available_kinds = [k for k in HOLIDAY_KINDS if calendar.of_kind(k)]

    if mode is ComparisonMode.YEAR_ON_YEAR:
        if available_kinds:
            config.kind = st.selectbox(
                "Holiday",
                available_kinds,
                format_func=lambda k: k.human,
                key=f"{key_prefix}_comparison_kind",
            )
            years_for_kind = {
                i.academic_year for i in calendar.of_kind(config.kind)
            }
            if len(years_for_kind) < 2:
                st.warning(
                    "Only one year has this holiday. Add another academic year "
                    "in domain/calendars.py to compare year on year."
                )
        else:
            st.warning("No holidays defined in the calendar.")

    elif mode is ComparisonMode.BEFORE_AFTER:
        default_cutover = date.today() - timedelta(days=90)
        config.cutover = st.date_input(
            "Intervention date",
            value=default_cutover,
            key=f"{key_prefix}_comparison_cutover",
        )
        config.window_days = int(
            st.slider(
                "Window (days each side)",
                14,
                180,
                56,
                step=14,
                key=f"{key_prefix}_comparison_window",
            )
        )
        config.include_previous_year = st.checkbox(
            "Also show the same window last year",
            value=False,
            key=f"{key_prefix}_comparison_prev_year",
        )
        config.date_filter = st.selectbox(
            "Dates to compare",
            list(InterventionFilter),
            format_func=lambda f: f.human,
            key=f"{key_prefix}_comparison_date_filter",
            help="Restrict both windows to term time or holidays so like is "
            "compared with like. Holidays falling in a window are dropped "
            "when only term dates are compared, and vice versa.",
        )

    elif mode is ComparisonMode.CUSTOM:
        config.period_labels = st.multiselect(
            "Periods",
            calendar.labels(),
            key=f"{key_prefix}_comparison_periods",
        )

    elif mode is ComparisonMode.ROADWORKS:
        if not st.session_state.get("exclusions"):
            st.info(
                "Add an exclusion in the sidebar to compare roadworks against "
                "the baseline."
            )

    return config, resolve(calendar, config)
