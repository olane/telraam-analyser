"""Telraam Traffic Explorer — Streamlit entry point."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Telraam Traffic Explorer",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

import views.compare as compare  # noqa: E402
import views.detail as detail  # noqa: E402
import views.overview as overview  # noqa: E402
import views.trends as trends  # noqa: E402
from charts import register_template  # noqa: E402
from config import Config  # noqa: E402
from ui.controls import render_sidebar  # noqa: E402
from ui.state import init_state  # noqa: E402
from ui.theme import inject_css  # noqa: E402

register_template()
inject_css()

config = Config.from_env()
if not config.is_configured:
    st.error(
        "Set `TELRAAM_API_KEY` and `TELRAAM_SEGMENT_IDS` in Streamlit secrets "
        "or a local `.env` file, then reload."
    )
    st.stop()

init_state(config)
st.session_state["controls"] = render_sidebar(config, st.session_state["calendar"])

pages = [
    st.Page(
        overview.render,
        title="Overview",
        url_path="overview",
        icon=":material/dashboard:",
        default=True,
    ),
    st.Page(
        trends.render,
        title="Trends",
        url_path="trends",
        icon=":material/trending_up:",
    ),
    st.Page(
        compare.render,
        title="Compare",
        url_path="compare",
        icon=":material/insights:",
    ),
    st.Page(
        detail.render,
        title="Detail",
        url_path="detail",
        icon=":material/table:",
    ),
]

st.navigation(pages).run()
