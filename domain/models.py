"""Domain model for Telraam traffic comparison.

Typed, calendar-aware periods replace the old flat ``PeriodGroup``: every
period now has a *kind* (Christmas holiday, half term, term time, ...), an
optional academic year, and an optional anchor date. This is what makes
"compare similar periods" and year-on-year comparisons possible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

# ---------------------------------------------------------------------------
# Period kinds
# ---------------------------------------------------------------------------


class PeriodKind(str, Enum):
    """Semantic type of a period."""

    TERM = "term"
    AUTUMN_HALF = "autumn_half_term"
    CHRISTMAS = "christmas"
    FEB_HALF = "feb_half_term"
    EASTER = "easter"
    MAY_HALF = "may_half_term"
    SUMMER = "summer"
    CUSTOM = "custom"
    INTERVENTION_BEFORE = "intervention_before"
    INTERVENTION_AFTER = "intervention_after"

    @property
    def human(self) -> str:
        return _KIND_LABELS[self]

    @property
    def is_holiday(self) -> bool:
        return self in HOLIDAY_KINDS

    @property
    def is_term(self) -> bool:
        return self is PeriodKind.TERM

    @property
    def is_intervention(self) -> bool:
        return self in (PeriodKind.INTERVENTION_BEFORE, PeriodKind.INTERVENTION_AFTER)


_KIND_LABELS: dict[PeriodKind, str] = {
    PeriodKind.TERM: "Term time",
    PeriodKind.AUTUMN_HALF: "Autumn half term",
    PeriodKind.CHRISTMAS: "Christmas holiday",
    PeriodKind.FEB_HALF: "February half term",
    PeriodKind.EASTER: "Easter holiday",
    PeriodKind.MAY_HALF: "May half term",
    PeriodKind.SUMMER: "Summer holiday",
    PeriodKind.CUSTOM: "Custom period",
    PeriodKind.INTERVENTION_BEFORE: "Before intervention",
    PeriodKind.INTERVENTION_AFTER: "After intervention",
}

HOLIDAY_KINDS: tuple[PeriodKind, ...] = (
    PeriodKind.AUTUMN_HALF,
    PeriodKind.CHRISTMAS,
    PeriodKind.FEB_HALF,
    PeriodKind.EASTER,
    PeriodKind.MAY_HALF,
    PeriodKind.SUMMER,
)

# Order in which school holidays occur within an academic year.
HOLIDAY_ORDER: dict[PeriodKind, int] = {
    PeriodKind.AUTUMN_HALF: 0,
    PeriodKind.CHRISTMAS: 1,
    PeriodKind.FEB_HALF: 2,
    PeriodKind.EASTER: 3,
    PeriodKind.MAY_HALF: 4,
    PeriodKind.SUMMER: 5,
}


# ---------------------------------------------------------------------------
# Periods and calendars
# ---------------------------------------------------------------------------


DateRange = tuple[date, date]


@dataclass(frozen=True)
class PeriodInstance:
    """A concrete, dated occurrence of a period (e.g. "Christmas 2025-26")."""

    label: str
    kind: PeriodKind
    ranges: tuple[DateRange, ...] = ()
    academic_year: str | None = None
    anchor: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "ranges", tuple((s, e) for s, e in self.ranges)
        )

    @property
    def start(self) -> date | None:
        return min((s for s, _ in self.ranges), default=None)

    @property
    def end(self) -> date | None:
        return max((e for _, e in self.ranges), default=None)

    @property
    def n_days(self) -> int:
        """Number of calendar days covered (inclusive of both endpoints)."""
        return sum((e - s).days + 1 for s, e in self.ranges)


@dataclass(frozen=True)
class Exclusion:
    """A date range to drop from analysis (roadworks, closures, ...)."""

    label: str
    ranges: tuple[DateRange, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "ranges", tuple((s, e) for s, e in self.ranges)
        )


@dataclass
class Calendar:
    """A named collection of period instances (e.g. Cambridge school terms)."""

    name: str
    region: str = ""
    instances: list[PeriodInstance] = field(default_factory=list)

    # -- queries ---------------------------------------------------------

    def years(self) -> list[str]:
        return sorted({i.academic_year for i in self.instances if i.academic_year})

    def by_year(self, academic_year: str) -> list[PeriodInstance]:
        return [i for i in self.instances if i.academic_year == academic_year]

    def of_kind(self, kind: PeriodKind) -> list[PeriodInstance]:
        return [i for i in self.instances if i.kind is kind]

    def labels(self) -> list[str]:
        return [i.label for i in self.instances]

    def get(self, label: str) -> PeriodInstance | None:
        for i in self.instances:
            if i.label == label:
                return i
        return None


# ---------------------------------------------------------------------------
# Comparison configuration
# ---------------------------------------------------------------------------


class Alignment(str, Enum):
    """How to line up periods of different lengths."""

    WEEKDAY = "weekday"
    DAY_INDEX = "day_index"
    ANCHOR = "anchor"
    CALENDAR = "calendar"

    @property
    def human(self) -> str:
        return {
            Alignment.WEEKDAY: "Match like weekdays",
            Alignment.DAY_INDEX: "Count day 1, 2, 3, ...",
            Alignment.ANCHOR: "Days from anchor date",
            Alignment.CALENDAR: "Real calendar dates",
        }[self]


class ComparisonMode(str, Enum):
    """Opinionated comparison recipes."""

    HOLIDAY_VS_TERM = "holiday_vs_term"
    YEAR_ON_YEAR = "year_on_year"
    BY_KIND = "by_kind"
    TREND = "trend"
    BEFORE_AFTER = "before_after"
    CUSTOM = "custom"

    @property
    def human(self) -> str:
        return {
            ComparisonMode.HOLIDAY_VS_TERM: "Holidays vs term time",
            ComparisonMode.YEAR_ON_YEAR: "Year on year (same holiday)",
            ComparisonMode.BY_KIND: "Compare holiday types",
            ComparisonMode.TREND: "Trend over time",
            ComparisonMode.BEFORE_AFTER: "Before / after an intervention",
            ComparisonMode.CUSTOM: "Custom selection",
        }[self]


@dataclass
class ComparisonConfig:
    """User-chosen comparison recipe plus its parameters."""

    mode: ComparisonMode = ComparisonMode.HOLIDAY_VS_TERM
    period_labels: list[str] = field(default_factory=list)
    kind: PeriodKind | None = None
    kinds: list[PeriodKind] = field(default_factory=list)
    years: list[str] = field(default_factory=list)
    alignment: Alignment = Alignment.WEEKDAY
    cutover: date | None = None
    window_days: int = 56
    include_previous_year: bool = False


@dataclass
class FilterSettings:
    start_hour: int = 0
    end_hour: int = 23
    selected_days: list[int] = field(default_factory=lambda: list(range(7)))
    selected_modalities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# API fetch parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchParams:
    segment_id: str
    time_start: date
    time_end: date
    level: str = "segments"
    format: str = "per-hour"


# ---------------------------------------------------------------------------
# Modalities
# ---------------------------------------------------------------------------

CLASSIC_MODALITIES = ["pedestrian", "bike", "car", "heavy"]

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
    "night_lft",
    "night_rgt",
]

# Column order used whenever modalities are listed in the UI.
MODALITY_ORDER = [
    "pedestrian",
    "bike",
    "car",
    "heavy",
    "night",
    "pedestrian_lft",
    "pedestrian_rgt",
    "bike_lft",
    "bike_rgt",
    "car_lft",
    "car_rgt",
    "heavy_lft",
    "heavy_rgt",
    "night_lft",
    "night_rgt",
]

MODALITY_LABELS = {
    "pedestrian": "Pedestrians",
    "bike": "Cycles",
    "car": "Cars",
    "heavy": "Heavy vehicles",
    "night": "Night (all modes)",
}

# Speed histogram bucket columns (V85 distribution)
SPEED_BUCKETS = [
    "car_speed_hist_0to70plus",
    "car_speed_hist_0to120plus",
]
