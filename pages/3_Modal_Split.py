"""Modal split comparison between period groups."""

import streamlit as st
from analysis import (
    assign_period_groups,
    compute_modal_split,
    filter_days_of_week,
    filter_time_of_day,
)
from charts import plot_modal_split

st.header("Modal Split")

if "traffic_df" not in st.session_state:
    st.info("Load data from the sidebar first.")
    st.stop()

df = st.session_state.traffic_df
groups = st.session_state.period_groups_parsed
fs = st.session_state.filter_settings

if not fs.selected_modalities:
    st.warning("Select at least one modality in the sidebar.")
    st.stop()

df = filter_time_of_day(df, fs.start_hour, fs.end_hour)
df = filter_days_of_week(df, fs.selected_days)
df = assign_period_groups(df, groups)

if df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

split = compute_modal_split(df, fs.selected_modalities)
fig = plot_modal_split(split, fs.selected_modalities)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Data table"):
    st.dataframe(split)
