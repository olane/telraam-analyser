"""Period group presets and save/load to JSON."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

PRESETS_DIR = Path("saved_periods")

# ---------------------------------------------------------------------------
# Cambridge (Cambridgeshire) school holidays 2025-26
# Source: https://www.cambridgeshire.gov.uk/residents/children-and-families/schools-learning/school-term-dates-closures
# ---------------------------------------------------------------------------

_CAMBRIDGE_HOLIDAYS_2025_26 = [
    (date(2025, 10, 27), date(2025, 10, 31)),  # Autumn half term
    (date(2025, 12, 22), date(2026, 1, 2)),     # Christmas
    (date(2026, 2, 16), date(2026, 2, 20)),     # February half term
    (date(2026, 3, 30), date(2026, 4, 10)),     # Easter
    (date(2026, 5, 25), date(2026, 5, 29)),     # May half term
]

_CAMBRIDGE_TERMS_2025_26 = [
    (date(2025, 9, 1), date(2025, 10, 24)),     # Autumn 1
    (date(2025, 11, 3), date(2025, 12, 19)),    # Autumn 2
    (date(2026, 1, 5), date(2026, 2, 13)),      # Spring 1
    (date(2026, 2, 23), date(2026, 3, 27)),     # Spring 2
    (date(2026, 4, 13), date(2026, 5, 22)),     # Summer 1
    (date(2026, 6, 1), date(2026, 7, 20)),      # Summer 2
]

WEEKDAYS = [0, 1, 2, 3, 4]  # Mon-Fri

# Each preset is a dict with "groups" and optional "days" (day-of-week filter)
BUILTIN_PRESETS: dict[str, dict] = {
    "Cambridge: Term vs Holidays 2025-26": {
        "groups": [
            {"name": "Term time", "ranges": _CAMBRIDGE_TERMS_2025_26},
            {"name": "School holidays", "ranges": _CAMBRIDGE_HOLIDAYS_2025_26},
        ],
        "days": WEEKDAYS,
    },
    "Cambridge: Term time 2025-26": {
        "groups": [
            {"name": "Term time", "ranges": _CAMBRIDGE_TERMS_2025_26},
        ],
        "days": WEEKDAYS,
    },
    "Cambridge: School holidays 2025-26": {
        "groups": [
            {"name": "School holidays", "ranges": _CAMBRIDGE_HOLIDAYS_2025_26},
        ],
        "days": WEEKDAYS,
    },
}


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------

def _serialise_groups(groups: list[dict]) -> list[dict]:
    """Convert groups with date objects to JSON-safe dicts."""
    out = []
    for g in groups:
        out.append({
            "name": g["name"],
            "ranges": [[s.isoformat(), e.isoformat()] for s, e in g["ranges"]],
        })
    return out


def _deserialise_groups(raw: list[dict]) -> list[dict]:
    """Convert JSON dicts back to groups with date objects."""
    out = []
    for g in raw:
        out.append({
            "name": g["name"],
            "ranges": [
                (date.fromisoformat(s), date.fromisoformat(e))
                for s, e in g["ranges"]
            ],
        })
    return out


def save_period_groups(name: str, groups: list[dict]) -> Path:
    """Save period groups to a JSON file. Returns the file path."""
    PRESETS_DIR.mkdir(exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    path = PRESETS_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(_serialise_groups(groups), indent=2))
    return path


def list_saved() -> list[str]:
    """Return names of saved period group files."""
    if not PRESETS_DIR.exists():
        return []
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def load_period_groups(name: str) -> list[dict]:
    """Load period groups from a saved JSON file."""
    path = PRESETS_DIR / f"{name}.json"
    raw = json.loads(path.read_text())
    return _deserialise_groups(raw)
