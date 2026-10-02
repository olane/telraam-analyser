"""Reusable UI components."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    compute_typical_week,
    dedupe_modalities,
    describe_instances,
    weekday_hour_matrix,
)
from charts import plot_typical_week
from domain.models import ComparisonConfig, PeriodInstance

LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
TELRAAM_URL = "https://telraam.net/"

ALL_OPTION = "All"


def format_pct_change(before: float, after: float) -> str | None:
    """Signed percentage change from *before* to *after*, or None if undefined."""
    if not before:
        return None
    return f"{(after - before) / before * 100:+.1f}%"


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


def _resolve_modality(df, modalities, choice):
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


def _ordered_groups(df, group_col: str) -> list[str]:
    """Return the comparison groups present in *df* in their canonical order."""
    labels = df[group_col].dropna()
    if hasattr(labels, "cat"):
        present = set(labels)
        return [g for g in labels.cat.categories if g in present]
    return list(dict.fromkeys(labels))


def typical_week_heatmaps(
    df,
    modalities: list[str],
    choice: str,
    comparison: ComparisonConfig,
    group_col: str = "group_label",
    key_prefix: str = "typical",
) -> None:
    """One typical-week heatmap per comparison group.

    The comparison axis decides the groups (e.g. weekday/weekend or
    term/holiday), so the number of plots follows the selected comparison.
    """
    assigned = df[df[group_col].notna()]
    if assigned.empty:
        st.info("No data matches the current comparison.")
        return

    st.subheader("Typical week by group")
    st.caption(
        f"Average week broken down by {comparison.mode.human.lower()} "
        "— one plot per comparison group."
    )
    frame, column, display = _resolve_modality(assigned, modalities, choice)
    typical = compute_typical_week(frame, [column], group_col=group_col)
    columns = st.columns(2)
    for i, group in enumerate(_ordered_groups(assigned, group_col)):
        matrix = weekday_hour_matrix(
            typical, group, column, group_col=group_col
        )
        columns[i % 2].plotly_chart(
            plot_typical_week(
                matrix, title=f"Typical week — {group} — {display}"
            ),
            use_container_width=True,
            key=f"{key_prefix}_{group}",
        )
