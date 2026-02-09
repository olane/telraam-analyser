"""Telraam Traffic Comparison — Streamlit entry point."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from config import Config
from models import PeriodGroup, FilterSettings
from api_client import TelraamClient, TelraamAPIError
from cache import CacheManager
from analysis import get_available_modalities
from presets import BUILTIN_PRESETS, save_period_groups, list_saved, load_period_groups

st.set_page_config(
    page_title="Telraam Traffic Comparison",
    page_icon=":bar_chart:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

config = Config.from_env()

if not config.api_key:
    st.error("Set `TELRAAM_API_KEY` in your `.env` file.")
    st.stop()

if not config.segment_ids:
    st.error("Set `TELRAAM_SEGMENT_IDS` in your `.env` file (comma-separated).")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — segment selector
# ---------------------------------------------------------------------------

st.sidebar.title("Telraam Comparison")

segment_id = st.sidebar.selectbox("Segment", config.segment_ids)

# ---------------------------------------------------------------------------
# Sidebar — period groups: presets & save/load
# ---------------------------------------------------------------------------

st.sidebar.header("Period Groups")

# Preset / load selector
preset_options = list(BUILTIN_PRESETS.keys()) + [f"Saved: {n}" for n in list_saved()]

if preset_options:
    cols = st.sidebar.columns([3, 1])
    chosen_preset = cols[0].selectbox("Preset / saved", preset_options, label_visibility="collapsed")
    if cols[1].button("Load"):
        if chosen_preset.startswith("Saved: "):
            loaded = load_period_groups(chosen_preset.removeprefix("Saved: "))
        else:
            loaded = [
                {"name": g["name"], "ranges": list(g["ranges"])}
                for g in BUILTIN_PRESETS[chosen_preset]
            ]
        st.session_state.period_groups = loaded
        # Bump version to generate fresh widget keys
        st.session_state.pg_version = st.session_state.get("pg_version", 0) + 1
        st.rerun()

if "period_groups" not in st.session_state:
    st.session_state.period_groups = [
        {"name": "Period A", "ranges": []},
        {"name": "Period B", "ranges": []},
    ]

groups_state = st.session_state.period_groups
_v = st.session_state.get("pg_version", 0)

# Save current groups
with st.sidebar.expander("Save current periods"):
    save_name = st.text_input("Name", key="save_name")
    if st.button("Save") and save_name:
        save_period_groups(save_name, groups_state)
        st.success(f"Saved as '{save_name}'")
        st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — period group editor
# ---------------------------------------------------------------------------


def _add_group():
    n = len(groups_state) + 1
    groups_state.append({"name": f"Period {chr(64 + n)}", "ranges": []})


def _remove_group(idx: int):
    if len(groups_state) > 1:
        groups_state.pop(idx)


for gi, g in enumerate(groups_state):
    with st.sidebar.expander(g["name"], expanded=True):
        g["name"] = st.text_input("Name", value=g["name"], key=f"gname_{_v}_{gi}")

        for ri, (rs, re) in enumerate(g["ranges"]):
            cols = st.columns([4, 4, 1])
            new_start = cols[0].date_input("Start", value=rs, key=f"gs_{_v}_{gi}_{ri}")
            new_end = cols[1].date_input("End", value=re, key=f"ge_{_v}_{gi}_{ri}")
            if cols[2].button(":x:", key=f"gx_{_v}_{gi}_{ri}"):
                g["ranges"].pop(ri)
                st.rerun()
            g["ranges"][ri] = (new_start, new_end)

        if st.button("+ Add date range", key=f"gadd_{_v}_{gi}"):
            today = date.today()
            g["ranges"].append((today - timedelta(days=30), today))
            st.rerun()

        if len(groups_state) > 1:
            if st.button("Remove group", key=f"grem_{_v}_{gi}"):
                _remove_group(gi)
                st.rerun()

if st.sidebar.button("+ Add period group"):
    _add_group()
    st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------

st.sidebar.header("Filters")

hour_range = st.sidebar.slider(
    "Hours of day", min_value=0, max_value=23, value=(0, 23)
)

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
selected_day_labels = st.sidebar.multiselect(
    "Days of week", DAY_LABELS, default=DAY_LABELS
)
selected_days = [DAY_LABELS.index(d) for d in selected_day_labels]

# Modality selection is deferred until data is loaded (we need column names)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

st.sidebar.header("Data")

if st.sidebar.button("Load Data", type="primary"):
    # Build PeriodGroup objects
    period_groups = []
    all_ranges: list[tuple[date, date]] = []
    for g in groups_state:
        ranges = [(s, e) for s, e in g["ranges"] if s <= e]
        if ranges:
            period_groups.append(PeriodGroup(name=g["name"], ranges=ranges))
            all_ranges.extend(ranges)

    if not period_groups:
        st.sidebar.error("Add at least one date range to a period group.")
    else:
        # Determine overall fetch range
        overall_start = min(r[0] for r in all_ranges)
        overall_end = max(r[1] for r in all_ranges) + timedelta(days=1)

        client = TelraamClient(config.api_key)
        cache = CacheManager(config.cache_dir)

        progress_bar = st.sidebar.progress(0, text="Fetching data...")

        def on_progress(done: int, total: int):
            progress_bar.progress(done / total, text=f"Chunk {done}/{total}")

        try:
            df = cache.get_or_fetch(
                segment_id=segment_id,
                level=config.default_level,
                fmt=config.default_format,
                start=overall_start,
                end=overall_end,
                client=client,
                progress_callback=on_progress,
            )
            progress_bar.empty()

            if df.empty:
                st.sidebar.warning("No data returned for the selected ranges.")
            else:
                st.session_state.traffic_df = df
                st.session_state.period_groups_parsed = period_groups
                st.session_state.available_modalities = get_available_modalities(df)
                st.sidebar.success(f"Loaded {len(df):,} rows.")
        except TelraamAPIError as exc:
            progress_bar.empty()
            st.sidebar.error(f"API error: {exc}")

# ---------------------------------------------------------------------------
# Sidebar — modality selector (after data loaded)
# ---------------------------------------------------------------------------

if "available_modalities" in st.session_state:
    default_mods = [
        m for m in st.session_state.available_modalities
        if m in ("pedestrian", "bike", "car", "heavy")
    ]
    selected_modalities = st.sidebar.multiselect(
        "Modalities",
        st.session_state.available_modalities,
        default=default_mods,
    )
else:
    selected_modalities = []

# Store filter settings in session state for pages to use
st.session_state.filter_settings = FilterSettings(
    start_hour=hour_range[0],
    end_hour=hour_range[1],
    selected_days=selected_days,
    selected_modalities=selected_modalities,
)

# ---------------------------------------------------------------------------
# Main area — landing page
# ---------------------------------------------------------------------------

st.title("Telraam Traffic Comparison")

if "traffic_df" not in st.session_state:
    st.info(
        "Configure period groups and filters in the sidebar, then click **Load Data**."
    )
else:
    st.write(
        f"**{len(st.session_state.traffic_df):,}** rows loaded. "
        f"Use the pages in the sidebar to explore charts."
    )
    with st.expander("Raw data preview"):
        st.dataframe(st.session_state.traffic_df.head(200))
