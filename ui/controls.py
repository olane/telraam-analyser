"""Sidebar: pick a sensor and time range, then the periods and filters.

Downloading is decoupled from analysis: the time range fetches everything
(cached, rate limits excepted), and the grouping recipe only decides which
periods get labelled in the already-loaded data.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analysis import (
    WEEKDAY_LABELS,
    dedupe_modalities,
    get_available_modalities,
    resolve,
)
from domain.models import (
    HOLIDAY_KINDS,
    NIGHT_DISTRIBUTION_DEFAULT,
    NIGHT_DISTRIBUTION_TARGETS,
    Calendar,
    ComparisonConfig,
    ComparisonMode,
    Exclusion,
    FilterSettings,
    InterventionFilter,
    NightRedistribution,
    PeriodInstance,
    PeriodKind,
    base_of,
    is_directional,
    modality_label,
)
from ui.components import attribution_footer
from ui.state import Controls, ensure_data

DEFAULT_MODALITIES = ("pedestrian", "bike", "car", "heavy", "night")

# Views that group the loaded frame into comparison buckets. Trends marks raw
# calendar periods instead, so it gets a "Mark periods" control rather than
# the comparison axis.
GROUPING_PAGES = ("Overview", "Compare", "Detail")
TRENDS_PAGE = "Trends"

# Range presets in days. ``None`` means "everything since the API's earliest
# data"; ``CUSTOM_RANGE`` asks for explicit dates.
RANGE_PRESETS: dict[str, int | None] = {
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last 6 months": 182,
    "Last 12 months": 365,
    "All time": None,
    "Custom range": -1,
}
CUSTOM_RANGE = "Custom range"
DEFAULT_RANGE = "All time"


def _date_range(config) -> tuple[date, date]:
    """Sensor-independent date range to download, end exclusive."""
    preset = st.sidebar.selectbox(
        "Date range",
        list(RANGE_PRESETS),
        index=list(RANGE_PRESETS).index(DEFAULT_RANGE),
    )

    if preset == CUSTOM_RANGE:
        default_start = date.today() - timedelta(days=365)
        col_start, col_end = st.sidebar.columns(2)
        start = col_start.date_input("From", value=default_start, key="range_start")
        end = col_end.date_input("To", value=date.today(), key="range_end")
        return start, end + timedelta(days=1)

    span = RANGE_PRESETS[preset]
    end = date.today() + timedelta(days=1)
    if span is None:
        return config.earliest_data, end
    return date.today() - timedelta(days=span - 1), end


def _load(segment_id: str, start: date, end: date) -> tuple[pd.DataFrame | None, str | None]:
    """Fetch (or reuse) the rows for the selected range, reporting status."""
    if start >= end:
        st.sidebar.info("Choose a time range that covers at least one date.")
        return None, None

    with st.spinner("Loading traffic data…"):
        df, error = ensure_data(segment_id, start, end)

    if error:
        st.sidebar.error(error)
    elif df is not None and not df.empty:
        st.sidebar.caption(f"{len(df):,} hourly rows loaded")
    return df, error


def _grouping(calendar: Calendar, page_title: str) -> ComparisonConfig:
    """Choose the comparison axis used to group the comparison charts."""
    if page_title not in GROUPING_PAGES:
        return ComparisonConfig()

    mode = st.sidebar.selectbox(
        "Group charts by",
        list(ComparisonMode),
        format_func=lambda m: m.human,
        help="How rows are grouped in the comparison charts. Changing this "
        "does not re-download data.",
    )
    config = ComparisonConfig(mode=mode)

    # Every academic year is always included; the loaded time range, not a
    # year picker, decides which dates are actually analysed.
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

    elif mode is ComparisonMode.BEFORE_AFTER:
        default_cutover = date.today() - timedelta(days=90)
        config.cutover = st.sidebar.date_input(
            "Intervention date", value=default_cutover
        )
        config.window_days = int(
            st.sidebar.slider("Window (days each side)", 14, 180, 56, step=14)
        )
        config.include_previous_year = st.sidebar.checkbox(
            "Also show the same window last year", value=False
        )
        config.date_filter = st.sidebar.selectbox(
            "Dates to compare",
            list(InterventionFilter),
            format_func=lambda f: f.human,
            help="Restrict both windows to term time or holidays so like is "
            "compared with like. Holidays falling in a window are dropped "
            "when only term dates are compared, and vice versa.",
        )

    elif mode is ComparisonMode.CUSTOM:
        config.period_labels = st.sidebar.multiselect(
            "Periods", calendar.labels()
        )

    elif mode is ComparisonMode.ROADWORKS:
        if not st.session_state.get("exclusions"):
            st.sidebar.info(
                "Add an exclusion below to compare roadworks against the "
                "baseline."
            )

    return config


def _mark_periods(calendar: Calendar) -> list[PeriodInstance]:
    """Choose which calendar periods are shaded on the trend charts.

    Annotation is independent of the comparison axis, so Trends can keep
    showing term boundaries and holiday bands while the other views group the
    same data differently.
    """
    kinds = [k for k in PeriodKind if calendar.of_kind(k)]
    chosen = st.sidebar.multiselect(
        "Mark periods",
        kinds,
        default=kinds,
        format_func=lambda k: k.human,
        help="Calendar periods shaded on the trend charts. Independent of how "
        "the other views group the data.",
    )
    return [i for i in calendar.instances if i.kind in chosen]


def _night_redistribution(df) -> NightRedistribution:
    """Global toggle and per-mode shares for moving night into other modes.

    Night detections are headlights only, so the camera cannot classify them.
    When on, those counts are added to the chosen modes and the night buckets
    disappear; when off, night is left as its own mode.
    """
    targets = (
        [t for t in NIGHT_DISTRIBUTION_TARGETS if t in df.columns]
        if df is not None
        else []
    )

    enabled = st.sidebar.checkbox(
        "Redistribute night into other modes",
        value=True,
        key="night_redistribute_enabled",
        disabled=not targets,
        help="Night detections are headlights only and cannot be classified. "
        "When on, they are moved into the modes below and night is hidden; "
        "when off, night is shown as its own mode.",
    )
    if not targets:
        st.sidebar.caption(
            "No night data for this segment, so there is nothing to redistribute."
        )
        return NightRedistribution(enabled=False)

    shares = dict(NIGHT_DISTRIBUTION_DEFAULT)
    if enabled:
        with st.sidebar.expander("Night proportions"):
            st.caption(
                "Assumed split of night detections per mode. Weights are "
                "normalised, so they need not sum to 100%."
            )
            raw: dict[str, float] = {}
            for target in targets:
                default = int(
                    round(NIGHT_DISTRIBUTION_DEFAULT.get(target, 0.0) * 100)
                )
                raw[target] = st.slider(
                    f"{modality_label(target)} (%)",
                    0,
                    100,
                    default,
                    key=f"night_share_{target}",
                )
            total = sum(raw.values())
            if total <= 0:
                st.warning(
                    "At least one mode must receive a share of the night; "
                    "using the defaults instead."
                )
            else:
                shares = {target: value / total for target, value in raw.items()}

    return NightRedistribution(enabled=enabled, shares=shares)


def _filters(df, hide_night: bool = False) -> list[str]:
    """Global filters applied by every view; returns selected modalities."""
    available = get_available_modalities(df) if df is not None else []
    if hide_night:
        available = [m for m in available if base_of(m) != "night"]
    combined = [m for m in available if not is_directional(m)]
    variants = [m for m in available if is_directional(m)]

    defaults = [m for m in DEFAULT_MODALITIES if m in combined]
    selected = list(
        st.sidebar.multiselect(
            "Modalities",
            combined,
            default=defaults,
            format_func=modality_label,
            help="Combined counts per transport mode.",
        )
    )

    selected_variants: list[str] = []
    with st.sidebar.expander("Advanced filters"):
        st.session_state["_hour_range"] = st.slider(
            "Hours of day", 0, 23, (0, 23)
        )
        st.session_state["_day_labels"] = st.multiselect(
            "Days of week", WEEKDAY_LABELS, default=WEEKDAY_LABELS
        )
        if variants:
            st.divider()
            split = st.checkbox(
                "Split by direction (left / right)",
                value=False,
                help="Use the S2 left/right variants. Selecting a direction "
                "replaces its combined total so counts are not double counted.",
            )
            if split:
                selected_variants = st.multiselect(
                    "Directional modalities",
                    variants,
                    default=[m for m in variants if base_of(m) in selected],
                    format_func=modality_label,
                )

    # Never sum a combined mode and its direction split together.
    return dedupe_modalities(selected + list(selected_variants))


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


def _page_nav(pages) -> None:
    """Page links, placed after the data controls so views follow loading."""
    st.sidebar.subheader("View")
    for page in pages:
        st.sidebar.page_link(
            page, label=page.title, icon=page.icon, use_container_width=True
        )


def render_sidebar(config, calendar: Calendar, pages, current_page) -> Controls:
    st.sidebar.title("Telraam Explorer")
    page_title = getattr(current_page, "title", "")

    # -- Data: sensor + download range -----------------------------------
    st.sidebar.subheader("Data")
    segment_id = st.sidebar.selectbox("Segment", config.segment_ids)
    start, end = _date_range(config)
    df, error = _load(segment_id, start, end)

    # -- View: which page to read ----------------------------------------
    _page_nav(pages)

    # -- View settings: how the loaded data is interpreted ----------------
    st.sidebar.subheader("View settings")
    comparison = _grouping(calendar, page_title)
    instances = (
        _mark_periods(calendar)
        if page_title == TRENDS_PAGE
        else resolve(calendar, comparison)
    )

    night = _night_redistribution(df)
    selected_modalities = _filters(df, hide_night=night.enabled)
    _exclusions()

    hour_range = st.session_state.get("_hour_range", (0, 23))
    day_labels = st.session_state.get("_day_labels", WEEKDAY_LABELS)
    filters = FilterSettings(
        start_hour=hour_range[0],
        end_hour=hour_range[1],
        selected_days=[WEEKDAY_LABELS.index(d) for d in day_labels],
        selected_modalities=selected_modalities,
    )

    attribution_footer(segment_id)

    return Controls(
        segment_id=segment_id,
        filters=filters,
        exclusions=list(st.session_state["exclusions"]),
        instances=instances,
        comparison=comparison,
        night=night,
        df=df if df is not None else pd.DataFrame(),
        error=error,
    )
