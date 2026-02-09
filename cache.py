from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from api_client import TelraamClient
from models import FetchParams


class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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
        """Return data for the requested range, fetching only missing gaps."""
        path = self._cache_path(segment_id, level, fmt)
        cached = self._load_cached(path)

        gaps = _find_gaps(cached, start, end)

        if not gaps:
            # All data is cached — slice and return
            start_ts = pd.Timestamp(start, tz="UTC")
            end_ts = pd.Timestamp(end, tz="UTC")
            return cached.loc[start_ts:end_ts]  # type: ignore[union-attr]

        # Fetch missing ranges
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

        # Merge with existing cache
        frames = [f for f in ([cached] + new_frames) if f is not None and not f.empty]
        if not frames:
            return pd.DataFrame()

        merged = pd.concat(frames)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        self._save_cache(path, merged)

        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        return merged.loc[start_ts:end_ts]


def _find_gaps(
    cached: pd.DataFrame | None,
    start: date,
    end: date,
) -> list[tuple[date, date]]:
    """Determine which date ranges are missing from the cache."""
    if cached is None or cached.empty:
        return [(start, end)]

    cached_start = cached.index.min().date()
    cached_end = cached.index.max().date()

    gaps: list[tuple[date, date]] = []

    if start < cached_start:
        gaps.append((start, min(cached_start, end)))

    if end > cached_end:
        gaps.append((max(cached_end, start), end))

    return gaps
