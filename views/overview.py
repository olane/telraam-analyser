"""Overview view: headline numbers for the current selection."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    compute_period_totals,
    daily_total_series,
    period_mean_daily,
)
from ui.components import format_pct_change, kpi_row, period_summary
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def _mean_daily(df: pd.DataFrame, modalities: list[str]) -> float | None:
    if df.empty or not modalities:
        return None
    total = daily_total_series(df, modalities)
    if total.empty:
        return None
    return float(total.mean())


def render() -> None:
    page_header(
        "Overview",
        "A quick read on the periods you selected.",
    )
    controls = get_controls()

    if controls.error:
        st.error(controls.error)
        return
    if controls.df is None or controls.df.empty:
        st.info("No data loaded. Adjust the periods in the sidebar.")
        return

    df = prepared_df()
    assigned = df[df["group_label"].notna()]
    modalities = controls.filters.selected_modalities

    if not modalities:
        st.warning("Select at least one modality in the sidebar.")
        return

    totals = (
        compute_period_totals(assigned, modalities, group_col="group_label")
        if not assigned.empty
        else pd.DataFrame()
    )

    # Compare mean daily counts, not raw totals: period lengths differ a lot
    # (a one-week half term vs a six-week term), so totals are misleading.
    per_period_daily = (
        period_mean_daily(assigned, modalities, group_col="group_label")
        if not assigned.empty
        else pd.Series(dtype=float)
    )

    present = set(assigned["group_label"].dropna().unique())
    items: list[dict] = [
        {"label": "Hourly rows", "value": f"{len(controls.df):,}"},
        {"label": "Groups", "value": str(len(present))},
    ]

    mean_daily = _mean_daily(assigned, modalities)
    if mean_daily is not None:
        items.append(
            {"label": "Mean daily count", "value": f"{mean_daily:,.0f}"}
        )

    if len(per_period_daily) >= 2:
        first_label = per_period_daily.index[0]
        second_label = per_period_daily.index[1]
        items.append(
            {
                "label": f"{second_label} vs {first_label}",
                "value": f"{per_period_daily[second_label]:,.0f}",
                "delta": format_pct_change(
                    per_period_daily[first_label],
                    per_period_daily[second_label],
                ),
                "help": "Mean daily count across selected modalities.",
            }
        )

    kpi_row(items)

    marked = set(df["period_label"].dropna().unique())
    shown = [i for i in controls.instances if i.label in marked]
    if shown:
        st.subheader("Marked periods")
        period_summary(
            shown, caption="Periods marked on the trend charts."
        )

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

    if not totals.empty:
        st.subheader("Totals by group")
        st.dataframe(totals, use_container_width=True, hide_index=True)

    st.caption(
        "Tip: open **Trends** for long-term patterns and **Compare** for "
        "weekday-aligned comparisons."
    )
