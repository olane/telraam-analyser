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
    HOLIDAY = "holiday"
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
    PeriodKind.HOLIDAY: "School holidays",
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
    PeriodKind.HOLIDAY,
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


class ComparisonMode(str, Enum):
    """What the comparison charts group by.

    A recipe also decides which calendar periods are marked on trend charts,
    but the *axis* is what matters: instead of one bucket per holiday, rows are
    grouped into a small set of meaningful buckets (term vs holiday, before vs
    after, weekday vs weekend, ...).
    """

    HOLIDAY_VS_TERM = "holiday_vs_term"
    YEAR_ON_YEAR = "year_on_year"
    BEFORE_AFTER = "before_after"
    WEEKDAY_VS_WEEKEND = "weekday_vs_weekend"
    TIME_OF_DAY = "time_of_day"
    ROADWORKS = "roadworks"
    CUSTOM = "custom"

    @property
    def human(self) -> str:
        return {
            ComparisonMode.HOLIDAY_VS_TERM: "Term time vs holidays",
            ComparisonMode.YEAR_ON_YEAR: "Same period, previous year",
            ComparisonMode.BEFORE_AFTER: "Before / after an intervention",
            ComparisonMode.WEEKDAY_VS_WEEKEND: "Weekday vs weekend",
            ComparisonMode.TIME_OF_DAY: "Time of day",
            ComparisonMode.ROADWORKS: "Roadworks vs baseline",
            ComparisonMode.CUSTOM: "Custom periods",
        }[self]


@dataclass
class ComparisonConfig:
    """User-chosen comparison recipe plus its parameters."""

    mode: ComparisonMode = ComparisonMode.HOLIDAY_VS_TERM
    period_labels: list[str] = field(default_factory=list)
    kind: PeriodKind | None = None
    years: list[str] = field(default_factory=list)
    cutover: date | None = None
    window_days: int = 56
    include_previous_year: bool = False


# Group labels shared by the comparison axes and their charts.
TERM_LABEL = "Term time"
NOT_TERM_LABEL = "Not term time"
HOLIDAY_LABEL = "School holidays"
WEEKDAY_LABEL = "Weekday"
WEEKEND_LABEL = "Weekend"
BASELINE_LABEL = "Baseline"
EXCLUDED_LABEL = "Roadworks"

# Ordered day-part bands used by the time-of-day comparison axis.
TIME_OF_DAY_BANDS: tuple[tuple[str, int, int], ...] = (
    ("Night (0–6)", 0, 6),
    ("Morning school run (7–9)", 7, 9),
    ("Midday (10–14)", 10, 14),
    ("Afternoon school run (15–17)", 15, 17),
    ("Evening (18–23)", 18, 23),
)


def time_of_day_band(hour: int) -> str:
    """Return the ordered time-of-day band label for *hour*."""
    for label, start, end in TIME_OF_DAY_BANDS:
        if start <= hour <= end:
            return label
    return TIME_OF_DAY_BANDS[-1][0]


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
    "night_lft": "Night (left)",
    "night_rgt": "Night (right)",
}

# S2 direction split variants carry a left/right suffix; their base column is
# the sum of the two, so selecting both would double count.
DIRECTIONAL_SUFFIXES = ("_lft", "_rgt")


def is_directional(modality: str) -> bool:
    """True for the left/right split variants (e.g. ``car_lft``)."""
    return modality.endswith(DIRECTIONAL_SUFFIXES)


def base_of(modality: str) -> str:
    """Return the combined-modality name for a directional variant."""
    base, sep, _ = modality.rpartition("_")
    return base if sep else modality


def modality_label(modality: str) -> str:
    """Human-readable name for a modality column."""
    if modality in MODALITY_LABELS:
        return MODALITY_LABELS[modality]
    if is_directional(modality):
        side = "left" if modality.endswith("_lft") else "right"
        return f"{modality_label(base_of(modality))} ({side})"
    return modality.replace("_", " ").title()

# Speed histogram bucket columns (V85 distribution)
SPEED_BUCKETS = [
    "car_speed_hist_0to70plus",
    "car_speed_hist_0to120plus",
]
