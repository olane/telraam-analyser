from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class PeriodGroup:
    name: str
    ranges: list[tuple[date, date]] = field(default_factory=list)


@dataclass
class FilterSettings:
    start_hour: int = 0
    end_hour: int = 23
    selected_days: list[int] = field(default_factory=lambda: list(range(7)))
    selected_modalities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FetchParams:
    segment_id: str
    time_start: date
    time_end: date
    level: str = "segments"
    format: str = "per-hour"


# Classic modalities (V1 sensors / basic)
CLASSIC_MODALITIES = ["pedestrian", "bike", "car", "heavy"]

# S2 modalities (advanced sensors)
S2_MODALITIES = [
    "pedestrian",
    "bike",
    "car",
    "heavy",
    "pedestrian_lft",
    "pedestrian_rgt",
    "bike_lft",
    "bike_rgt",
    "car_lft",
    "car_rgt",
    "heavy_lft",
    "heavy_rgt",
]

# Speed histogram bucket columns (V85 distribution)
SPEED_BUCKETS = [
    "car_speed_hist_0to70plus",
    "car_speed_hist_0to120plus",
]
