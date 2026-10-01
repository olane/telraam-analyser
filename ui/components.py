"""Reusable UI components."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import describe_instances
from domain.models import PeriodInstance

LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
TELRAAM_URL = "https://telraam.net/"


def kpi_row(items: list[dict]) -> None:
    """Render a row of KPI metrics. Each item: {label, value, delta?, help?}."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.metric(
            item["label"],
            item.get("value", "—"),
            delta=item.get("delta"),
            help=item.get("help"),
        )


def period_summary(instances: list[PeriodInstance], caption: str = "") -> None:
    """Show the selected periods in a compact table."""
    if not instances:
        st.info("No periods selected.")
        return
    if caption:
        st.caption(caption)
    st.dataframe(
        describe_instances(instances),
        use_container_width=True,
        hide_index=True,
    )


def csv_download(
    df: pd.DataFrame, filename: str, label: str = "Download CSV"
) -> None:
    if df is None or df.empty:
        return
    st.download_button(
        label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def attribution_footer(segment_id: str | None = None) -> None:
    seg = f" · segment {segment_id}" if segment_id else ""
    st.markdown(
        '<div class="attribution">'
        f'Data © <a href="{TELRAAM_URL}">Telraam</a>, licensed under '
        f'<a href="{LICENSE_URL}">CC BY-NC 4.0</a>{seg}. '
        "Non-commercial use only. This tool shows derived aggregates."
        "</div>",
        unsafe_allow_html=True,
    )
