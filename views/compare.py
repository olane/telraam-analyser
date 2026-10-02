"""Compare view: weekday-aligned comparison of the chosen comparison axis."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_hourly_profile,
    compute_modal_split,
    compute_weekday_totals,
)
from charts import (
    plot_hourly_profile,
    plot_modal_split,
    plot_weekday_comparison,
)
from ui.components import period_summary
from ui.state import get_controls, prepared_df
from ui.theme import page_header

GROUP_COL = "group_label"


def render() -> None:
    page_header(
        "Compare",
        "Like weekdays against like weekdays, grouped by your comparison axis.",
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
        st.warning("No data matches the current filters or comparison.")
        return

    period_summary(
        controls.instances, caption="Periods marked on the trend charts."
    )
    st.divider()

    daily = compute_daily_totals(df, modalities, group_col=GROUP_COL)
    weekday_df = compute_weekday_totals(
        daily, modalities, group_col=GROUP_COL
    )

    modality = st.selectbox("Modality", modalities, key="compare_modality")
    st.plotly_chart(
        plot_weekday_comparison(weekday_df, modality, group_col=GROUP_COL),
        use_container_width=True,
        key="compare_weekday",
    )

    st.divider()
    st.subheader("Hourly profile")
    profile = compute_hourly_profile(df, modalities, group_col=GROUP_COL)
    st.plotly_chart(
        plot_hourly_profile(profile, modalities, group_col=GROUP_COL),
        use_container_width=True,
        key="compare_hourly",
    )

    st.divider()
    st.subheader("Modal split")
    split = compute_modal_split(df, modalities, group_col=GROUP_COL)
    st.plotly_chart(
        plot_modal_split(split, modalities, group_col=GROUP_COL),
        use_container_width=True,
        key="compare_modal",
    )
