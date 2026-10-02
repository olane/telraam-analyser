"""Trends view: long-term trend, weekday-adjusted trend, typical week."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_daily_trend,
    compute_typical_week,
    compute_weekday_totals,
    dedupe_modalities,
    term_status,
    weekday_adjusted_trend,
    weekday_hour_matrix,
)
from charts import (
    plot_daily_trend,
    plot_typical_week,
    plot_weekday_adjusted_trend,
    plot_weekday_comparison,
)
from domain.models import NOT_TERM_LABEL, TERM_LABEL
from ui.state import get_controls, prepared_df
from ui.theme import page_header

ALL_OPTION = "All"
GROUP_COL = "group_label"


def _modality_frame(df, modalities: list[str], choice: str):
    """Resolve a modality choice to (frame, column, display name).

    When *choice* is ``"All"`` a combined ``total`` column is added so the
    single-column aggregations can be reused unchanged. Combined modes whose
    direction split is also selected are dropped to avoid double counting.
    """
    if choice == ALL_OPTION:
        frame = df.copy()
        columns = dedupe_modalities(list(modalities))
        frame["total"] = frame[columns].sum(axis=1)
        return frame, "total", "all selected modalities"
    return df, choice, choice


def render() -> None:
    page_header(
        "Trends",
        "How traffic moves through time, with holidays and exclusions marked.",
    )
    controls = get_controls()

    if controls.error:
        st.error(controls.error)
        return
    if controls.df is None or controls.df.empty:
        st.info("No data loaded. Adjust the periods in the sidebar.")
        return

    modalities = controls.filters.selected_modalities
    if not modalities:
        st.warning("Select at least one modality in the sidebar.")
        return

    df = prepared_df()
    if df.empty:
        st.warning("No data matches the current filters.")
        return

    top_left, top_right = st.columns([2, 1])
    trend_choice = top_left.selectbox(
        "Trend modality",
        [ALL_OPTION, *modalities],
        key="trend_modality",
        help="Show a single mode, or the combined total of every mode selected "
        "in the sidebar.",
    )
    window = top_right.slider("Rolling average (days)", 3, 28, 7)

    trend_modalities = (
        modalities if trend_choice == ALL_OPTION else [trend_choice]
    )
    trend_label = (
        "all selected modalities" if trend_choice == ALL_OPTION else trend_choice
    )

    trend = compute_daily_trend(df, trend_modalities, window)
    st.plotly_chart(
        plot_daily_trend(
            trend,
            instances=controls.instances,
            exclusions=controls.exclusions,
            title=f"Traffic trend — {trend_label}",
            rolling_label=f"{window}-day average",
        ),
        use_container_width=True,
        key="trend_daily",
    )

    st.subheader("Weekday-adjusted trend")
    st.caption(
        "Each day is shown relative to the average for that weekday, so the "
        "weekly cycle doesn't hide the underlying direction of travel."
    )
    adjusted = weekday_adjusted_trend(df, trend_modalities)
    st.plotly_chart(
        plot_weekday_adjusted_trend(
            adjusted,
            instances=controls.instances,
            exclusions=controls.exclusions,
            title=f"Weekday-adjusted trend — {trend_label}",
        ),
        use_container_width=True,
        key="trend_weekday_adjusted",
    )

    assigned = df[df[GROUP_COL].notna()]
    if assigned.empty:
        st.info("No data matches the current comparison.")
        return

    st.subheader("Weekday comparison")
    comparison_choice = st.selectbox(
        "Weekday comparison modality",
        [ALL_OPTION, *modalities],
        key="trend_wd_modality",
        help="Show a single mode, or the combined total of every mode selected "
        "in the sidebar.",
    )
    daily_frame, daily_col, daily_display = _modality_frame(
        assigned, modalities, comparison_choice
    )
    daily = compute_daily_totals(
        daily_frame, [daily_col], group_col=GROUP_COL
    )
    weekday_df = compute_weekday_totals(
        daily, [daily_col], group_col=GROUP_COL
    )
    st.plotly_chart(
        plot_weekday_comparison(
            weekday_df, daily_col, group_col=GROUP_COL
        ),
        use_container_width=True,
        key="trend_weekday_comparison",
    )

    st.subheader("Typical week")
    st.caption(
        "Term time versus not term time — average week, all matching days "
        "rolled together."
    )
    typical_frame, typical_col, typical_display = _modality_frame(
        df, modalities, comparison_choice
    )
    typical_frame["term_group"] = term_status(typical_frame)
    typical = compute_typical_week(
        typical_frame, [typical_col], group_col="term_group"
    )
    left, right = st.columns(2)
    for column, status in ((left, TERM_LABEL), (right, NOT_TERM_LABEL)):
        matrix = weekday_hour_matrix(
            typical, status, typical_col, group_col="term_group"
        )
        column.plotly_chart(
            plot_typical_week(
                matrix, title=f"Typical week — {status} — {typical_display}"
            ),
            use_container_width=True,
            key=f"trend_typical_{status}",
        )
