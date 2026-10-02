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
            "Spring term", PeriodKind.TERM,
            ((date(2026, 1, 5), date(2026, 1, 30)),),
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
    assert "Groups" in labels
    assert "Mean daily count" in labels
    assert len(at.metric) >= 4
    # The period comparison KPI carries a percentage delta.
    assert any(metric.delta for metric in at.metric)


def test_trends_modality_filter_offers_all():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    boxes = {box.label: box for box in at.selectbox}
    assert "All" in boxes["Trend modality"].options


def test_compare_modality_defaults_to_car():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    boxes = {box.label: box for box in at.selectbox}
    # Compare offers no "All" option, so it should default to cars.
    assert boxes["Modality"].value == "car"


def test_typical_week_groups_follow_the_comparison_axis():
    import pandas as pd

    from analysis import (
        add_comparison_group,
        add_time_columns,
        compute_typical_week,
        weekday_hour_matrix,
    )
    from domain.models import ComparisonConfig, ComparisonMode
    from views.trends import _ordered_groups

    index = pd.date_range("2026-01-05", "2026-01-18 23:00", freq="h", tz="UTC")
    df = pd.DataFrame({"car": 10.0}, index=index)
    df = add_time_columns(df)
    df = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.WEEKDAY_VS_WEEKEND)
    )

    assert _ordered_groups(df) == ["Weekday", "Weekend"]

    typical = compute_typical_week(df, ["car"], group_col="group_label")
    weekday = weekday_hour_matrix(
        typical, "Weekday", "car", group_col="group_label"
    )
    weekend = weekday_hour_matrix(
        typical, "Weekend", "car", group_col="group_label"
    )
    # Like weekdays are grouped together: weekdays fill rows, weekend blanks.
    assert weekday.loc["Mon"].notna().all()
    assert weekday.loc["Sat"].isna().all()
    assert weekend.loc["Sat"].notna().all()
    assert weekend.loc["Mon"].isna().all()
