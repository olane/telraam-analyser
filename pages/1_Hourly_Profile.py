"""Hourly traffic profile comparison."""

import streamlit as st
from analysis import (
    assign_period_groups,
    compute_hourly_profile,
    filter_days_of_week,
    filter_time_of_day,
)
from charts import plot_hourly_profile

st.header("Hourly Traffic Profile")

if "traffic_df" not in st.session_state:
    st.info("Load data from the sidebar first.")
    st.stop()

df = st.session_state.traffic_df
groups = st.session_state.period_groups_parsed
fs = st.session_state.filter_settings

if not fs.selected_modalities:
    st.warning("Select at least one modality in the sidebar.")
    st.stop()

# Apply filters
df = filter_time_of_day(df, fs.start_hour, fs.end_hour)
df = filter_days_of_week(df, fs.selected_days)
df = assign_period_groups(df, groups)

if df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

profile = compute_hourly_profile(df, fs.selected_modalities)
fig = plot_hourly_profile(profile, fs.selected_modalities)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Data table"):
    st.dataframe(profile)
