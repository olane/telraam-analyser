from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def make_df():
    """Factory for synthetic hourly traffic frames."""

    def _make(start: str, end: str, base: float = 10.0, by_weekday=None):
        index = pd.date_range(start, end, freq="h", tz="UTC")
        df = pd.DataFrame(index=index)
        df.index.name = "date"
        df["pedestrian"] = base * 0.2
        df["bike"] = base * 0.3
        df["car"] = base
        df["heavy"] = base * 0.05
        if by_weekday:
            multiplier = (
                index.dayofweek.map(lambda d: by_weekday.get(d, 1.0))
                .astype(float)
                .to_numpy()
            )
            for column in ["pedestrian", "bike", "car", "heavy"]:
                df[column] = df[column].to_numpy() * multiplier
        return df

    return _make
