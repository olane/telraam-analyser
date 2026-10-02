from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from api_client import TelraamClient, chunk_count
from domain.models import FetchParams, SegmentInfo
from guard import BudgetExceeded, DailyRequestBudget, KeyedLocks

COVERAGE_SUFFIX = ".coverage.json"


def _utc_today() -> date:
    """Today in UTC, matching the timezone of the API's timestamps."""
    return datetime.now(timezone.utc).date()


class CacheManager:
    def __init__(
        self, cache_dir: Path, budget: DailyRequestBudget | None = None
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.budget = budget
        self._locks = KeyedLocks()

    def _cache_path(self, segment_id: str, level: str, fmt: str) -> Path:
        return self.cache_dir / f"{segment_id}_{level}_{fmt}.parquet"

    def _coverage_path(self, path: Path) -> Path:
        return path.with_name(path.stem + COVERAGE_SUFFIX)

    def _segment_info_path(self, segment_id: str) -> Path:
        return self.cache_dir / f"{segment_id}_segment_info.json"

    def _load_cached(self, path: Path) -> pd.DataFrame | None:
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
            if not df.index.empty:
                df.index = pd.to_datetime(df.index, utc=True)
            return df
        except Exception:
            return None

    def _save_cache(self, path: Path, df: pd.DataFrame) -> None:
        df.to_parquet(path, engine="pyarrow")

    # -- coverage metadata -------------------------------------------------
    #
    # The parquet only stores rows that actually came back. Empty stretches
    # (before a sensor was installed, or holes in its history) leave no trace,
    # so without this sidecar the same empty 90-day chunks get re-requested on
    # every fresh session. Coverage records which date ranges we have already
    # asked the API about, whether or not they contained data.

    def _load_coverage(
        self, path: Path, cached: pd.DataFrame | None
    ) -> list[tuple[date, date]]:
        coverage_path = self._coverage_path(path)
        if coverage_path.exists():
            try:
                payload = json.loads(coverage_path.read_text())
                return [
                    (date.fromisoformat(start), date.fromisoformat(end))
                    for start, end in payload["intervals"]
                ]
            except (OSError, ValueError, TypeError, KeyError, AttributeError):
                return []
        # Back-compat: existing caches predate the sidecar, so treat the rows
        # we already hold as the fetched range (still never the current day).
        if cached is not None and not cached.empty:
            start = cached.index.min().date()
            end = min(cached.index.max().date() + timedelta(days=1), _utc_today())
            if start < end:
                return [(start, end)]
        return []

    def _save_coverage(
        self, path: Path, intervals: list[tuple[date, date]]
    ) -> None:
        # Never claim to have covered the current day (or beyond): it is still
        # filling in, so leave a tail gap for the next fetch to top up.
        today = _utc_today()
        clamped = [(start, min(end, today)) for start, end in intervals]
        clamped = [(start, end) for start, end in clamped if start < end]
        payload = {
            "intervals": [
                [start.isoformat(), end.isoformat()]
                for start, end in _merge_intervals(clamped)
            ]
        }
        try:
            self._coverage_path(path).write_text(json.dumps(payload))
        except OSError:
            pass

    # -- segment history ---------------------------------------------------

    def _load_segment_info(self, segment_id: str) -> SegmentInfo | None:
        path = self._segment_info_path(segment_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            first = payload.get("first_data")
            return SegmentInfo(
                first_data=date.fromisoformat(first) if first else None
            )
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    def _save_segment_info(self, segment_id: str, info: SegmentInfo) -> None:
        payload = {
            "first_data": info.first_data.isoformat() if info.first_data else None,
        }
        try:
            self._segment_info_path(segment_id).write_text(json.dumps(payload))
        except OSError:
            pass

    def _history_start(
        self, segment_id: str, start: date, client: TelraamClient
    ) -> date:
        """Clamp *start* up to the segment's first data date, if known.

        The first data date is immutable, so one metadata request per segment
        is cached on disk. Any failure falls back to the requested start.
        """
        info = self._load_segment_info(segment_id)
        if info is None:
            if self.budget is not None and not self.budget.try_reserve(1):
                return start
            try:
                info = client.fetch_segment_info(segment_id)
            except Exception:
                return start
            self._save_segment_info(segment_id, info)
        if info.first_data is not None and info.first_data > start:
            return info.first_data
        return start

    def get_or_fetch(
        self,
        segment_id: str,
        level: str,
        fmt: str,
        start: date,
        end: date,
        client: TelraamClient,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> pd.DataFrame:
        """Return data for the requested range, fetching only missing gaps.

        Concurrent callers for the same segment/level/format are serialised so
        that a public deployment triggers one upstream fetch, not many.
        """
        key = f"{segment_id}|{level}|{fmt}"
        with self._locks.get(key):
            return self._get_or_fetch_locked(
                segment_id, level, fmt, start, end, client, progress_callback
            )

    def _get_or_fetch_locked(
        self,
        segment_id: str,
        level: str,
        fmt: str,
        start: date,
        end: date,
        client: TelraamClient,
        progress_callback: Callable[[int, int], None] | None,
    ) -> pd.DataFrame:
        path = self._cache_path(segment_id, level, fmt)
        cached = self._load_cached(path)
        start = self._history_start(segment_id, start, client)

        coverage = self._load_coverage(path, cached)
        gaps = _find_gaps(coverage, start, end)

        if not gaps:
            return _slice(cached, start, end)

        estimated = sum(chunk_count(g[0], g[1]) for g in gaps)
        if self.budget is not None and not self.budget.try_reserve(estimated):
            raise BudgetExceeded(
                f"Daily API request budget reached (needs {estimated}). "
                "Try again tomorrow or narrow the date range."
            )

        new_frames: list[pd.DataFrame] = []
        for gap_start, gap_end in gaps:
            params = FetchParams(
                segment_id=segment_id,
                time_start=gap_start,
                time_end=gap_end,
                level=level,
                format=fmt,
            )
            df = client.fetch_traffic(params, progress_callback=progress_callback)
            if not df.empty:
                new_frames.append(df)

        frames = [f for f in ([cached] + new_frames) if f is not None and not f.empty]
        if frames:
            merged = pd.concat(frames)
            merged = merged[~merged.index.duplicated(keep="last")].sort_index()
            self._save_cache(path, merged)
        else:
            merged = cached if cached is not None else pd.DataFrame()

        self._save_coverage(path, list(coverage) + list(gaps))
        return _slice(merged, start, end)


def _slice(df: pd.DataFrame | None, start: date, end: date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return df.loc[start_ts:end_ts]


def _merge_intervals(
    intervals: list[tuple[date, date]],
) -> list[tuple[date, date]]:
    """Sort and coalesce touching/overlapping half-open date intervals."""
    merged: list[tuple[date, date]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _find_gaps(
    coverage: list[tuple[date, date]],
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """Sub-ranges of [start, end) that have not been fetched yet."""
    if start >= end:
        return []

    covered = _merge_intervals(
        [
            (max(s, start), min(e, end))
            for s, e in coverage
            if max(s, start) < min(e, end)
        ]
    )

    gaps: list[tuple[date, date]] = []
    cursor = start
    for covered_start, covered_end in covered:
        if covered_start > cursor:
            gaps.append((cursor, covered_start))
        cursor = max(cursor, covered_end)
    if cursor < end:
        gaps.append((cursor, end))
    return gaps
