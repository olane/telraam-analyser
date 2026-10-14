from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _view_script() -> None:
    from datetime import date

    import pandas as pd
    import streamlit as st

    import views.compare as compare
    import views.detail as detail
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

    for view in (trends, compare, detail):
        view.render()


def test_views_render_without_exception():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception


def test_compare_renders_headline_kpis_for_every_group():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    metrics = {metric.label: metric for metric in at.metric}
    # One card per comparison group, not just the first two.
    assert "Term time" in metrics
    assert "School holidays" in metrics
    # Non-baseline cards carry the percentage change.
    assert metrics["School holidays"].delta


def test_trends_modality_filter_offers_all():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    boxes = {box.label: box for box in at.selectbox}
    assert "All" in boxes["Trend modality"].options


def _trends_group_script() -> None:
    from datetime import date

    import pandas as pd
    import streamlit as st

    import views.trends as trends
    from domain.models import FilterSettings, PeriodInstance, PeriodKind
    from ui.state import Controls

    index = pd.date_range("2026-01-05", "2026-02-28 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5
    df["night"] = 1.0

    instances = [
        PeriodInstance(
            "Spring term",
            PeriodKind.TERM,
            ((date(2026, 1, 5), date(2026, 1, 30)),),
        ),
    ]
    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(selected_modalities=["car", "heavy"]),
        exclusions=[],
        instances=instances,
        df=df,
    )
    trends.render()


def test_trends_motorised_selection_renders():
    at = AppTest.from_function(_trends_group_script, default_timeout=30).run()
    assert not at.exception
    box = at.selectbox(key="trend_modality")
    assert "Motorised vehicles" in box.options
    box.select("motorised").run()
    assert not at.exception


def _before_after_script() -> None:
    import pandas as pd
    import streamlit as st

    import views.compare as compare
    from domain.models import ComparisonMode, FilterSettings
    from ui.state import Controls

    index = pd.date_range("2025-12-15", "2026-04-30 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5

    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(selected_modalities=["car", "bike"]),
        exclusions=[],
        instances=[],
        df=df,
    )
    # The axis now lives on the page, so seed its widget state directly.
    st.session_state["compare_comparison_mode"] = ComparisonMode.BEFORE_AFTER
    compare.render()


def test_before_after_compare_renders_context_trend():
    at = AppTest.from_function(_before_after_script, default_timeout=30).run()
    assert not at.exception
    headers = [h.value for h in at.subheader]
    assert "What is being compared" in headers


def _time_of_day_script() -> None:
    import pandas as pd
    import streamlit as st

    import views.compare as compare
    from domain.models import ComparisonMode, FilterSettings
    from ui.state import Controls

    index = pd.date_range("2025-12-15", "2026-04-30 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5

    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(selected_modalities=["car", "bike"]),
        exclusions=[],
        instances=[],
        df=df,
    )
    st.session_state["compare_comparison_mode"] = ComparisonMode.TIME_OF_DAY
    compare.render()


def test_time_of_day_compare_hides_headline_kpis():
    at = AppTest.from_function(_time_of_day_script, default_timeout=30).run()
    assert not at.exception
    headers = [h.value for h in at.subheader]
    assert "Headline comparison" not in headers


def test_sidebar_defaults_to_all_time():
    from ui.controls import DEFAULT_RANGE

    assert DEFAULT_RANGE == "All time"


def _trends_controls_script() -> None:
    import streamlit as st

    from domain.calendars import default_calendar
    from ui.controls import _mark_periods

    st.session_state.setdefault("exclusions", [])
    _mark_periods(default_calendar())


def test_trends_hides_grouping_axis_but_offers_marking():
    at = AppTest.from_function(_trends_controls_script, default_timeout=30).run()
    assert not at.exception
    selectbox_labels = {box.label for box in at.selectbox}
    assert "Group charts by" not in selectbox_labels
    assert "Mark holidays" in {box.label for box in at.checkbox}


def test_comparison_pages_own_the_grouping_axis():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    assert "Group charts by" in {box.label for box in at.selectbox}


def test_typical_week_groups_follow_the_comparison_axis():
    import pandas as pd

    from analysis import (
        add_comparison_group,
        add_time_columns,
        compute_typical_week,
        weekday_hour_matrix,
    )
    from domain.models import ComparisonConfig, ComparisonMode
    from ui.components import _ordered_groups

    index = pd.date_range("2026-01-05", "2026-01-18 23:00", freq="h", tz="UTC")
    df = pd.DataFrame({"car": 10.0}, index=index)
    df = add_time_columns(df)
    df = add_comparison_group(
        df, ComparisonConfig(mode=ComparisonMode.WEEKDAY_VS_WEEKEND)
    )

    assert _ordered_groups(df, "group_label") == ["Weekday", "Weekend"]

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
