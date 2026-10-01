from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Telraam's current API (v1) has data from roughly this point onwards. Used
# as the default earliest date for full-history trend requests so we never
# ask the API for decades of empty data.
EARLIEST_DATA = date(2021, 2, 1)

DEFAULT_DAILY_BUDGET = 900


def _setting(key: str, default: str | None = None) -> str | None:
    """Read a setting from Streamlit secrets first, then the environment."""
    try:
        import streamlit as st

        try:
            if key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
    except Exception:
        pass
    return os.getenv(key, default)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    api_key: str
    segment_ids: list[str]
    cache_dir: Path = field(default_factory=lambda: Path("data"))
    default_level: str = "segments"
    default_format: str = "per-hour"
    daily_request_budget: int = DEFAULT_DAILY_BUDGET
    earliest_data: date = EARLIEST_DATA
    allow_all_segments: bool = False

    @classmethod
    def from_env(cls) -> Config:
        api_key = (_setting("TELRAAM_API_KEY") or "").strip()
        raw_ids = _setting("TELRAAM_SEGMENT_IDS") or ""
        segment_ids = [s.strip() for s in raw_ids.split(",") if s.strip()]

        budget_raw = _setting("TELRAAM_DAILY_BUDGET")
        try:
            budget = int(budget_raw) if budget_raw else DEFAULT_DAILY_BUDGET
        except ValueError:
            budget = DEFAULT_DAILY_BUDGET

        return cls(
            api_key=api_key,
            segment_ids=segment_ids,
            daily_request_budget=budget,
            allow_all_segments=_as_bool(_setting("TELRAAM_ALLOW_ALL_SEGMENTS")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.segment_ids)

    def is_allowed_segment(self, segment_id: str) -> bool:
        return self.allow_all_segments or segment_id in self.segment_ids
