"""Sidebar controls: segment, comparison recipe, filters, exclusions, load."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analysis import get_available_modalities, resolve
from domain.models import (
    HOLIDAY_KINDS,
    Alignment,
    Calendar,
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
    FilterSettings,
)
from ui.components import attribution_footer
from ui.state import Controls, ensure_data

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DEFAULT_MODALITIES = ("pedestrian", "bike", "car", "heavy", "night")


def _fetch_range(
    instances, mode: ComparisonMode, earliest: date, today: date
) -> tuple[date, date] | None:
    if mode is ComparisonMode.TREND:
        return earliest, today + timedelta(days=1)
    starts = [i.start for i in instances if i.start]
    ends = [i.end for i in instances if i.end]
    if not starts or not ends:
        return None
    return min(starts), max(ends) + timedelta(days=1)


def _comparison_config(calendar: Calendar) -> ComparisonConfig:
    st.sidebar.subheader("Comparison")
    mode = st.sidebar.selectbox(
        "What to compare",
        list(ComparisonMode),
        format_func=lambda m: m.human,
    )
    config = ComparisonConfig(mode=mode)

    available_years = calendar.years()
    default_years = available_years
    selected_years = st.sidebar.multiselect(
        "Academic years", available_years, default=default_years
    )
    config.years = selected_years

    available_kinds = [k for k in HOLIDAY_KINDS if calendar.of_kind(k)]

    if mode is ComparisonMode.YEAR_ON_YEAR:
        if available_kinds:
            config.kind = st.sidebar.selectbox(
                "Holiday", available_kinds, format_func=lambda k: k.human
            )
            years_for_kind = {i.academic_year for i in calendar.of_kind(config.kind)}
            if len(years_for_kind) < 2:
                st.sidebar.warning(
                    "Only one year has this holiday. Add another academic year "
                    "in domain/calendars.py to compare year on year."
                )
        else:
            st.sidebar.warning("No holidays defined in the calendar.")

    elif mode is ComparisonMode.BY_KIND:
        config.kinds = st.sidebar.multiselect(
            "Holiday types",
            available_kinds,
            default=available_kinds,
            format_func=lambda k: k.human,
        )

    elif mode is ComparisonMode.BEFORE_AFTER:
        default_cutover = date.today() - timedelta(days=90)
        cutover = st.sidebar.date_input("Intervention date", value=default_cutover)
        config.cutover = cutover
        config.window_days = int(
            st.sidebar.slider(
                "Window (days each side)", 14, 180, 56, step=14
            )
        )
        config.include_previous_year = st.sidebar.checkbox(
            "Also show the same window last year", value=False
        )

    elif mode is ComparisonMode.CUSTOM:
        config.period_labels = st.sidebar.multiselect(
            "Periods", calendar.labels()
        )

    with st.sidebar.expander("Advanced"):
        config.alignment = st.selectbox(
            "Alignment",
            list(Alignment),
            index=0,
            format_func=lambda a: a.human,
        )

    return config


def _filters() -> None:
    st.sidebar.subheader("Filters")
    st.session_state["_hour_range"] = st.sidebar.slider(
        "Hours of day", 0, 23, (0, 23)
    )
    st.session_state["_day_labels"] = st.sidebar.multiselect(
        "Days of week", DAY_LABELS, default=DAY_LABELS
    )


def _exclusions() -> None:
    exclusions: list[Exclusion] = st.session_state["exclusions"]
    with st.sidebar.expander(f"Exclusions ({len(exclusions)})"):
        st.caption("Drop roadworks, closures or other anomalies from analysis.")
        for i, exclusion in enumerate(exclusions):
            col_a, col_b = st.columns([4, 1])
            spans = ", ".join(f"{s}→{e}" for s, e in exclusion.ranges)
            col_a.write(f"**{exclusion.label}**  \n{spans}")
            if col_b.button("Remove", key=f"exdel_{i}"):
                exclusions.pop(i)
                st.rerun()

        with st.form("add_exclusion", clear_on_submit=True):
            label = st.text_input("Label", placeholder="e.g. A14 roadworks")
            col_s, col_e = st.columns(2)
            start = col_s.date_input("From", value=date.today() - timedelta(days=7))
            end = col_e.date_input("To", value=date.today())
            if st.form_submit_button("Add exclusion"):
                if label and start <= end:
                    exclusions.append(Exclusion(label, ((start, end),)))
                    st.rerun()
                else:
                    st.warning("Provide a label and a valid date range.")


def _modalities(df) -> list[str]:
    available = get_available_modalities(df)
    defaults = [m for m in DEFAULT_MODALITIES if m in available]
    return st.sidebar.multiselect("Modalities", available, default=defaults)


def render_sidebar(config, calendar: Calendar) -> Controls:
    st.sidebar.title("Telraam Explorer")

    segment_id = st.sidebar.selectbox("Segment", config.segment_ids)

    comparison = _comparison_config(calendar)
    instances = resolve(calendar, comparison)

    _filters()
    _exclusions()

    st.sidebar.subheader("Data")
    fetch_range = _fetch_range(
        instances, comparison.mode, config.earliest_data, date.today()
    )

    df = None
    error: str | None = None

    if fetch_range is None:
        st.sidebar.info("Choose periods that cover at least one date.")
    else:
        start, end = fetch_range
        with st.spinner("Loading traffic data…"):
            df, error = ensure_data(segment_id, start, end)

    if error:
        st.sidebar.error(error)
    elif df is not None and not df.empty:
        st.sidebar.caption(f"{len(df):,} hourly rows loaded")
        if st.sidebar.button("Clear session cache"):
            from ui.state import reset_data

            reset_data()
            st.rerun()

    selected_modalities = _modalities(df) if df is not None else []

    hour_range = st.session_state.get("_hour_range", (0, 23))
    day_labels = st.session_state.get("_day_labels", DAY_LABELS)
    filters = FilterSettings(
        start_hour=hour_range[0],
        end_hour=hour_range[1],
        selected_days=[DAY_LABELS.index(d) for d in day_labels],
        selected_modalities=selected_modalities,
    )

    attribution_footer(segment_id)

    controls = Controls(
        segment_id=segment_id,
        filters=filters,
        comparison=comparison,
        exclusions=list(st.session_state["exclusions"]),
        instances=instances,
        df=df if df is not None else pd.DataFrame(),
        error=error,
    )
    return controls
