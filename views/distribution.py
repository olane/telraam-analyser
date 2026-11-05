"""Distribution view: how daily totals are spread across the loaded range."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    DAY_TYPE_COL,
    add_day_type,
    add_derived_modalities,
    compute_daily_histogram,
    compute_daily_summary,
    dedupe_modalities,
    get_available_groups,
)
from charts import plot_daily_histogram
from domain.models import modality_label
from ui.components import (
    ALL_OPTION,
    csv_download,
    kpi_row,
    require_modalities,
)
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def _category_choice(modalities: list[str], groups: list[str]) -> str:
    return st.selectbox(
        "Category",
        [ALL_OPTION, *modalities, *groups],
        format_func=lambda value: (
            "All selected modalities"
            if value == ALL_OPTION
            else modality_label(value)
        ),
        key="distribution_category",
        help="Show one transport mode, an aggregate such as motorised "
        "vehicles, or the combined total of the sidebar selection.",
    )


def _series(df, choice: str, modalities: list[str]):
    """Return (frame, column, display label) for the chosen category."""
    if choice == ALL_OPTION:
        frame = df.copy()
        columns = dedupe_modalities(list(modalities))
        frame["total"] = frame[columns].sum(axis=1)
        return frame, "total", "All selected modalities"
    if choice not in df.columns:
        df = add_derived_modalities(df)
    return df, choice, modality_label(choice)


def _kpi_cards(row, common_label: str | None = None) -> None:
    items = [
        {
            "label": "Days counted",
            "value": f"{int(row['days']):,}",
            "help": "Days with data for this category in the selected range.",
        },
        {
            "label": "Median / day",
            "value": f"{row['median']:,.0f}",
            "help": "Half the days are above this daily total and half below.",
        },
        {
            "label": "Mean / day",
            "value": f"{row['mean']:,.0f}",
            "help": "Average daily total across the selected days.",
        },
        {
            "label": "Std dev / day",
            "value": f"{row['std']:,.0f}",
            "help": "Spread of daily totals across the selected days.",
        },
    ]
    if common_label is not None:
        items.append(
            {
                "label": "Most common range",
                "value": str(common_label),
                "help": "The range containing the most days.",
            }
        )
    kpi_row(items)


def _summary_display(summary, overall):
    display = summary.rename(
        columns={
            DAY_TYPE_COL: "Day type",
            "days": "Days",
            "total": "Total",
            "median": "Median / day",
            "mean": "Mean / day",
            "std": "Std dev / day",
        }
    )
    total = pd.DataFrame(
        [
            {
                "Day type": "Total",
                "Days": int(overall["days"]),
                "Total": overall["total"],
                "Median / day": overall["median"],
                "Mean / day": overall["mean"],
                "Std dev / day": overall["std"],
            }
        ]
    )
    return pd.concat([display, total], ignore_index=True)


def render() -> None:
    page_header(
        "Distribution",
        "How daily totals are spread across the loaded date range.",
    )
    controls = get_controls()
    modalities = require_modalities(controls)
    if modalities is None:
        return

    df = prepared_df()
    if df.empty:
        st.warning("No data matches the current filters.")
        return

    groups = get_available_groups(df)
    left, right = st.columns([2, 1])
    with left:
        choice = _category_choice(modalities, groups)
    with right:
        bin_width = int(
            st.number_input(
                "Range width (vehicles per day)",
                min_value=10,
                max_value=5_000,
                value=100,
                step=10,
                key="distribution_bin_width",
                help="How wide each daily-total bucket is. The default 100 "
                "gives ranges like 200–299, 300–399, and so on.",
            )
        )

    split = st.checkbox(
        "Separate weekdays and weekends",
        value=False,
        key="distribution_split",
        help="Show a separate histogram and summary row for weekdays and weekends.",
    )

    frame, column, display = _series(df, choice, modalities)
    if split:
        frame = add_day_type(frame)
    group_col = DAY_TYPE_COL if split else None

    hist = compute_daily_histogram(
        frame, column, bin_width=bin_width, group_col=group_col
    )
    if hist.empty:
        st.info("No daily counts are available for the current selection.")
        return

    summary = compute_daily_summary(frame, column, group_col=group_col)
    overall = (
        summary.iloc[0]
        if group_col is None
        else compute_daily_summary(frame, column).iloc[0]
    )
    common_label = (
        hist.loc[hist["days"].idxmax(), "label"] if group_col is None else None
    )

    st.caption(
        "Each bar counts days by their total for the whole day; the dotted "
        "line shows how many days are at or above each range. Days with "
        "missing hours are counted from the hours that are present."
    )
    _kpi_cards(overall, common_label)

    if split:
        st.subheader("Daily summary by day type")
        display_summary = _summary_display(summary, overall)
        st.dataframe(
            display_summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Days": st.column_config.NumberColumn(format="%d"),
                "Total": st.column_config.NumberColumn(format="%d"),
                "Median / day": st.column_config.NumberColumn(format="%.0f"),
                "Mean / day": st.column_config.NumberColumn(format="%.0f"),
                "Std dev / day": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.plotly_chart(
        plot_daily_histogram(
            hist,
            column,
            bin_width=bin_width,
            label=display,
            group_col=group_col,
        ),
        use_container_width=True,
        key="distribution_histogram",
    )

    with st.expander("Daily ranges (table)"):
        table = hist.rename(
            columns={
                "low": "From",
                "high": "To",
                "label": "Range",
                "days": "Days",
                "at_or_above": "Days at or above",
            }
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

    csv_download(hist, "daily_distribution.csv", "Download distribution (CSV)")
    if split:
        csv_download(
            display_summary,
            "daily_summary.csv",
            "Download summary (CSV)",
        )
