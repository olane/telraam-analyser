from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from api_client import TelraamClient, chunk_count
from domain.models import FetchParams
from guard import BudgetExceeded, DailyRequestBudget, KeyedLocks


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
        gaps = _find_gaps(cached, start, end)

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
        if not frames:
            return pd.DataFrame()

        merged = pd.concat(frames)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        self._save_cache(path, merged)
        return _slice(merged, start, end)


def _slice(df: pd.DataFrame | None, start: date, end: date) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    return df.loc[start_ts:end_ts]


def _find_gaps(
    cached: pd.DataFrame | None,
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """Determine which date ranges are missing from the cache."""
    from datetime import date as date_type

    if cached is None or cached.empty:
        return [(start, end)]

    cached_start = cached.index.min().date()
    cached_end = cached.index.max().date()
    today = date_type.today()

    gaps: list[tuple[date, date]] = []

    if start < cached_start:
        gaps.append((start, min(cached_start, end)))

    # Only fetch beyond cached_end if there is genuinely new data to get.
    if end > cached_end and cached_end < today:
        gaps.append((max(cached_end, start), min(end, today + timedelta(days=1))))

    return gaps
