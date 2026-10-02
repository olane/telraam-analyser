"""Detail view: the periods, totals and shares behind the charts."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_modal_split,
    compute_period_totals,
)
from ui.components import aggregate_table, csv_download, period_summary
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def render() -> None:
    page_header("Detail", "The periods, totals and shares behind the charts.")
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

    period_summary(
        controls.instances, caption="Periods marked on the trend charts."
    )

    grouped = prepared_df(keep_only_assigned=True)
    if grouped.empty:
        st.info("No data matches the current comparison.")
        return

    st.divider()
    st.subheader("Totals by group")
    totals = compute_period_totals(grouped, modalities, group_col="group_label")
    aggregate_table(totals, "Group", decimals=0)
    csv_download(totals, "period_totals.csv", "Download totals (CSV)")

    st.subheader("Modal split (%)")
    split = compute_modal_split(grouped, modalities, group_col="group_label")
    aggregate_table(split, "Group", decimals=1)
    csv_download(split, "modal_split.csv", "Download modal split (CSV)")

    st.caption(
        "Only derived aggregates are exportable. Raw Telraam data is subject "
        "to the CC BY-NC 4.0 licence."
    )
