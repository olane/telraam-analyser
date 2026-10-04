"""Trends view: long-term trend, weekday-adjusted trend, speed."""

from __future__ import annotations

import streamlit as st

from analysis import (
    add_derived_modalities,
    compute_daily_trend,
    compute_speed_distribution,
    compute_speed_summary,
    compute_speed_trend,
    get_available_groups,
    weekday_adjusted_trend,
)
from charts import (
    plot_daily_trend,
    plot_speed_distribution,
    plot_speed_trend,
    plot_weekday_adjusted_trend,
)
from domain.models import NIGHT_MOTORISED_SHARE_DEFAULT, modality_label
from ui.components import ALL_OPTION, V85_DOCS_URL, csv_download
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

    top_left, top_right = st.columns([2, 1])
    groups = get_available_groups(df)
    trend_choice = top_left.selectbox(
        "Trend modality",
        [ALL_OPTION, *modalities, *groups],
        format_func=modality_label,
        key="trend_modality",
        help="Show a single mode or an aggregate group, or the combined total "
        "of every mode selected in the sidebar.",
    )
    window = top_right.slider("Rolling average (days)", 3, 28, 7)

    if trend_choice in groups:
        night_share = st.slider(
            "Night assumed motorised (%)",
            0,
            100,
            int(round(NIGHT_MOTORISED_SHARE_DEFAULT * 100)),
            help="Headlight-only night detections counted as motorised; the "
            "rest are treated as bikes.",
        )
        st.caption(
            "In winter months it gets dark earlier, so more traffic is only "
            "detectable as headlights and is counted under **night** instead "
            "of its mode, under-counting the other categories. "
            "**Motorised vehicles** adds back the night detections assumed "
            "not to be bikes to correct for this."
        )
        df = add_derived_modalities(df, {"night": night_share / 100})

    trend_modalities = (
        modalities if trend_choice == ALL_OPTION else [trend_choice]
    )
    trend_label = (
        "all selected modalities"
        if trend_choice == ALL_OPTION
        else modality_label(trend_choice)
    )

    trend = compute_daily_trend(df, trend_modalities, window)
    st.plotly_chart(
        plot_daily_trend(
            trend,
            instances=controls.instances,
            exclusions=controls.exclusions,
            title=f"Traffic trend — {trend_label}",
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
    adjusted = weekday_adjusted_trend(df, trend_modalities)
    st.plotly_chart(
        plot_weekday_adjusted_trend(
            adjusted,
            instances=controls.instances,
            exclusions=controls.exclusions,
            title=f"Weekday-adjusted trend — {trend_label}",
        ),
        use_container_width=True,
        key="trend_weekday_adjusted",
    )

    st.subheader("Speed")
    st.caption(
        "V85 is the 85th percentile speed — the speed 85% of cars travel at or "
        f"below. [How Telraam measures V85]({V85_DOCS_URL})."
    )
    unit = st.radio("Speed unit", ["mph", "km/h"], horizontal=True)
    summary = compute_speed_summary(df, unit=unit)
    if summary is not None and not summary.empty:
        st.dataframe(summary, use_container_width=True, hide_index=True)

        speed = compute_speed_distribution(df, unit=unit)
        if speed is not None and not speed.empty:
            st.plotly_chart(
                plot_speed_distribution(speed, unit=unit),
                use_container_width=True,
                key="trend_speed",
            )
            csv_download(
                speed, "speed_distribution.csv", "Download speed data (CSV)"
            )

        speed_trend = compute_speed_trend(df, unit=unit)
        if speed_trend is not None and not speed_trend.empty:
            st.plotly_chart(
                plot_speed_trend(speed_trend, unit=unit),
                use_container_width=True,
                key="trend_speed_trend",
            )
            csv_download(
                speed_trend, "speed_trend.csv", "Download V85 trend (CSV)"
            )
    else:
        st.info("No speed data is available for this segment or selection.")
