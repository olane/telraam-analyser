from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Callable

import pandas as pd
import requests

from models import FetchParams

API_BASE = "https://telraam-api.net/v1"
MAX_CHUNK_DAYS = 90


class TelraamAPIError(Exception):
    pass


class TelraamClient:
    def __init__(self, api_key: str, sleep_seconds: float = 1.0):
        self.api_key = api_key
        self.sleep_seconds = sleep_seconds
        self._session = requests.Session()
        self._session.headers["X-Api-Key"] = api_key
        self._last_request_time: float = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.sleep_seconds:
            time.sleep(self.sleep_seconds - elapsed)

    def _post_traffic(self, params: FetchParams) -> list[dict]:
        self._rate_limit()
        body = {
            "id": params.segment_id,
            "time_start": params.time_start.strftime("%Y-%m-%d %H:%M:%SZ"),
            "time_end": params.time_end.strftime("%Y-%m-%d %H:%M:%SZ"),
            "level": params.level,
            "format": params.format,
        }
        resp = self._session.post(f"{API_BASE}/reports/traffic", json=body)
        self._last_request_time = time.monotonic()

        if resp.status_code != 200:
            raise TelraamAPIError(
                f"API returned {resp.status_code}: {resp.text[:500]}"
            )

        data = resp.json()
        report = data.get("report", [])
        if not isinstance(report, list):
            raise TelraamAPIError(f"Unexpected report format: {type(report)}")
        return report

    def fetch_traffic(
        self,
        params: FetchParams,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> pd.DataFrame:
        """Fetch traffic data, auto-chunking requests that exceed 90 days."""
        chunks = _split_into_chunks(params)
        total = len(chunks)
        all_records: list[dict] = []

        for i, chunk in enumerate(chunks):
            records = self._post_traffic(chunk)
            all_records.extend(records)
            if progress_callback:
                progress_callback(i + 1, total)

        if not all_records:
            return pd.DataFrame()

        df = pd.DataFrame(all_records)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df = df.set_index("date").sort_index()
        return df


def _split_into_chunks(params: FetchParams) -> list[FetchParams]:
    """Split a date range into <=90-day chunks."""
    chunks: list[FetchParams] = []
    current_start = params.time_start
    end = params.time_end

    while current_start < end:
        chunk_end = min(current_start + timedelta(days=MAX_CHUNK_DAYS), end)
        chunks.append(
            FetchParams(
                segment_id=params.segment_id,
                time_start=current_start,
                time_end=chunk_end,
                level=params.level,
                format=params.format,
            )
        )
        current_start = chunk_end

    return chunks
