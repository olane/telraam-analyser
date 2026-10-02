from __future__ import annotations

from analysis.filters import dedupe_modalities
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
