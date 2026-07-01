"""
Data loader for the Narrative Breakdown dashboard.

Synthetic Amazon media-monitoring dataset (reach/engagement by narrative &
sentiment), scoped to this dashboard package — no "All narratives" aggregate
row, that's only needed by the sibling ``timeline`` dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

DATA_KEY = "breakdown_weekly_narratives"

START_DATE = datetime(2026, 1, 5)
WEEKS = [(i + 1, START_DATE + timedelta(weeks=i)) for i in range(50)]

NARRATIVES = [
    "AWS AI infrastructure and cloud growth",
    "Marketplace seller fees and antitrust scrutiny",
    "Warehouse labor and union actions",
    "Prime Video ads and content strategy",
    "Data-center energy and climate footprint",
]

SMOOTH_PROFILES = {
    "AWS AI infrastructure and cloud growth": dict(
        r_period=22, r_phase=0.0, r_pos=24000, r_neu=31000, r_neg=3000,
        e_period=22, e_phase=0.1, e_pos=1800,  e_neu=2400,  e_neg=280,
    ),
    "Marketplace seller fees and antitrust scrutiny": dict(
        r_period=18, r_phase=2.1, r_pos=2000,  r_neu=18000, r_neg=27000,
        e_period=18, e_phase=2.0, e_pos=180,   e_neu=1500,  e_neg=2100,
    ),
    "Warehouse labor and union actions": dict(
        r_period=16, r_phase=1.2, r_pos=500,   r_neu=12000, r_neg=21000,
        e_period=16, e_phase=1.1, e_pos=80,    e_neu=950,   e_neg=1700,
    ),
    "Prime Video ads and content strategy": dict(
        r_period=25, r_phase=4.5, r_pos=20000, r_neu=16000, r_neg=5000,
        e_period=25, e_phase=4.4, e_pos=1600,  e_neu=1250,  e_neg=400,
    ),
    "Data-center energy and climate footprint": dict(
        r_period=14, r_phase=3.3, r_pos=3000,  r_neu=14000, r_neg=19000,
        e_period=14, e_phase=3.2, e_pos=270,   e_neu=1100,  e_neg=1550,
    ),
}


def _make_wave(arr: np.ndarray, period: float, phase: float, peak: float, sigma: float = 4.5) -> np.ndarray:
    t = 2 * np.pi * arr / period + phase
    raw = peak * np.clip(np.sin(t), 0, None)
    raw = raw * (1 + np.random.normal(0, 0.03, len(raw)))
    return np.clip(gaussian_filter1d(raw, sigma=sigma), 0, None)


def load_weekly_narratives() -> pd.DataFrame:
    """Weekly reach/engagement by narrative & sentiment (no aggregate row).

    Re-seeded on every call so cache refreshes reproduce the same synthetic
    series instead of drifting on each TTL expiry.
    """
    np.random.seed(42)
    n = len(WEEKS)
    week_arr = np.arange(n, dtype=float)
    rows = []

    for narrative in NARRATIVES:
        p = SMOOTH_PROFILES[narrative]
        waves = {
            ("positive", "reach"):      _make_wave(week_arr, p["r_period"], p["r_phase"],       p["r_pos"]),
            ("neutral",  "reach"):      _make_wave(week_arr, p["r_period"], p["r_phase"] + 0.6, p["r_neu"]),
            ("negative", "reach"):      _make_wave(week_arr, p["r_period"], p["r_phase"] + 1.3, p["r_neg"]),
            ("positive", "engagement"): _make_wave(week_arr, p["e_period"], p["e_phase"],       p["e_pos"]),
            ("neutral",  "engagement"): _make_wave(week_arr, p["e_period"], p["e_phase"] + 0.6, p["e_neu"]),
            ("negative", "engagement"): _make_wave(week_arr, p["e_period"], p["e_phase"] + 1.3, p["e_neg"]),
        }
        for i, (_, week_start) in enumerate(WEEKS):
            for sentiment in ("positive", "neutral", "negative"):
                rows.append({
                    "week_start":      week_start,
                    "narrative_label": narrative,
                    "sentiment":       sentiment,
                    "reach":           int(waves[(sentiment, "reach")][i]),
                    "engagement":      int(waves[(sentiment, "engagement")][i]),
                })

    df = pd.DataFrame(rows)
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df
