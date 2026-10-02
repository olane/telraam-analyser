"""Filtering and period-labelling functions (pure: DataFrame in, out)."""

from __future__ import annotations

import pandas as pd

from domain.models import (
    MODALITY_ORDER,
    Exclusion,
    PeriodInstance,
    is_directional,
)

# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def get_available_modalities(df: pd.DataFrame) -> list[str]:
    """Return modality columns present in *df*, in a sensible order."""
    return [m for m in MODALITY_ORDER if m in df.columns]


def dedupe_modalities(modalities: list[str]) -> list[str]:
    """Drop a combined modality when its directional variants are selected.

    ``car`` is the sum of ``car_lft`` and ``car_rgt``, so summing all three
    double counts. Prefer the directional split when both are present.
    """
    selected = set(modalities)
    out: list[str] = []
    for modality in modalities:
        if not is_directional(modality) and (
            f"{modality}_lft" in selected or f"{modality}_rgt" in selected
        ):
            continue
        out.append(modality)
    return out


def get_speed_hist_columns(df: pd.DataFrame) -> str | None:
    """Return the speed histogram column name if present, else None."""
    for col in ("car_speed_hist_0to120plus", "car_speed_hist_0to70plus"):
        if col in df.columns:
            return col
    return None


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _end_of_day(d) -> pd.Timestamp:
    return pd.Timestamp(d, tz="UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59)


def _range_mask(index: pd.DatetimeIndex, ranges) -> pd.Series:
    mask = pd.Series(False, index=index)
    for start, end in ranges:
        mask |= (index >= pd.Timestamp(start, tz="UTC")) & (index <= _end_of_day(end))
    return mask


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``hour``, ``weekday`` (0=Mon) and ``day`` columns."""
    df = df.copy()
    df["hour"] = df.index.hour
    df["weekday"] = df.index.dayofweek
    df["day"] = df.index.normalize()
    return df


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_time_of_day(
    df: pd.DataFrame, start_hour: int, end_hour: int
) -> pd.DataFrame:
    """Keep only rows whose hour falls within [start_hour, end_hour]."""
    if "hour" not in df.columns:
        df = add_time_columns(df)
    return df[(df["hour"] >= start_hour) & (df["hour"] <= end_hour)]


def filter_days_of_week(df: pd.DataFrame, days: list[int]) -> pd.DataFrame:
    """Keep only rows whose weekday is in *days* (0=Monday … 6=Sunday)."""
    if "weekday" not in df.columns:
        df = add_time_columns(df)
    return df[df["weekday"].isin(days)]


def _exclusion_mask(
    index: pd.DatetimeIndex, exclusions: list[Exclusion]
) -> pd.Series:
    mask = pd.Series(False, index=index)
    for exclusion in exclusions:
        if exclusion.ranges:
            mask |= _range_mask(index, exclusion.ranges)
    return mask


def mark_exclusions(
    df: pd.DataFrame, exclusions: list[Exclusion]
) -> pd.DataFrame:
    """Flag excluded rows without dropping them.

    The roadworks comparison axis needs to keep excluded rows so it can bucket
    them against the baseline; every other axis drops them in
    :func:`analysis.pipeline.prepare_frame`.
    """
    df = df.copy()
    df["is_excluded"] = (
        _exclusion_mask(df.index, exclusions)
        if exclusions
        else False
    )
    return df


# ---------------------------------------------------------------------------
# Period labelling
# ---------------------------------------------------------------------------

def label_periods(
    df: pd.DataFrame, instances: list[PeriodInstance]
) -> pd.DataFrame:
    """Add ``period_label``/``period_kind``/``academic_year`` columns.

    Unlike the old behaviour, rows outside every period are *kept* (with a
    null label) so they can still be drawn on continuous trend charts.
    """
    df = add_time_columns(df)
    df["period_label"] = None
    df["period_kind"] = None
    df["academic_year"] = None

    for instance in instances:
        if not instance.ranges:
            continue
        mask = _range_mask(df.index, instance.ranges)
        df.loc[mask, "period_label"] = instance.label
        df.loc[mask, "period_kind"] = instance.kind.value
        df.loc[mask, "academic_year"] = instance.academic_year

    return df


def keep_assigned(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows that fall inside one of the labelled periods."""
    if "period_label" not in df.columns:
        raise KeyError("label_periods() must be called before keep_assigned()")
    return df[df["period_label"].notna()].copy()


def add_weekday_occurrence(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``weekday_occurrence`` (1st/2nd/... Monday within each period)."""
    if "period_label" not in df.columns:
        raise KeyError("label_periods() must be called first")
    df = df.copy()
    day_weekday = df[["period_label", "day", "weekday"]].drop_duplicates()
    day_weekday["weekday_occurrence"] = (
        day_weekday.groupby(["period_label", "weekday"]).cumcount() + 1
    )
    return df.merge(
        day_weekday, on=["period_label", "day", "weekday"], how="left"
    )
