from __future__ import annotations

import pandas as pd
import pytest

from analysis.filters import (
    add_derived_modalities,
    dedupe_modalities,
    get_available_groups,
    get_available_modalities,
    redistribute_night,
)
from domain.models import base_of, is_directional, modality_label


def test_is_directional_flags_split_variants():
    assert is_directional("car_lft")
    assert is_directional("night_rgt")
    assert not is_directional("car")
    assert not is_directional("night")


def test_base_of_strips_direction_suffix():
    assert base_of("car_lft") == "car"
    assert base_of("night_rgt") == "night"
    assert base_of("car") == "car"


def test_modality_labels_are_human_readable():
    assert modality_label("pedestrian") == "Pedestrians"
    assert modality_label("car_lft") == "Cars (left)"
    assert modality_label("night_rgt") == "Night (right)"
    assert modality_label("motorised") == "Motorised vehicles"


def test_get_available_modalities_excludes_groups():
    df = pd.DataFrame(
        {
            "pedestrian": [1.0],
            "car": [2.0],
            "heavy": [3.0],
            "night": [4.0],
        }
    )
    available = get_available_modalities(df)
    assert "car" in available
    assert "motorised" not in available


def test_get_available_groups_offers_motorised_when_parts_present():
    df = pd.DataFrame(
        {
            "pedestrian": [1.0],
            "car": [2.0],
        }
    )
    assert get_available_groups(df) == []

    df["heavy"] = 3.0
    assert get_available_groups(df) == ["motorised"]


def test_add_derived_modalities_sums_car_and_heavy():
    df = pd.DataFrame(
        {
            "car": [1.0, 2.0],
            "heavy": [10.0, 20.0],
            "night": [100.0, 200.0],
        }
    )
    out = add_derived_modalities(df)
    # motorised is only car + heavy; night is not folded in.
    assert list(out["motorised"]) == [11.0, 22.0]


def test_redistribute_night_moves_counts_and_drops_night():
    df = pd.DataFrame(
        {"bike": [1.0], "car": [2.0], "heavy": [3.0], "night": [100.0]}
    )
    out = redistribute_night(df, {"bike": 0.15, "car": 0.85, "heavy": 0.0})
    assert "night" not in out.columns
    assert out["bike"].tolist() == pytest.approx([16.0])
    assert out["car"].tolist() == pytest.approx([87.0])
    assert out["heavy"].tolist() == pytest.approx([3.0])


def test_redistribute_night_normalises_relative_shares():
    df = pd.DataFrame({"bike": [0.0], "car": [0.0], "night": [10.0]})
    out = redistribute_night(df, {"bike": 1.0, "car": 3.0})
    assert out["bike"].tolist() == pytest.approx([2.5])
    assert out["car"].tolist() == pytest.approx([7.5])


def test_redistribute_night_keeps_direction_splits_in_step():
    df = pd.DataFrame(
        {
            "bike": [0.0],
            "car": [0.0],
            "night": [10.0],
            "night_lft": [4.0],
            "night_rgt": [6.0],
            "car_lft": [0.0],
            "car_rgt": [0.0],
        }
    )
    out = redistribute_night(df, {"car": 1.0})
    assert "night" not in out.columns
    assert "night_lft" not in out.columns
    assert "night_rgt" not in out.columns
    assert list(out["car"]) == [10.0]
    assert list(out["car_lft"]) == [4.0]
    assert list(out["car_rgt"]) == [6.0]


def test_redistribute_night_without_targets_is_a_noop():
    df = pd.DataFrame({"pedestrian": [1.0], "night": [5.0]})
    out = redistribute_night(df, {"car": 1.0})
    assert "night" in out.columns
    assert list(out["night"]) == [5.0]


def test_dedupe_drops_combined_when_split_selected():
    assert dedupe_modalities(["pedestrian", "car", "car_lft", "car_rgt"]) == [
        "pedestrian",
        "car_lft",
        "car_rgt",
    ]


def test_dedupe_keeps_combined_for_untouched_modes():
    assert dedupe_modalities(["pedestrian", "bike", "car"]) == [
        "pedestrian",
        "bike",
        "car",
    ]


def test_dedupe_handles_night_split():
    assert dedupe_modalities(["night", "night_lft", "night_rgt"]) == [
        "night_lft",
        "night_rgt",
    ]
