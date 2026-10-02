"""Overview view: headline numbers for the current selection."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    compute_period_totals,
    daily_total_series,
    period_mean_daily,
)
from ui.components import (
    aggregate_table,
    format_pct_change,
    kpi_row,
    period_summary,
)
from ui.state import get_controls, prepared_df
from ui.theme import page_header

# Cap the per-group cards so a many-period custom selection can't overflow the
# KPI row; the full comparison is always in the totals table below.
MAX_GROUP_CARDS = 4


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
        st.info("No data loaded. Adjust the data controls in the sidebar.")
        return

    df = prepared_df()
    assigned = df[df["group_label"].notna()]
    modalities = controls.filters.selected_modalities

    if not modalities:
        st.warning("Select at least one modality in the sidebar.")
        return

    # Compare mean daily counts, not raw totals: period lengths differ a lot
    # (a one-week half term vs a six-week term), so totals are misleading.
    per_period_daily = (
        period_mean_daily(assigned, modalities, group_col="group_label")
        if not assigned.empty
        else pd.Series(dtype=float)
    )
    mean_daily = _mean_daily(assigned, modalities)
    present = set(assigned["group_label"].dropna().unique())

    # Lead with the comparison itself; download counters belong in a caption.
    items: list[dict] = []
    if mean_daily is not None:
        items.append(
            {
                "label": "Mean daily count",
                "value": f"{mean_daily:,.0f}",
                "help": "Average daily count across the selection.",
            }
        )
    if not per_period_daily.empty:
        baseline_label = per_period_daily.index[0]
        baseline = float(per_period_daily.iloc[0])
        for group, value in list(per_period_daily.items())[:MAX_GROUP_CARDS]:
            is_baseline = group == baseline_label
            items.append(
                {
                    "label": str(group),
                    "value": f"{value:,.0f}",
                    "delta": (
                        None
                        if is_baseline
                        else format_pct_change(baseline, float(value))
                    ),
                    "help": (
                        "Mean daily count (baseline)."
                        if is_baseline
                        else f"Mean daily count; change against {baseline_label}."
                    ),
                }
            )
    kpi_row(items)

    st.caption(
        f"{len(controls.df):,} hourly rows loaded · {len(present)} groups in "
        "the current comparison."
    )

    if not assigned.empty:
        st.subheader("Totals by group")
        totals = compute_period_totals(
            assigned, modalities, group_col="group_label"
        )
        aggregate_table(totals, "Group", decimals=0)

    marked = set(df["period_label"].dropna().unique())
    shown = [i for i in controls.instances if i.label in marked]
    if shown:
        st.subheader("Calendar periods")
        period_summary(shown, caption="Periods marked on the trend charts.")

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

    st.caption(
        "Tip: open **Trends** for long-term patterns and **Compare** for "
        "weekday-aligned comparisons."
    )
