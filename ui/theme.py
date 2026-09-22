"""Visual theme: CSS injection and page headers."""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
    :root {
        --telraam-ink: #102027;
        --telraam-accent: #0b6e99;
        --telraam-muted: #607d8b;
    }
    .block-container { padding-top: 2.2rem; max-width: 1200px; }
    h1, h2, h3 { color: var(--telraam-ink); letter-spacing: -0.01em; }
    [data-testid="stMetric"] {
        background: #f7fafc;
        border: 1px solid #e3e8ee;
        border-radius: 10px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stMetricValue"] { color: var(--telraam-accent); }
    section[data-testid="stSidebar"] { border-right: 1px solid #e3e8ee; }
    .app-header { padding: 0.2rem 0 0.6rem 0; }
    .app-header h1 { margin-bottom: 0.1rem; }
    .app-subtitle { color: var(--telraam-muted); font-size: 0.95rem; }
    .attribution {
        color: var(--telraam-muted);
        font-size: 0.78rem;
        border-top: 1px solid #e3e8ee;
        margin-top: 2rem;
        padding-top: 0.8rem;
    }
    .attribution a { color: var(--telraam-accent); }
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "") -> None:
    sub = f'<div class="app-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="app-header"><h1>{title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )
