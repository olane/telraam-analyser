"""Trends view: long-term trend, weekday-adjusted trend, typical week."""

from __future__ import annotations

import streamlit as st

from analysis import (
    compute_daily_totals,
    compute_daily_trend,
    compute_typical_week,
    compute_weekday_totals,
    weekday_adjusted_trend,
    weekday_hour_matrix,
)
from charts import (
    plot_daily_trend,
    plot_typical_week,
    plot_weekday_adjusted_trend,
    plot_weekday_comparison,
)
from ui.state import get_controls, prepared_df
from ui.theme import page_header


def render() -> None:
    page_header(
        "Trends",
        "How traffic moves through time, with holidays and exclusions marked.",
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

    df = prepared_df()
    if df.empty:
        st.warning("No data matches the current filters.")
        return

    window = st.slider("Rolling average window (days)", 3, 28, 7)
    trend = compute_daily_trend(df, modalities, window)
    st.plotly_chart(
        plot_daily_trend(
            trend,
            instances=controls.instances,
            exclusions=controls.exclusions,
            rolling_label=f"{window}-day average",
        ),
        use_container_width=True,
        key="trend_daily",
    )

    st.subheader("Weekday-adjusted trend")
    st.caption(
        "Each day is shown relative to the average for that weekday, so the "
        "weekly cycle doesn't hide the underlying direction of travel."
    )
    adjusted = weekday_adjusted_trend(df, modalities)
    st.plotly_chart(
        plot_weekday_adjusted_trend(
            adjusted,
            instances=controls.instances,
            exclusions=controls.exclusions,
        ),
        use_container_width=True,
        key="trend_weekday_adjusted",
    )

    assigned = df[df["period_label"].notna()]
    if assigned.empty:
        st.info("No labelled periods are covered by the loaded data.")
        return

    st.subheader("Weekday comparison")
    daily = compute_daily_totals(assigned, modalities)
    weekday_df = compute_weekday_totals(daily, modalities)
    modality = st.selectbox("Modality", modalities, key="trend_wd_modality")
    st.plotly_chart(
        plot_weekday_comparison(weekday_df, modality),
        use_container_width=True,
        key="trend_weekday_comparison",
    )

    st.subheader("Typical week")
    labels = list(dict.fromkeys(assigned["period_label"]))
    chosen = st.selectbox("Period", labels, key="trend_typical_period")
    typical = compute_typical_week(
        assigned[assigned["period_label"] == chosen], modalities
    )
    matrix = weekday_hour_matrix(typical, chosen, modality)
    st.plotly_chart(
        plot_typical_week(
            matrix, title=f"Typical week — {chosen} — {modality}"
        ),
        use_container_width=True,
        key="trend_typical_week",
    )
