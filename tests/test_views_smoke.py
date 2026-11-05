from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _view_script() -> None:
    from datetime import date

    import pandas as pd
    import streamlit as st

    import views.compare as compare
    import views.detail as detail
    import views.distribution as distribution
    import views.trends as trends
    from domain.models import Exclusion, FilterSettings
    from ui.state import Controls

    index = pd.date_range("2025-12-15", "2026-02-28 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5

    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(
            selected_modalities=["pedestrian", "bike", "car", "heavy"]
        ),
        exclusions=[Exclusion("Roadworks", ((date(2026, 1, 12), date(2026, 1, 16)),))],
        df=df,
    )

    for view in (trends, compare, distribution, detail):
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


def test_distribution_category_offers_aggregate_groups():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    box = at.selectbox(key="distribution_category")
    assert "All selected modalities" in box.options
    assert "Motorised vehicles" in box.options
    box.select("motorised").run()
    assert not at.exception


def test_distribution_can_split_weekday_and_weekend():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    at.checkbox(key="distribution_split").check().run()
    assert not at.exception
    assert "Daily summary by day type" in [h.value for h in at.subheader]


def test_distribution_removes_the_threshold_control():
    at = AppTest.from_function(_view_script, default_timeout=30).run()
    assert not at.exception
    labels = {control.label for control in at.number_input}
    assert "Threshold (counts per day)" not in labels
    assert "Range width (counts per day)" in labels


def _trends_group_script() -> None:
    import pandas as pd
    import streamlit as st

    import views.trends as trends
    from domain.models import FilterSettings
    from ui.state import Controls

    index = pd.date_range("2026-01-05", "2026-02-28 23:00", freq="h", tz="UTC")
    df = pd.DataFrame(index=index)
    df["pedestrian"] = 2.0
    df["bike"] = 3.0
    df["car"] = 10.0
    df["heavy"] = 0.5
    df["night"] = 1.0

    st.session_state["controls"] = Controls(
        segment_id="123",
        filters=FilterSettings(selected_modalities=["car", "heavy"]),
        exclusions=[],
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


def test_trends_hides_grouping_axis_but_offers_marking():
    at = AppTest.from_function(_trends_group_script, default_timeout=30).run()
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


def test_distribution_summary_table_includes_a_total_row():
    import pandas as pd

    from views.distribution import _summary_display

    summary = pd.DataFrame(
        {
            "day_type": ["Weekday", "Weekend"],
            "days": [5, 2],
            "total": [1200.0, 960.0],
            "median": [240.0, 480.0],
            "mean": [240.0, 480.0],
            "std": [0.0, 0.0],
        }
    )
    overall = pd.Series(
        {
            "days": 7,
            "total": 2160.0,
            "median": 240.0,
            "mean": 308.571,
            "std": 108.42,
        }
    )

    display = _summary_display(summary, overall)

    assert display.iloc[-1]["Day type"] == "Total"
    assert display.iloc[-1]["Days"] == 7
    assert display.iloc[-1]["Total"] == 2160.0
    assert display.iloc[-1]["Total"] == display.iloc[:-1]["Total"].sum()
    assert list(display.columns) == [
        "Day type",
        "Days",
        "Total",
        "Median / day",
        "Mean / day",
        "Std dev / day",
    ]


def test_sidebar_presets_include_year_to_date():
    from ui.controls import RANGE_PRESETS, YEAR_TO_DATE

    assert YEAR_TO_DATE in RANGE_PRESETS


def test_year_to_date_preset_starts_on_new_year():
    from datetime import date

    from ui.controls import YEAR_TO_DATE, _preset_range

    start, end = _preset_range(
        YEAR_TO_DATE, date(2026, 11, 5), date(2021, 2, 1)
    )
    assert start == date(2026, 1, 1)
    assert end == date(2026, 11, 6)


def test_year_to_date_preset_respects_earliest_data():
    from datetime import date

    from ui.controls import YEAR_TO_DATE, _preset_range

    start, _ = _preset_range(
        YEAR_TO_DATE, date(2026, 11, 5), date(2026, 3, 1)
    )
    assert start == date(2026, 3, 1)


def test_last_days_preset_includes_today():
    from datetime import date

    from ui.controls import _preset_range

    start, end = _preset_range(
        "Last 30 days", date(2026, 11, 5), date(2021, 2, 1)
    )
    assert start == date(2026, 10, 7)
    assert end == date(2026, 11, 6)


def test_all_time_preset_starts_at_earliest_data():
    from datetime import date

    from ui.controls import DEFAULT_RANGE, _preset_range

    start, end = _preset_range(
        DEFAULT_RANGE, date(2026, 11, 5), date(2021, 2, 1)
    )
    assert start == date(2021, 2, 1)
    assert end == date(2026, 11, 6)
