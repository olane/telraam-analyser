from __future__ import annotations

import pandas as pd

from analysis.filters import (
    MODALITY_GROUPS,
    add_derived_modalities,
    dedupe_modalities,
    get_available_groups,
    get_available_modalities,
)
from domain.models import base_of, group_of, is_directional, modality_label


def test_is_directional_flags_split_variants():
    assert is_directional("car_lft")
    assert is_directional("night_rgt")
    assert not is_directional("car")
    assert not is_directional("night")


def test_base_of_strips_direction_suffix():
    assert base_of("car_lft") == "car"
    assert base_of("night_rgt") == "night"
    assert base_of("car") == "car"


def test_group_of_maps_motorised_components():
    assert group_of("car") == "motorised"
    assert group_of("heavy") == "motorised"
    assert group_of("night") == "motorised"
    assert group_of("night_lft") == "motorised"
    assert group_of("pedestrian") is None
    assert group_of("motorised") is None


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
            "heavy": [3.0],
        }
    )
    assert get_available_groups(df) == []

    df["night"] = 4.0
    assert get_available_groups(df) == ["motorised"]


def test_add_derived_modalities_sums_parts():
    df = pd.DataFrame(
        {
            "car": [1.0, 2.0],
            "heavy": [10.0, 20.0],
            "night": [100.0, 200.0],
        }
    )
    out = add_derived_modalities(df)
    assert list(out["motorised"]) == [111.0, 222.0]


def test_add_derived_modalities_scales_night_share(monkeypatch):
    monkeypatch.setitem(
        MODALITY_GROUPS, "motorised", {"car": 1.0, "heavy": 1.0, "night": 0.5}
    )
    df = pd.DataFrame(
        {"car": [2.0], "heavy": [3.0], "night": [10.0]}
    )
    out = add_derived_modalities(df)
    assert list(out["motorised"]) == [10.0]


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


def test_dedupe_group_supersedes_components():
    assert dedupe_modalities(
        ["pedestrian", "motorised", "car", "heavy", "night"]
    ) == ["pedestrian", "motorised"]


def test_dedupe_group_supersedes_directional_components():
    assert dedupe_modalities(["motorised", "car_lft", "car_rgt"]) == ["motorised"]
