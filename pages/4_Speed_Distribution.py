"""Car speed distribution comparison."""

import streamlit as st
from analysis import (
    assign_period_groups,
    compute_speed_distribution,
    compute_speed_summary,
    filter_days_of_week,
    filter_time_of_day,
)
from charts import plot_speed_distribution

st.header("Speed Distribution")

if "traffic_df" not in st.session_state:
    st.info("Load data from the sidebar first.")
    st.stop()

df = st.session_state.traffic_df
groups = st.session_state.period_groups_parsed
fs = st.session_state.filter_settings

df = filter_time_of_day(df, fs.start_hour, fs.end_hour)
df = filter_days_of_week(df, fs.selected_days)
df = assign_period_groups(df, groups)

if df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

unit = st.radio("Unit", ["mph", "km/h"], horizontal=True)

# Summary comparison
summary = compute_speed_summary(df, unit=unit)
if summary is not None:
    st.subheader("Speed Comparison")
    cols = st.columns(len(summary))
    for i, (_, row) in enumerate(summary.iterrows()):
        with cols[i]:
            st.markdown(f"**{row['period_group']}**")
            for col_name in summary.columns:
                if col_name == "period_group":
                    continue
                st.metric(col_name, row[col_name])

# Histogram
speed = compute_speed_distribution(df, unit=unit)

if speed is None:
    st.info("No speed histogram data available for this segment/data range.")
    st.stop()

fig = plot_speed_distribution(speed, unit=unit)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Data table"):
    st.dataframe(speed)
