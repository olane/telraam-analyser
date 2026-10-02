from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from api_client import TelraamClient, _parse_iso_date
from cache import CacheManager, _find_gaps, _merge_intervals, _utc_today
from domain.models import SegmentInfo
from guard import DailyRequestBudget, KeyedLocks


def test_budget_reserves_up_to_limit(tmp_path):
    budget = DailyRequestBudget(tmp_path / "budget.json", limit=3)
    assert budget.try_reserve(2) is True
    assert budget.remaining() == 1
    assert budget.try_reserve(2) is False
    assert budget.try_reserve(1) is True
    assert budget.remaining() == 0


def test_budget_persists_across_instances(tmp_path):
    path = tmp_path / "budget.json"
    first = DailyRequestBudget(path, limit=5)
    first.try_reserve(2)
    second = DailyRequestBudget(path, limit=5)
    assert second.used() == 2


def test_keyed_locks_return_same_lock():
    locks = KeyedLocks()
    assert locks.get("a") is locks.get("a")
    assert locks.get("a") is not locks.get("b")


# -- gaps -------------------------------------------------------------------


def test_find_gaps_full_range_when_uncovered():
    gaps = _find_gaps([], date(2025, 1, 1), date(2025, 2, 1))
    assert gaps == [(date(2025, 1, 1), date(2025, 2, 1))]


def test_find_gaps_before_and_after_coverage():
    coverage = [(date(2025, 1, 10), date(2025, 1, 20))]
    gaps = _find_gaps(coverage, date(2025, 1, 1), date(2025, 2, 1))
    assert gaps == [
        (date(2025, 1, 1), date(2025, 1, 10)),
        (date(2025, 1, 20), date(2025, 2, 1)),
    ]


def test_find_gaps_none_when_coverage_covers():
    coverage = [(date(2024, 1, 1), date(2026, 1, 1))]
    assert _find_gaps(coverage, date(2025, 1, 1), date(2025, 2, 1)) == []


def test_find_gaps_ignore_empty_and_inverted_ranges():
    assert _find_gaps([], date(2025, 2, 1), date(2025, 1, 1)) == []


def test_merge_intervals_coalesces_and_sorts():
    merged = _merge_intervals(
        [
            (date(2025, 3, 1), date(2025, 4, 1)),
            (date(2025, 1, 1), date(2025, 2, 1)),
            (date(2025, 2, 1), date(2025, 3, 1)),
        ]
    )
    assert merged == [(date(2025, 1, 1), date(2025, 4, 1))]


def test_parse_iso_date_handles_z_and_junk():
    assert _parse_iso_date("2022-07-04T12:00:20.148Z") == date(2022, 7, 4)
    assert _parse_iso_date(None) is None
    assert _parse_iso_date("not-a-date") is None


# -- cache manager ----------------------------------------------------------


class FakeClient:
    """Serves a contiguous block of hourly data in [data_start, data_end)."""

    def __init__(self, data_start: date | None = None, data_end: date | None = None):
        self.data_start = data_start
        self.data_end = data_end
        self.traffic_calls: list[tuple[date, date]] = []
        self.info_calls = 0
        self.info = SegmentInfo()

    def fetch_traffic(self, params, progress_callback=None):
        self.traffic_calls.append((params.time_start, params.time_end))
        if self.data_start is None or self.data_end is None:
            return pd.DataFrame()
        start = max(params.time_start, self.data_start)
        end = min(params.time_end, self.data_end)
        if start >= end:
            return pd.DataFrame()
        index = pd.date_range(start, end, freq="h", tz="UTC", inclusive="left")
        return pd.DataFrame({"car": 1.0}, index=index)

    def fetch_segment_info(self, segment_id):
        self.info_calls += 1
        return self.info


def test_cache_reuses_overlapping_gaps(tmp_path):
    client = FakeClient(date(2025, 1, 1), date(2025, 6, 1))
    manager = CacheManager(tmp_path)

    first = manager.get_or_fetch(
        "seg", "segments", "per-hour", date(2025, 3, 1), date(2025, 4, 1), client
    )
    assert not first.empty
    assert client.traffic_calls == [(date(2025, 3, 1), date(2025, 4, 1))]

    # A range fully inside what we already fetched triggers no request.
    again = manager.get_or_fetch(
        "seg", "segments", "per-hour", date(2025, 3, 15), date(2025, 3, 20), client
    )
    assert not again.empty
    assert len(client.traffic_calls) == 1


def test_cache_records_empty_ranges(tmp_path):
    client = FakeClient(date(2025, 3, 1), date(2025, 4, 1))
    manager = CacheManager(tmp_path)

    empty = manager.get_or_fetch(
        "seg", "segments", "per-hour", date(2025, 1, 1), date(2025, 2, 1), client
    )
    assert empty.empty
    assert len(client.traffic_calls) == 1

    # The empty stretch is remembered: a fresh manager makes no request.
    fresh = CacheManager(tmp_path)
    empty_again = fresh.get_or_fetch(
        "seg", "segments", "per-hour", date(2025, 1, 1), date(2025, 2, 1), client
    )
    assert empty_again.empty
    assert len(client.traffic_calls) == 1


def test_history_start_skips_empty_prefix(tmp_path):
    client = FakeClient(date(2025, 3, 1), date(2025, 6, 1))
    client.info = SegmentInfo(first_data=date(2025, 3, 1))
    manager = CacheManager(tmp_path)

    manager.get_or_fetch(
        "seg", "segments", "per-hour", date(2021, 2, 1), date(2025, 4, 1), client
    )

    # Only the segment's real history was requested, not the empty prefix.
    assert client.traffic_calls == [(date(2025, 3, 1), date(2025, 4, 1))]
    assert client.info_calls == 1

    # The metadata is cached, so a second call does not re-ask.
    manager.get_or_fetch(
        "seg", "segments", "per-hour", date(2021, 2, 1), date(2025, 4, 1), client
    )
    assert client.info_calls == 1


def test_cache_covers_only_up_to_today(tmp_path):
    today = _utc_today()
    client = FakeClient(today - timedelta(days=30), today)
    manager = CacheManager(tmp_path)

    manager.get_or_fetch(
        "seg",
        "segments",
        "per-hour",
        today - timedelta(days=10),
        today + timedelta(days=1),
        client,
    )
    path = manager._cache_path("seg", "segments", "per-hour")
    coverage = manager._load_coverage(path, None)
    assert coverage
    assert all(end <= today for _, end in coverage)


def test_load_segment_info_is_reused(tmp_path):
    client = FakeClient()
    client.info = SegmentInfo(first_data=date(2025, 3, 1))
    manager = CacheManager(tmp_path)

    manager._history_start("seg", date(2021, 2, 1), client)
    manager._history_start("seg", date(2021, 2, 1), client)
    assert client.info_calls == 1


def test_parse_segment_info_response():
    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {
                "features": [
                    {
                        "properties": {
                            "first_data_package": "2022-07-04T12:00:20.148Z",
                            "last_data_package": "2024-06-20T14:15:23.400Z",
                            "timezone": "Europe/Brussels",
                        }
                    }
                ]
            }

    client = TelraamClient("key")
    client._session = type("S", (), {"get": lambda self, url: Response()})()
    info = client.fetch_segment_info("9000001463")
    assert info.first_data == date(2022, 7, 4)
    assert info.last_data == date(2024, 6, 20)
    assert info.timezone == "Europe/Brussels"
