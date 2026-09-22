from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _view_script() -> None:
    from datetime import date

    import pandas as pd
    import streamlit as st

    import views.compare as compare
    import views.detail as detail
    import views.overview as overview
    import views.trends as trends
    from domain.models import (
        ComparisonConfig,
        ComparisonMode,
        Exclusion,
        FilterSettings,
        PeriodInstance,
        PeriodKind,
    )
    from ui.state import Controls

    index = pd.date_range("2025-12-15", "2026-02-28 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5

    instances = [
        PeriodInstance(
            "Christmas", PeriodKind.CHRISTMAS,
            ((date(2025, 12, 22), date(2026, 1, 2)),),
        ),
        PeriodInstance(
            "February half term", PeriodKind.FEB_HALF,
            ((date(2026, 2, 16), date(2026, 2, 22)),),
        ),
    ]

    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(
            selected_modalities=["pedestrian", "bike", "car", "heavy"]
        ),
        comparison=ComparisonConfig(mode=ComparisonMode.HOLIDAY_VS_TERM),
        exclusions=[Exclusion("Roadworks", ((date(2026, 1, 12), date(2026, 1, 16)),))],
        instances=instances,
        df=df,
    )

    for view in (overview, trends, compare, detail):
        view.render()


def test_views_render_without_exception():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception


def test_overview_renders_kpis():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    labels = {metric.label for metric in at.metric}
    assert "Periods" in labels
    assert "Mean daily count" in labels
    assert len(at.metric) >= 4
    # The period comparison KPI carries a percentage delta.
    assert any(metric.delta for metric in at.metric)
