"""Server-side guards for a publicly reachable deployment.

A fully public app shares one API key, so a single visitor can trigger a lot
of upstream requests. Two protections live here:

* :class:`DailyRequestBudget` — a file-backed counter that stops the app from
  burning through the Telraam daily quota.
* :class:`KeyedLocks` — coalesces concurrent fetches for the same cache key so
  N simultaneous visitors cause one fetch, not N.
"""

from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path


class BudgetExceeded(RuntimeError):
    """Raised when a fetch would exceed the configured daily request budget."""


class DailyRequestBudget:
    def __init__(self, path: Path, limit: int = 900):
        self.path = Path(path)
        self.limit = limit
        self._lock = threading.Lock()

    def _today(self) -> str:
        return date.today().isoformat()

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (OSError, ValueError):
            return {}

    def used(self) -> int:
        return int(self._read().get(self._today(), 0))

    def remaining(self) -> int:
        return max(0, self.limit - self.used())

    def try_reserve(self, n: int = 1) -> bool:
        """Atomically reserve *n* requests for today, or return False."""
        if n <= 0:
            return True
        with self._lock:
            used = int(self._read().get(self._today(), 0))
            if used + n > self.limit:
                return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({self._today(): used + n}))
            return True


class KeyedLocks:
    """A registry of per-key re-entrant locks."""

    def __init__(self) -> None:
        self._locks: dict[str, threading.RLock] = {}
        self._guard = threading.Lock()

    def get(self, key: str) -> threading.RLock:
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.RLock()
                self._locks[key] = lock
            return lock
