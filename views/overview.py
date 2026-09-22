"""Overview view: headline numbers for the current selection."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_period_totals,
    period_mean_daily,
)
from ui.components import kpi_row, period_summary
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def _mean_daily(df: pd.DataFrame, modalities: list[str]) -> float | None:
    if df.empty or not modalities:
        return None
    daily = compute_daily_totals(df, modalities)
    if daily.empty:
        return None
    totals = daily[modalities].sum(axis=1)
    return float(totals.mean())


def _pct_delta(before: float, after: float) -> str | None:
    if not before:
        return None
    return f"{(after - before) / before * 100:+.1f}%"


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
    assigned = df[df["period_label"].notna()]
    modalities = controls.filters.selected_modalities

    if not modalities:
        st.warning("Select at least one modality in the sidebar.")
        return

    totals = (
        compute_period_totals(assigned, modalities)
        if not assigned.empty
        else pd.DataFrame()
    )

    # Compare mean daily counts, not raw totals: period lengths differ a lot
    # (a one-week half term vs a six-week term), so totals are misleading.
    per_period_daily = (
        period_mean_daily(assigned, modalities)
        if not assigned.empty
        else pd.Series(dtype=float)
    )

    items: list[dict] = [
        {"label": "Hourly rows", "value": f"{len(controls.df):,}"},
        {"label": "Periods", "value": str(len(controls.instances))},
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
                "delta": _pct_delta(
                    per_period_daily[first_label],
                    per_period_daily[second_label],
                ),
                "help": "Mean daily count across selected modalities.",
            }
        )

    kpi_row(items)

    st.subheader("Selected periods")
    period_summary(controls.instances, caption="These are the periods being compared.")

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
        st.subheader("Totals by period")
        st.dataframe(totals, use_container_width=True, hide_index=True)

    st.caption(
        "Tip: open **Trends** for long-term patterns and **Compare** for "
        "weekday-aligned comparisons."
    )
