"""Detail view: speed, data tables and export of derived aggregates."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_modal_split,
    compute_period_totals,
    compute_speed_distribution,
    compute_speed_summary,
)
from charts import plot_speed_distribution
from ui.components import csv_download
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def render() -> None:
    page_header("Detail", "Speed, shares and the numbers behind the charts.")
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

    unit = st.radio("Speed unit", ["mph", "km/h"], horizontal=True)

    summary = compute_speed_summary(df, unit=unit)
    if summary is not None and not summary.empty:
        st.subheader("Speed comparison")
        st.dataframe(summary, use_container_width=True, hide_index=True)

        speed = compute_speed_distribution(df, unit=unit)
        if speed is not None and not speed.empty:
            st.plotly_chart(
                plot_speed_distribution(speed, unit=unit),
                use_container_width=True,
                key="detail_speed",
            )
            csv_download(
                speed, "speed_distribution.csv", "Download speed data (CSV)"
            )
    else:
        st.info("No speed data is available for this segment or selection.")

    st.divider()
    st.subheader("Totals by period")
    totals = compute_period_totals(df, modalities)
    st.dataframe(totals, use_container_width=True, hide_index=True)
    csv_download(totals, "period_totals.csv", "Download totals (CSV)")

    st.subheader("Modal split (%)")
    split = compute_modal_split(df, modalities)
    st.dataframe(split, use_container_width=True, hide_index=True)
    csv_download(split, "modal_split.csv", "Download modal split (CSV)")

    st.caption(
        "Only derived aggregates are exportable. Raw Telraam data is subject "
        "to the CC BY-NC 4.0 licence."
    )
