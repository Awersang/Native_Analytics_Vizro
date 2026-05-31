"""
Local fixture data used when BigQuery is unavailable (offline dev / CI).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def bike_hire_fixture(n_days: int = 30) -> pd.DataFrame:
    """A small stand-in for the public `london_bicycles.cycle_hire` summary
    used by the bq_sample dashboard when BigQuery cannot be reached."""
    rng = np.random.default_rng(7)
    dates = pd.date_range("2023-01-01", periods=n_days, freq="D")
    stations = ["Hyde Park", "King's Cross", "Waterloo", "Shoreditch", "Camden"]
    rows = []
    for d in dates:
        for s in stations:
            rows.append(
                {
                    "day": d,
                    "station_name": s,
                    "trips": int(rng.integers(200, 2000)),
                    "avg_duration_min": round(float(rng.uniform(8, 35)), 1),
                }
            )
    return pd.DataFrame(rows)


def disinformation_timeline_fixture(n_days: int = 14) -> pd.DataFrame:
    """A stand-in for ``amazon_2025.disinformation_timeline`` used when
    BigQuery cannot be reached (offline dev / CI). Schema mirrors the live
    table: ``day`` (date), ``stage`` (str), ``number_of_publications`` (int).
    """
    rng = np.random.default_rng(11)
    dates = pd.date_range("2025-10-01", periods=n_days, freq="D")
    stages = ["disinformation", "intervened", "corrected", "correct_from_start"]
    rows = []
    for d in dates:
        for s in stages:
            rows.append(
                {
                    "day": d,
                    "stage": s,
                    "number_of_publications": int(rng.integers(0, 50)),
                }
            )
    return pd.DataFrame(rows)
