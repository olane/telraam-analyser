"""Session-state plumbing: config, calendar, cache and the prepared frame."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import streamlit as st

from analysis import (
    drop_exclusions,
    filter_days_of_week,
    filter_time_of_day,
    label_periods,
)
from api_client import TelraamClient
from cache import CacheManager
from config import Config
from domain.calendars import default_calendar
from domain.models import (
    ComparisonConfig,
    Exclusion,
    FilterSettings,
    PeriodInstance,
)
from guard import BudgetExceeded, DailyRequestBudget


@dataclass
class Controls:
    """Everything the views need, computed once per rerun."""

    segment_id: str
    filters: FilterSettings
    comparison: ComparisonConfig
    exclusions: list[Exclusion]
    instances: list[PeriodInstance]
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    error: str | None = None


def init_state(config: Config) -> None:
    ss = st.session_state
    ss.setdefault("config", config)
    ss.setdefault("calendar", default_calendar())
    ss.setdefault("exclusions", [])
    ss.setdefault(
        "cache_manager",
        CacheManager(
            config.cache_dir,
            DailyRequestBudget(
                config.cache_dir / ".budget.json", config.daily_request_budget
            ),
        ),
    )
    ss.setdefault("client", TelraamClient(config.api_key))
    ss.setdefault("_data", None)
    ss.setdefault("_data_segment", None)
    ss.setdefault("_data_start", None)
    ss.setdefault("_data_end", None)


def ensure_data(
    segment_id: str,
    start: date,
    end: date,
    progress_callback=None,
) -> tuple[pd.DataFrame, str | None]:
    """Return data for [start, end], reusing the session cache where possible."""
    ss = st.session_state
    config: Config = ss["config"]

    if not config.is_allowed_segment(segment_id):
        return pd.DataFrame(), f"Segment {segment_id} is not in the allowlist."
    if start >= end:
        return pd.DataFrame(), "The selected periods do not cover any dates."

    cached = ss["_data"]
    if (
        cached is not None
        and ss["_data_segment"] == segment_id
        and ss["_data_start"] is not None
        and ss["_data_start"] <= start
        and ss["_data_end"] >= end
    ):
        return _slice(cached, start, end), None

    try:
        df = ss["cache_manager"].get_or_fetch(
            segment_id=segment_id,
            level=config.default_level,
            fmt=config.default_format,
            start=start,
            end=end,
            client=ss["client"],
            progress_callback=progress_callback,
        )
    except BudgetExceeded as exc:
        return pd.DataFrame(), str(exc)
    except Exception as exc:  # network / API errors
        return pd.DataFrame(), f"Could not load data: {exc}"

    ss["_data"] = df
    ss["_data_segment"] = segment_id
    ss["_data_start"] = start
    ss["_data_end"] = end
    return df, None


def _slice(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.loc[
        pd.Timestamp(start, tz="UTC") : pd.Timestamp(end, tz="UTC")
    ]


def get_controls() -> Controls:
    return st.session_state["controls"]


def prepared_df(keep_only_assigned: bool = False) -> pd.DataFrame:
    """Apply exclusions, filters and period labels to the loaded frame."""
    controls = get_controls()
    df = controls.df
    if df is None or df.empty:
        return pd.DataFrame()

    df = drop_exclusions(df, controls.exclusions)
    df = filter_time_of_day(
        df, controls.filters.start_hour, controls.filters.end_hour
    )
    df = filter_days_of_week(df, controls.filters.selected_days)
    df = label_periods(df, controls.instances)

    if keep_only_assigned:
        df = df[df["period_label"].notna()].copy()
    return df


def reset_data() -> None:
    ss = st.session_state
    ss["_data"] = None
    ss["_data_segment"] = None
