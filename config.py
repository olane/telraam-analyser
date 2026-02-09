from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_key: str
    segment_ids: list[str]
    cache_dir: Path = Path("data")
    default_level: str = "segments"
    default_format: str = "per-hour"

    @classmethod
    def from_env(cls) -> Config:
        api_key = os.getenv("TELRAAM_API_KEY", "")
        raw_ids = os.getenv("TELRAAM_SEGMENT_IDS", "")
        segment_ids = [s.strip() for s in raw_ids.split(",") if s.strip()]
        return cls(api_key=api_key, segment_ids=segment_ids)
