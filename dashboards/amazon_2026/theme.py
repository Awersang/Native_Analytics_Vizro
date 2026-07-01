"""Design tokens, color palettes, and pure color helpers shared across charts.

Split out of the old `charts_shared.py` god-file (see IMPROVEMENT_PLAN.md §5.4).
This module has no internal dependencies on `ui_components.py`/`timeline_charts.py`
so both of those can import from here freely.
"""
from __future__ import annotations

import hashlib

THEME_TEXT = "var(--na-text)"
THEME_TEXT_MUTED = "var(--na-text-muted)"
THEME_BORDER = "var(--na-border)"
THEME_GRID = "var(--na-grid)"
THEME_SURFACE = "var(--na-surface)"
THEME_SURFACE_ALT = "var(--na-surface-alt)"
THEME_ROW_EVEN = "var(--na-row-even)"
THEME_ROW_ODD = "var(--na-row-odd)"
WEEKLY_DTICK_MS = 7 * 24 * 60 * 60 * 1000


def theme_hoverlabel(size: int = 13, **extra) -> dict:
    return {
        "bgcolor": THEME_SURFACE,
        "bordercolor": THEME_BORDER,
        "font": {"color": THEME_TEXT, "size": size},
        **extra,
    }


SENTIMENT_COLORS = {
    "Positive": "#3f9d5c",
    "Neutral": "#4a8fc2",
    "Negative": "#d9534f",
}

# Canonical Trad / SoMe accent pair — reused for Overview source bars, the
# publisher overlap Venn, and (via --na-bar-trad-publications/--na-bar-some-posts)
# table data-bars.
ACCENT_TRAD = "#2f7dd1"
ACCENT_SOME = "#d98933"

# Canonical Trad Media_Type -> color assignments — used by the Overview "by
# Media Type" donut and anywhere else a Trad media type needs a color (e.g.
# the Topic Areas media/topic sankey).
MEDIA_TYPE_COLORS: dict[str, str] = {
    "Online": "#4C9F70",
    "Radio": "#E0833F",
    "Newswire": "#5B8DBE",
    "Print": "#A66DD4",
    "TV": "#D9534F",
    "Podcast": "#3FB6C9",
    "Blog": "#E6B450",
    "Newsletter": "#8FCB7E",
    "Video": "#E07AA0",
    "Unknown": "#7F7F7F",
}

# Canonical SoMe Platform -> color assignments (brand colors) — used by the
# Overview "by Platform" donut and anywhere else a platform needs a color
# (e.g. the Topic Areas media/topic sankey).
PLATFORM_COLORS: dict[str, str] = {
    "twitter": "#1DA1F2",
    "facebook": "#4267B2",
    "instagram": "#E1306C",
    "Unknown": "#7F7F7F",
}


def media_label_color(label: str, source: str | None = None) -> str:
    """Return the canonical color for a Trad media type or SoMe platform label.

    Looks up `MEDIA_TYPE_COLORS` / `PLATFORM_COLORS` by `label`. When `source`
    disambiguates ("Trad" vs "SoMe"), only that map is consulted; otherwise both
    maps are checked. Unrecognized labels fall back to a stable hash into
    `DONUT_COLORS`, so any new media type/platform still gets a consistent color.
    """
    if source == "Trad":
        color = MEDIA_TYPE_COLORS.get(label)
    elif source == "SoMe":
        color = PLATFORM_COLORS.get(label)
    else:
        color = MEDIA_TYPE_COLORS.get(label) or PLATFORM_COLORS.get(label)
    if color:
        return color
    digest = hashlib.md5(label.encode("utf-8")).hexdigest()
    return DONUT_COLORS[int(digest, 16) % len(DONUT_COLORS)]

# Cycling categorical palette — Publishers/Narratives mini-donuts and treemaps,
# and the canonical Topic Area color map (see `topic_area_color_map`).
DONUT_COLORS = [
    "#2f7dd1",
    "#22a6a1",
    "#d98933",
    "#8a6fd1",
    "#35a66b",
    "#c84e5a",
    "#b8a33e",
    "#5aa4b1",
]

# DONUT_COLORS plus two extra hues — used wherever a cycling palette needs a
# couple more distinct colors than the 8-color donut set provides.
NARRATIVE_LINE_COLORS = DONUT_COLORS + ["#e07040", "#7b5ea7"]


# Wide qualitative palette for Topic Areas — large and varied enough that the
# ~19 topic areas in `amazon_2026_trad`/`amazon_2026_some` each get their own
# distinct, dark-mode-friendly color (see `TOPIC_AREA_COLOR_OVERRIDES`).
TOPIC_AREA_PALETTE = [
    "#4C78A8",  # blue
    "#D1853C",  # orange (desaturated from #F58518 to match the Sentiment palette's ~55-65% saturation)
    "#54A24B",  # green
    "#DA6160",  # red (desaturated from #E45756)
    "#72B7B2",  # teal
    "#B279A2",  # mauve
    "#D3B745",  # yellow (desaturated from #EECA3B)
    "#E5919A",  # pink (desaturated/darkened from #FF9DA6)
    "#9D755D",  # brown
    "#5254A3",  # indigo
    "#8CA252",  # olive
    "#BD9E39",  # mustard
    "#AD494A",  # brick red
    "#6B6ECF",  # violet
    "#E7969C",  # salmon
    "#637939",  # dark olive
    "#3A7CA5",  # steel blue
    "#A05195",  # orchid
    "#7BBA2C",  # bright green (desaturated from #5BA300, used by Amazon Haul)
    "#D4A017",  # gold
    "#2F4B7C",  # deep blue
    "#C2785C",  # terracotta
]

# Canonical Topic Area -> color assignments, covering the live taxonomy from
# `amazon_2026_trad`/`amazon_2026_some`. These take priority in
# `topic_area_color_map` so every known topic area keeps a fixed, distinct,
# intentional color everywhere it appears.
TOPIC_AREA_COLOR_OVERRIDES: dict[str, str] = {
    "Policy": TOPIC_AREA_PALETTE[0],
    "Economic Impact": TOPIC_AREA_PALETTE[1],
    "Others (Corporate)": TOPIC_AREA_PALETTE[2],
    "Workplace & Operations": TOPIC_AREA_PALETTE[3],
    "Stores": TOPIC_AREA_PALETTE[4],
    "Customer Trust": TOPIC_AREA_PALETTE[5],
    "Innovation": TOPIC_AREA_PALETTE[6],
    "Community Impact": TOPIC_AREA_PALETTE[7],
    "Selling Partner Services": TOPIC_AREA_PALETTE[8],
    "Core Retail": TOPIC_AREA_PALETTE[9],
    "Sustainability": TOPIC_AREA_PALETTE[10],
    "Others (Stores)": TOPIC_AREA_PALETTE[11],
    "Books & Publishing": TOPIC_AREA_PALETTE[12],
    "High Velocity Events": TOPIC_AREA_PALETTE[13],
    "MCF": TOPIC_AREA_PALETTE[14],
    "Devices": TOPIC_AREA_PALETTE[15],
    "Payments": TOPIC_AREA_PALETTE[16],
    "Grocery": TOPIC_AREA_PALETTE[17],
    "Amazon Haul": TOPIC_AREA_PALETTE[18],
    "Unknown": "#7f7f7f",
}


def _topic_area_fallback_color(topic_area: str) -> str:
    """Deterministically pick a `TOPIC_AREA_PALETTE` entry for an uncatalogued topic area.

    Uses a stable hash (not the built-in `hash()`, which is randomized per
    process) so the color only depends on the topic area's name, never on
    which other topic areas happen to be present in the current view.
    """
    digest = hashlib.md5(topic_area.encode("utf-8")).hexdigest()
    return TOPIC_AREA_PALETTE[int(digest, 16) % len(TOPIC_AREA_PALETTE)]


def topic_area_color_map(topic_areas: list[str]) -> dict[str, str]:
    """Return a stable Topic Area -> color mapping shared across the whole dashboard.

    Each topic area's color depends only on its own name (via
    `TOPIC_AREA_COLOR_OVERRIDES` or a stable hash fallback) — never on the
    set or order of topic areas passed in — so a given topic area always
    renders in the same color regardless of metric, source filter, or page.
    """
    unique_topic_areas = {str(topic_area) for topic_area in topic_areas}
    return {
        topic_area: TOPIC_AREA_COLOR_OVERRIDES.get(topic_area) or _topic_area_fallback_color(topic_area)
        for topic_area in unique_topic_areas
    }


def hex_to_rgba(color: str | None, alpha: float) -> str:
    if not color:
        return f"rgba(31, 119, 180, {alpha})"
    value = str(color).strip().lstrip("#")
    if len(value) != 6:
        return color
    try:
        red = int(value[0:2], 16)
        green = int(value[2:4], 16)
        blue = int(value[4:6], 16)
    except ValueError:
        return color
    return f"rgba({red}, {green}, {blue}, {alpha})"
