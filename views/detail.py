"""Detail view: the periods, totals and shares behind the charts."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    compute_modal_split,
    compute_period_totals,
)
from ui.components import (
    aggregate_table,
    csv_download,
    period_summary,
    require_modalities,
)
from ui.grouping import comparison_axis
from ui.state import get_calendar, get_controls, prepared_df
from ui.theme import page_header

GROUP_COL = "group_label"


def render() -> None:
    page_header("Detail", "The periods, totals and shares behind the charts.")
    controls = get_controls()
    modalities = require_modalities(controls)
    if modalities is None:
        return

    comparison, instances = comparison_axis(get_calendar(), "detail")

    period_summary(instances, caption="Periods marked on the trend charts.")

    if controls.exclusions:
        st.subheader("Excluded ranges")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Label": e.label,
                        "Ranges": ", ".join(f"{s} → {d}" for s, d in e.ranges),
                    }
                    for e in controls.exclusions
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    grouped = prepared_df(
        keep_only_assigned=True, comparison=comparison, instances=instances
    )
    if grouped.empty:
        st.info("No data matches the current comparison.")
        return

    st.divider()
    st.subheader("Totals by group")
    totals = compute_period_totals(grouped, modalities, group_col=GROUP_COL)
    aggregate_table(totals, "Group", decimals=0)
    csv_download(totals, "period_totals.csv", "Download totals (CSV)")

    st.subheader("Modal split (%)")
    split = compute_modal_split(grouped, modalities, group_col=GROUP_COL)
    aggregate_table(split, "Group", decimals=1)
    csv_download(split, "modal_split.csv", "Download modal split (CSV)")

    st.caption(
        "Only derived aggregates are exportable. Raw Telraam data is subject "
        "to the CC BY-NC 4.0 licence."
    )
