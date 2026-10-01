from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from cache import _find_gaps
from guard import DailyRequestBudget, KeyedLocks


def test_budget_reserves_up_to_limit(tmp_path):
    budget = DailyRequestBudget(tmp_path / "budget.json", limit=3)
    assert budget.try_reserve(2) is True
    assert budget.remaining() == 1
    assert budget.try_reserve(2) is False
    assert budget.try_reserve(1) is True
    assert budget.remaining() == 0


def test_budget_persists_across_instances(tmp_path):
    path = tmp_path / "budget.json"
    first = DailyRequestBudget(path, limit=5)
    first.try_reserve(2)
    second = DailyRequestBudget(path, limit=5)
    assert second.used() == 2


def test_keyed_locks_return_same_lock():
    locks = KeyedLocks()
    assert locks.get("a") is locks.get("a")
    assert locks.get("a") is not locks.get("b")


def test_find_gaps_full_range_when_empty():
    gaps = _find_gaps(None, date(2025, 1, 1), date(2025, 2, 1))
    assert gaps == [(date(2025, 1, 1), date(2025, 2, 1))]


def test_find_gaps_before_and_after_cache():
    index = pd.date_range("2025-01-10", "2025-01-20", freq="h", tz="UTC")
    cached = pd.DataFrame({"car": 1.0}, index=index)
    gaps = _find_gaps(cached, date(2025, 1, 1), date(2025, 2, 1))
    assert (date(2025, 1, 1), date(2025, 1, 10)) in gaps
    assert any(g[0] == date(2025, 1, 20) for g in gaps)


def test_find_gaps_none_when_cache_covers():
    today = date.today()
    index = pd.date_range(today - timedelta(days=30), today, freq="h", tz="UTC")
    cached = pd.DataFrame({"car": 1.0}, index=index)
    gaps = _find_gaps(cached, today - timedelta(days=10), today)
    assert gaps == []
