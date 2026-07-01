"""
Data loaders for the Reach & Engagement Timeline dashboard.

Synthetic Amazon media-monitoring dataset, scoped to this dashboard package.
``load_weekly`` includes the "All narratives" aggregate row the timeline
chart groups on; the sibling ``breakdown`` dashboard keeps its own narrower
copy without it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

WEEKLY_KEY = "timeline_weekly"
CAMPAIGNS_KEY = "timeline_campaigns"

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


def load_weekly() -> pd.DataFrame:
    """Weekly reach/engagement by narrative & sentiment, plus an "All
    narratives" aggregate row used by the dual-axis timeline chart.

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

    # "All narratives" aggregate
    agg = (
        df.groupby(["week_start", "sentiment"], as_index=False)[["reach", "engagement"]]
        .sum()
        .assign(narrative_label="All narratives")
    )
    return pd.concat([df, agg], ignore_index=True)


def load_campaigns() -> pd.DataFrame:
    """Campaign schedule enriched with total reach over each campaign window."""
    df_weekly = load_weekly()
    weekly_all = (
        df_weekly[df_weekly["narrative_label"] == "All narratives"]
        .groupby("week_start", as_index=False)[["reach", "engagement"]]
        .sum()
    )

    raw = pd.DataFrame(
        [
            ["C01", "AWS AI infrastructure positioning",   datetime(2026, 1, 12), datetime(2026, 5, 10)],
            ["C02", "Marketplace seller trust initiative", datetime(2026, 3,  2), datetime(2026, 7, 19)],
            ["C03", "Prime Day promotional campaign",      datetime(2026, 5, 18), datetime(2026, 9, 27)],
            ["C04", "Prime Video autumn content push",     datetime(2026, 7,  6), datetime(2026, 11, 22)],
            ["C05", "Sustainability & data-center energy", datetime(2026, 9, 28), datetime(2026, 12, 27)],
        ],
        columns=["campaign_id", "campaign_label", "campaign_start", "campaign_end"],
    )
    raw["campaign_start"] = pd.to_datetime(raw["campaign_start"])
    raw["campaign_end"]   = pd.to_datetime(raw["campaign_end"])

    def _campaign_reach(row):
        mask = (
            (weekly_all["week_start"] >= row["campaign_start"]) &
            (weekly_all["week_start"] <= row["campaign_end"])
        )
        return int(weekly_all.loc[mask, "reach"].sum())

    raw["reach"] = raw.apply(_campaign_reach, axis=1)
    return raw
