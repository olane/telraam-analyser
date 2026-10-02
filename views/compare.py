"""Compare view: weekday-aligned comparison of the chosen comparison axis."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_daily_trend,
    compute_hourly_profile,
    compute_modal_split,
    compute_weekday_totals,
    period_mean_daily,
)
from charts import (
    plot_daily_trend,
    plot_hourly_profile,
    plot_modal_split,
    plot_weekday_comparison,
)
from domain.models import ComparisonMode, InterventionFilter
from ui.components import (
    ALL_OPTION,
    format_pct_change,
    kpi_row,
    typical_week_heatmaps,
)
from ui.state import get_controls, prepared_df
from ui.theme import page_header

GROUP_COL = "group_label"


def _intervention_context(controls, modalities: list[str]) -> None:
    """Trend over the loaded range with the compared windows shaded."""
    full = prepared_df()
    if full.empty:
        return

    date_filter = controls.comparison.date_filter
    if date_filter is InterventionFilter.TERM_ONLY:
        detail = (
            "Only term-time dates inside each window are compared; the "
            "shaded bands show exactly which days they are."
        )
    elif date_filter is InterventionFilter.HOLIDAYS_ONLY:
        detail = (
            "Only holiday dates inside each window are compared; the "
            "shaded bands show exactly which days they are."
        )
    else:
        detail = "Every date inside each window is compared."

    st.subheader("What is being compared")
    st.caption(
        "Shaded windows are the periods used in the comparison below. "
        + detail
    )
    trend = compute_daily_trend(full, modalities, window=7)
    st.plotly_chart(
        plot_daily_trend(
            trend,
            instances=controls.instances,
            exclusions=controls.exclusions,
            title="Traffic trend around the intervention",
            rolling_label="7-day average",
        ),
        use_container_width=True,
        key="compare_intervention_trend",
    )

    empty = [i.label for i in controls.instances if i.n_days == 0]
    if empty:
        st.warning(
            "The current date filter leaves no dates in: "
            + ", ".join(empty)
            + ". Widen the window or change the dates to compare."
        )


def _headline_comparison(means) -> None:
    """One KPI card per comparison group: mean daily count vs the baseline."""
    if means is None or means.empty:
        return

    baseline_label = means.index[0]
    baseline = float(means.iloc[0])

    st.subheader("Headline comparison")
    st.caption(
        "Mean daily counts per group; deltas are the change against "
        f"**{baseline_label}**."
    )
    kpi_row(
        [
            {
                "label": str(group),
                "value": f"{value:,.0f}",
                "delta": (
                    format_pct_change(baseline, float(value))
                    if group != baseline_label
                    else None
                ),
                "help": "Mean daily count (average per day) across the "
                "selected modalities.",
            }
            for group, value in means.items()
        ]
    )


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

    st.caption(
        "Tip: choose which transport modes appear in the charts below with "
        "the **Modalities** filter in the left sidebar."
    )

    if controls.comparison.mode is ComparisonMode.BEFORE_AFTER:
        _intervention_context(controls, modalities)

    df = prepared_df(keep_only_assigned=True)
    if df.empty:
        st.warning("No data matches the current filters or comparison.")
        return

    daily = compute_daily_totals(df, modalities, group_col=GROUP_COL)
    weekday_df = compute_weekday_totals(daily, modalities, group_col=GROUP_COL)

    # Time-of-day bands cover different numbers of hours, so a single mean
    # daily figure per band is not comparable and adds no value here.
    show_headline = controls.comparison.mode is not ComparisonMode.TIME_OF_DAY
    labels = (["Headline"] if show_headline else []) + [
        "Weekday",
        "Typical week",
        "Hourly profile",
        "Modal split",
    ]
    tabs = st.tabs(labels)
    idx = 0

    if show_headline:
        with tabs[idx]:
            _headline_comparison(
                period_mean_daily(df, modalities, group_col=GROUP_COL)
            )
        idx += 1

    with tabs[idx]:
        st.subheader("Weekday comparison")
        columns = st.columns(2)
        for i, modality in enumerate(modalities):
            columns[i % 2].plotly_chart(
                plot_weekday_comparison(
                    weekday_df, modality, group_col=GROUP_COL
                ),
                use_container_width=True,
                key=f"compare_weekday_{modality}",
            )
    idx += 1

    with tabs[idx]:
        typical_week_heatmaps(
            df,
            modalities,
            ALL_OPTION,
            controls.comparison,
            key_prefix="compare_typical",
        )
    idx += 1

    with tabs[idx]:
        st.subheader("Hourly profile")
        profile = compute_hourly_profile(df, modalities, group_col=GROUP_COL)
        st.plotly_chart(
            plot_hourly_profile(profile, modalities, group_col=GROUP_COL),
            use_container_width=True,
            key="compare_hourly",
        )
    idx += 1

    with tabs[idx]:
        st.subheader("Modal split")
        split = compute_modal_split(df, modalities, group_col=GROUP_COL)
        st.plotly_chart(
            plot_modal_split(split, modalities, group_col=GROUP_COL),
            use_container_width=True,
            key="compare_modal",
        )
