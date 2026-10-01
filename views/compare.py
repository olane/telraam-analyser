"""Compare view: weekday-aligned comparison of the selected periods."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_hourly_profile,
    compute_modal_split,
    compute_weekday_occurrence_totals,
    compute_weekday_totals,
)
from charts import (
    plot_hourly_profile,
    plot_modal_split,
    plot_weekday_comparison,
    plot_weekday_occurrence,
)
from ui.components import period_summary
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def render() -> None:
    page_header(
        "Compare",
        "Like weekdays against like weekdays, across the selected periods.",
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

    df = prepared_df(keep_only_assigned=True)
    if df.empty:
        st.warning("No data matches the current filters or periods.")
        return

    period_summary(controls.instances)
    st.divider()

    daily = compute_daily_totals(df, modalities)
    weekday_df = compute_weekday_totals(daily, modalities)

    modality = st.selectbox("Modality", modalities, key="compare_modality")
    st.plotly_chart(
        plot_weekday_comparison(weekday_df, modality),
        use_container_width=True,
        key="compare_weekday",
    )

    shows_multiple_weeks = (
        not daily.empty
        and (daily.groupby("period_label")["day"].nunique().max() > 7)
    )
    if shows_multiple_weeks:
        if st.checkbox("Break down by week (nth weekday in period)"):
            occurrence = compute_weekday_occurrence_totals(daily, [modality])
            st.plotly_chart(
                plot_weekday_occurrence(occurrence, modality),
                use_container_width=True,
                key="compare_occurrence",
            )

    st.divider()
    st.subheader("Hourly profile")
    profile = compute_hourly_profile(df, modalities)
    st.plotly_chart(
        plot_hourly_profile(profile, modalities),
        use_container_width=True,
        key="compare_hourly",
    )

    st.divider()
    st.subheader("Modal split")
    split = compute_modal_split(df, modalities)
    st.plotly_chart(
        plot_modal_split(split, modalities),
        use_container_width=True,
        key="compare_modal",
    )
