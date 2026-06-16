"""Shared constants, utilities, and UI primitives used by both chart modules."""
from __future__ import annotations

import hashlib
import math
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.interpolate import PchipInterpolator
from plotly.subplots import make_subplots
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.dash_table.Format import Format, Scheme
from vizro.managers import data_manager

from dashboards.amazon_2026.data_common import SENTIMENT_ORDER

THEME_TEXT = "var(--amazon-publishers-text)"
THEME_TEXT_MUTED = "var(--amazon-publishers-text-muted)"
THEME_BORDER = "var(--amazon-publishers-border)"
THEME_GRID = "var(--amazon-publishers-grid)"
THEME_SURFACE = "var(--amazon-publishers-surface)"
THEME_SURFACE_ALT = "var(--amazon-publishers-surface-alt)"
THEME_ROW_EVEN = "var(--amazon-publishers-row-even)"
THEME_ROW_ODD = "var(--amazon-publishers-row-odd)"


def load_and_filter(key: str, filter_column: str, value: str) -> pd.DataFrame:
    """Load a registered dataset and filter to rows matching `value`, tolerating missing data."""
    try:
        df = data_manager[key].load()
    except Exception:
        return pd.DataFrame()
    if not df.empty and filter_column in df.columns:
        return df[df[filter_column] == value]
    return pd.DataFrame()


NARRATIVE_TRAD_COLUMNS = [
    "trad_publications",
    "trad_reach",
    "trad_positive_share_of_reach",
    "trad_negative_share_of_reach",
]
NARRATIVE_SOME_COLUMNS = [
    "some_posts",
    "some_reach",
    "some_engagement",
    "some_average_engagement",
    "some_positive_share_of_reach",
    "some_negative_share_of_reach",
]
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

TOOLTIP_CSS = [
    {"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"},
    {
        "selector": ".dash-header",
        "rule": "white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;",
    },
    {"selector": ".dash-tooltip", "rule": "z-index: 5000 !important; overflow: visible !important;"},
    {
        "selector": ".dash-table-tooltip",
        "rule": (
            "z-index: 5001 !important; background: var(--bs-body-bg, #111827) !important; "
            "color: var(--bs-body-color, #f8fafc) !important; "
            "border: 1px solid var(--bs-border-color, rgba(255,255,255,0.18)) !important; "
            "box-shadow: 0 14px 32px rgba(0,0,0,0.35) !important; white-space: normal !important;"
        ),
    },
]

NARRATIVE_BAR_COLORS = {
    "trad_publications": "var(--amazon-publishers-bar-trad-publications)",
    "trad_reach": "var(--amazon-publishers-bar-trad-reach)",
    "trad_positive_share_of_reach": "var(--amazon-publishers-bar-positive)",
    "trad_negative_share_of_reach": "var(--amazon-publishers-bar-negative)",
    "some_posts": "var(--amazon-publishers-bar-some-posts)",
    "some_reach": "var(--amazon-publishers-bar-some-reach)",
    "some_engagement": "var(--amazon-publishers-bar-some-engagement)",
    "some_average_engagement": "var(--amazon-publishers-bar-some-average)",
    "some_positive_share_of_reach": "var(--amazon-publishers-bar-positive)",
    "some_negative_share_of_reach": "var(--amazon-publishers-bar-negative)",
}


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _num(record: dict[str, Any], key: str) -> float:
    return _coerce_float(record.get(key, 0))


def _hex_to_rgba(color: str | None, alpha: float) -> str:
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


def _json_safe(record: dict[str, Any]) -> dict[str, Any]:
    clean = {}
    for key, value in record.items():
        if isinstance(value, (list, tuple, dict)):
            clean[key] = value
        elif pd.isna(value):
            clean[key] = ""
        elif isinstance(value, pd.Timestamp):
            clean[key] = value.isoformat()
        else:
            clean[key] = value
    return clean


def _kpi_card(
    label: str,
    value: str,
    caption: str | None = None,
    compact: bool = False,
) -> html.Div:
    children = [
        html.Div(label, className="amazon-publishers-kpi-label"),
        html.Div(value, className="amazon-publishers-kpi-value"),
    ]
    if caption:
        children.append(html.Div(caption, className="amazon-publishers-kpi-caption"))
    class_name = "amazon-publishers-kpi amazon-publishers-kpi-compact" if compact else "amazon-publishers-kpi"
    return html.Div(className=class_name, children=children)


def _as_list(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _filter_trad_some(source_filter: list[str] | str | None) -> list[str]:
    return [v for v in _as_list(source_filter) if v in {"Trad", "SoMe"}]


def _normalize_sources(
    source_filter: list[str] | str | None,
    available_sources: list[str],
) -> list[str]:
    selected = [s for s in _filter_trad_some(source_filter) if s in available_sources]
    if not available_sources:
        return []
    return selected or available_sources.copy()


def _normalized_narrative_sources(
    source_filter: list[str] | str | None,
    available_sources: list[str],
) -> list[str]:
    selected_sources = [s for s in _filter_trad_some(source_filter) if s in available_sources]
    if len(available_sources) <= 1:
        return available_sources.copy()
    return selected_sources or [available_sources[0]]


def _narratives_table_columns(source_filter: list[str] | str | None) -> list[dict[str, Any]]:
    selected_sources = _filter_trad_some(source_filter)
    columns: list[dict[str, Any]] = [{"name": ["", "Narrative"], "id": "narrative_label"}]
    if "Trad" in selected_sources:
        columns.extend(
            [
                {
                    "name": ["Trad", "Publications"],
                    "id": "trad_publications",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["Trad", "Reach"],
                    "id": "trad_reach",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["Trad", "Positive sentiment share of reach"],
                    "id": "trad_positive_share_of_reach",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["Trad", "Negative sentiment share of reach"],
                    "id": "trad_negative_share_of_reach",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
            ]
        )
    if "SoMe" in selected_sources:
        columns.extend(
            [
                {
                    "name": ["SoMe", "Posts"],
                    "id": "some_posts",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Reach"],
                    "id": "some_reach",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Engagement"],
                    "id": "some_engagement",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Avg engagement/post"],
                    "id": "some_average_engagement",
                    "type": "numeric",
                    "format": Format(group=True, precision=1, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Positive sentiment share of reach"],
                    "id": "some_positive_share_of_reach",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["SoMe", "Negative sentiment share of reach"],
                    "id": "some_negative_share_of_reach",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
            ]
        )
    return columns


def _narrative_has_source_divider(columns: list[dict[str, Any]]) -> bool:
    visible_ids = {column["id"] for column in columns}
    return any(column_id in visible_ids for column_id in NARRATIVE_SOME_COLUMNS) and any(
        column_id in visible_ids for column_id in NARRATIVE_TRAD_COLUMNS
    )


def _first_narrative_some_column(columns: list[dict[str, Any]]) -> str | None:
    visible_ids = {column["id"] for column in columns}
    for column_id in NARRATIVE_SOME_COLUMNS:
        if column_id in visible_ids:
            return column_id
    return None


def _narrative_header_divider_styles(source_filter: list[str] | str | None) -> list[dict[str, Any]]:
    columns = _narratives_table_columns(source_filter)
    styles = [
        {
            "if": {"column_id": "narrative_label"},
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
        }
    ]
    first_some_column = _first_narrative_some_column(columns)
    if _narrative_has_source_divider(columns) and first_some_column:
        styles.append(
            {
                "if": {"column_id": first_some_column},
                "borderLeft": "none",
                "boxShadow": f"inset 1px 0 0 {THEME_BORDER}",
            }
        )
    return styles


def _narrative_data_bar_styles(table_data: list[dict[str, Any]], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    visible_ids = {column["id"] for column in columns}
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {
            "if": {"column_id": "narrative_label"},
            "color": "var(--amazon-publishers-link)",
            "cursor": "pointer",
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
            "fontWeight": "700",
            "textAlign": "left",
        },
        {
            "if": {"state": "active"},
            "backgroundColor": "var(--bs-primary-bg-subtle)",
            "border": "1px solid var(--bs-primary-bg-subtle)",
        },
        {
            "if": {"state": "selected"},
            "backgroundColor": "var(--bs-primary-bg-subtle)",
            "border": "1px solid var(--bs-primary-bg-subtle)",
        },
    ]
    first_some_column = _first_narrative_some_column(columns)
    if _narrative_has_source_divider(columns) and first_some_column:
        styles.append(
            {
                "if": {"column_id": first_some_column},
                "borderLeft": "none",
                "boxShadow": f"inset 1px 0 0 {THEME_BORDER}",
            }
        )
    for column_id in [col for col in [*NARRATIVE_TRAD_COLUMNS, *NARRATIVE_SOME_COLUMNS] if col in visible_ids]:
        max_value = max((_num(row, column_id) for row in table_data), default=0)
        if max_value <= 0:
            continue
        for row in table_data:
            pct = max(0, min(100, (_num(row, column_id) / max_value) * 100))
            row_bg = THEME_ROW_ODD if int(row["row_id"]) % 2 else THEME_ROW_EVEN
            styles.append(
                {
                    "if": {"filter_query": f"{{row_id}} = {row['row_id']}", "column_id": column_id},
                    "background": (
                        f"linear-gradient(90deg, {NARRATIVE_BAR_COLORS[column_id]} 0%, "
                        f"{NARRATIVE_BAR_COLORS[column_id]} {pct:.2f}%, {row_bg} {pct:.2f}%, {row_bg} 100%)"
                    ),
                }
            )
    for row in table_data:
        styles.append(
            {
                "if": {"filter_query": f"{{row_id}} = {row['row_id']}", "column_id": "narrative_label"},
                "position": "relative",
                "zIndex": 4,
                "boxShadow": f"inset 0 -1px 0 {THEME_BORDER}",
            }
        )
    return styles


# ---------------------------------------------------------------------------
# Sentiment timeline (shared between Publishers and Narratives details)
# ---------------------------------------------------------------------------

TRAD_SOME_OPTIONS = [
    {"label": "Trad", "value": "Trad"},
    {"label": "SoMe", "value": "SoMe"},
]


def trad_some_controls(
    control_id: str,
    available_sources: list[str],
    selected_sources: list[str],
    *,
    disable_unavailable: bool = False,
    hide_when_single: bool = True,
) -> html.Div:
    """Shared Trad/SoMe source-toggle Checklist used by `na_panel(controls=...)`.

    With `disable_unavailable=True`, all options are shown but unavailable
    sources are disabled (timeline panel); otherwise only available sources
    are offered and, with `hide_when_single=True` (default), the whole control
    is hidden when there's nothing to toggle.
    """
    if disable_unavailable:
        options = [
            {**option, "disabled": option["value"] not in available_sources}
            for option in TRAD_SOME_OPTIONS
        ]
    else:
        options = TRAD_SOME_OPTIONS
    return html.Div(
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if hide_when_single and len(available_sources) <= 1 else None,
        children=[
            dcc.Checklist(
                id=control_id,
                options=options,
                value=selected_sources,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )


def _detail_metric_values(basic_metric: str) -> tuple[str, str]:
    if basic_metric == "reach":
        return "reach", "engagement"
    return "publications", "posts"


def _timeline_records_from_frame(data_frame: pd.DataFrame, id_field: str = "publisher_uid") -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in [id_field, "display_name", "week_start", "sentiment", "base_metric"]:
        if column not in df.columns:
            df[column] = ""
    if "metric_value" not in df.columns:
        df["metric_value"] = 0
    df["metric_value"] = pd.to_numeric(df["metric_value"], errors="coerce").fillna(0)
    parsed_dates = pd.to_datetime(df["week_start"], errors="coerce")
    df["week_start"] = parsed_dates.dt.date.astype(str)
    df.loc[parsed_dates.isna(), "week_start"] = ""
    return [_json_safe(record) for record in df.to_dict("records")]


def _timeline_metric_frame(
    records: list[dict[str, Any]],
    entity_id: str,
    metric: str,
    id_field: str = "publisher_uid",
) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    df = df[
        (df[id_field].astype(str) == entity_id)
        & (df["base_metric"].astype(str) == metric)
    ].copy()
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df = df.dropna(subset=["week_start"]).sort_values(["week_start", "sentiment"])
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    return df


def _timeline_series_frame(
    records: list[dict[str, Any]],
    entity_id: str,
    metric: str,
    week_index: pd.DatetimeIndex | None = None,
    id_field: str = "publisher_uid",
) -> pd.DataFrame:
    df = _timeline_metric_frame(records, entity_id, metric, id_field)
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    if week_index is None or week_index.empty:
        week_index = pd.date_range(df["week_start"].min(), df["week_start"].max(), freq="W-MON")
    rows: list[pd.DataFrame] = []
    for sentiment in SENTIMENT_ORDER:
        sub = df[df["sentiment"] == sentiment]
        rows.append(
            sub.groupby("week_start", as_index=True)["metric_value"]
            .sum()
            .reindex(week_index, fill_value=0)
            .rename_axis("week_start")
            .reset_index()
            .assign(sentiment=sentiment)
        )
    if not rows:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    return pd.concat(rows, ignore_index=True)


def _timeline_date_bounds(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> tuple[pd.Timestamp, pd.Timestamp] | None:
    payload = timeline_data or {}
    entity_id = str(payload.get(id_field, ""))
    trad_metric = str(payload.get("trad_metric", "publications"))
    some_metric = str(payload.get("some_metric", "posts"))
    frames = [
        _timeline_metric_frame(payload.get("trad_timeline", []), entity_id, trad_metric, id_field),
        _timeline_metric_frame(payload.get("some_timeline", []), entity_id, some_metric, id_field),
    ]
    for label in payload.get("narrative_labels") or []:
        narrative_label = str(label)
        frames.append(_timeline_metric_frame(payload.get("narrative_trad_timeline", []), narrative_label, trad_metric, "narrative_label"))
        frames.append(_timeline_metric_frame(payload.get("narrative_some_timeline", []), narrative_label, some_metric, "narrative_label"))
    dates = [frame["week_start"] for frame in frames if not frame.empty and "week_start" in frame]
    if not dates:
        return None
    min_date = min(series.min() for series in dates)
    max_date = max(series.max() for series in dates)
    if pd.isna(min_date) or pd.isna(max_date):
        return None
    return min_date, max_date


def _timeline_week_index(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> pd.DatetimeIndex:
    bounds = _timeline_date_bounds(timeline_data, id_field)
    if bounds is None:
        return pd.DatetimeIndex([])
    return pd.date_range(bounds[0], bounds[1], freq="W-MON")


def _timeline_xaxis_range(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> list[pd.Timestamp] | None:
    bounds = _timeline_date_bounds(timeline_data, id_field)
    if bounds is None:
        return None
    return [bounds[0], bounds[1]]


def _timeline_available_sources(timeline_data: dict[str, Any] | None) -> list[str]:
    payload = timeline_data or {}
    available_sources: list[str] = []
    if payload.get("has_trad"):
        available_sources.append("Trad")
    if payload.get("has_some"):
        available_sources.append("SoMe")
    return available_sources


def _timeline_axis_title(source_label: str | None, trad_metric: str, some_metric: str) -> str:
    if trad_metric == "publications" and some_metric == "posts":
        return "Publications and Posts"
    if source_label == "Trad":
        return {"publications": "Trad Publications", "reach": "Trad Reach"}.get(trad_metric, trad_metric.title())
    if source_label == "SoMe":
        return {"posts": "SoMe Posts", "engagement": "SoMe Engagement"}.get(some_metric, some_metric.title())
    return "Metric"


def _timeline_uses_shared_count_scale(trad_metric: str, some_metric: str) -> bool:
    return trad_metric == "publications" and some_metric == "posts"


def _timeline_chart_title(trad_metric: str, some_metric: str) -> str:
    if trad_metric == "publications" and some_metric == "posts":
        return "Publications Timeline by Sentiment"
    if trad_metric == "reach" and some_metric == "engagement":
        return "Reach and Engagement by Sentiment"
    if trad_metric == "reach":
        return "Reach Timeline by Sentiment"
    if some_metric == "engagement":
        return "Engagement Timeline by Sentiment"
    return "Timeline by Sentiment"


def _timeline_figure(
    timeline_data: dict[str, Any],
    source_filter: list[str] | str | None,
    id_field: str = "publisher_uid",
) -> go.Figure:
    available_sources = _timeline_available_sources(timeline_data)
    selected_sources = _normalize_sources(source_filter, available_sources)
    fig = go.Figure()
    combined_mode = len(selected_sources) > 1
    shared_count_scale = _timeline_uses_shared_count_scale(
        str(timeline_data.get("trad_metric", "publications")),
        str(timeline_data.get("some_metric", "posts")),
    )
    source_configs = {
        "Trad": {
            "records": timeline_data.get("trad_timeline", []),
            "metric": str(timeline_data.get("trad_metric", "publications")),
            "metric_labels": {"publications": "Publications", "reach": "Reach"},
            "axis": "y",
            "dash": "solid",
            "marker": "circle",
        },
        "SoMe": {
            "records": timeline_data.get("some_timeline", []),
            "metric": str(timeline_data.get("some_metric", "posts")),
            "metric_labels": {"posts": "Posts", "engagement": "Engagement"},
            "axis": "y2" if combined_mode and not shared_count_scale else "y",
            "dash": "dot",
            "marker": "diamond",
        },
    }
    entity_id = str(timeline_data.get(id_field, ""))
    shared_week_index = _timeline_week_index(timeline_data, id_field)

    for source_label in selected_sources:
        config = source_configs.get(source_label)
        if not config:
            continue
        metric = config["metric"]
        metric_label = config["metric_labels"].get(metric, metric.title())
        source_df = _timeline_series_frame(
            config["records"],
            entity_id,
            metric,
            shared_week_index,
            id_field,
        )
        if source_df.empty:
            continue
        fill_alpha = 0.08 if combined_mode else 0.14
        for sentiment in SENTIMENT_ORDER:
            sub = source_df[source_df["sentiment"] == sentiment]
            if sub.empty:
                continue
            trace_name = f"{source_label} {sentiment}" if combined_mode else sentiment
            fig.add_trace(
                go.Scatter(
                    x=sub["week_start"],
                    y=sub["metric_value"],
                    name=trace_name,
                    legendgroup=source_label,
                    mode="lines+markers",
                    line=dict(
                        width=2.5,
                        color=SENTIMENT_COLORS.get(sentiment),
                        shape="spline",
                        smoothing=0.45,
                        dash=config["dash"],
                    ),
                    marker=dict(size=6, color=SENTIMENT_COLORS.get(sentiment), symbol=config["marker"]),
                    fill="tozeroy",
                    fillcolor=_hex_to_rgba(SENTIMENT_COLORS.get(sentiment), fill_alpha),
                    yaxis=config["axis"],
                    hovertemplate=(
                        f"<b>{trace_name}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        f"{metric_label}: %{{y:,.0f}}<extra></extra>"
                    ),
                )
            )
    if not fig.data:
        fig.add_annotation(
            text="No weekly data",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )
    primary_label = _timeline_axis_title(
        selected_sources[0] if selected_sources else None,
        str(timeline_data.get("trad_metric", "publications")),
        str(timeline_data.get("some_metric", "posts")),
    )
    fig.update_layout(
        title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=26, r=26, t=18, b=46),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", title=None),
        xaxis=dict(
            title=None,
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            range=_timeline_xaxis_range(timeline_data, id_field),
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        yaxis=dict(title=primary_label, tickformat=",", rangemode="tozero", showgrid=True, gridcolor=THEME_GRID),
        hoverlabel=dict(bgcolor=THEME_SURFACE, bordercolor=THEME_BORDER, font=dict(color=THEME_TEXT, size=13)),
    )
    if combined_mode and not shared_count_scale:
        fig.update_layout(
            yaxis2=dict(
                title=_timeline_axis_title(
                    "SoMe",
                    str(timeline_data.get("trad_metric", "publications")),
                    str(timeline_data.get("some_metric", "posts")),
                ),
                tickformat=",",
                rangemode="tozero",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
            )
        )
    return fig


def _nice_axis_step(max_value: float, target_ticks: int = 4) -> float:
    """Return a "nice" tick step (1/2/2.5/5 x10^n) covering `max_value` in ~`target_ticks` steps."""
    if max_value <= 0:
        return 1.0
    raw_step = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    for multiple in (1, 2, 2.5, 5, 10):
        step = multiple * magnitude
        if step >= raw_step:
            return step
    return 10 * magnitude


def _media_split_weekly_pivot(data_frame: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    if data_frame is None or data_frame.empty:
        return pd.DataFrame()
    df = data_frame.copy()
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    df = df.dropna(subset=["week_start"])
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(index="week_start", columns=group_col, values=value_col, aggfunc="sum", fill_value=0)
    return pivot.sort_index()


def top_reach_flags(top_publications_df: pd.DataFrame, source: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Return the top `top_n` publications/posts for `source` ("Trad"/"SoMe") by reach.

    Each flag dict has `label` (Publication for Trad, Author for SoMe), `value`
    (the reach), `date` (ISO date string), and `kind="reach"` — used to render
    flag annotations on `media_split_timeline_figure`.
    """
    if top_publications_df is None or top_publications_df.empty or "Source" not in top_publications_df.columns:
        return []
    subset = top_publications_df[top_publications_df["Source"] == source].copy()
    if subset.empty:
        return []
    subset["Reach"] = pd.to_numeric(subset["Reach"], errors="coerce").fillna(0)
    subset = subset.sort_values("Reach", ascending=False).head(top_n)
    label_col = "Publication" if source == "Trad" else "Author"
    flags = []
    for _, row in subset.iterrows():
        date = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(date):
            continue
        label = str(row.get(label_col) or "Unknown").strip() or "Unknown"
        flags.append({"label": label, "value": float(row["Reach"]), "date": date.strftime("%Y-%m-%d"), "kind": "reach"})
    return flags


def _top_volume_week_flag(pivot: pd.DataFrame, stacked: bool, unit_label: str) -> dict[str, Any] | None:
    """Return a flag dict marking the week with the highest total `unit_label`
    (the same `totals` series used to anchor the reach flags), or `None` if
    there's no positive data."""
    if pivot.empty:
        return None
    totals = pivot.sum(axis=1) if stacked else pivot.max(axis=1)
    if totals.empty:
        return None
    week_start = totals.idxmax()
    value = float(totals.loc[week_start])
    if value <= 0:
        return None
    return {
        "label": f"Top week by {unit_label}",
        "value": value,
        "date": week_start.strftime("%Y-%m-%d"),
        "kind": "volume",
    }


def _add_reach_flag_annotations(
    fig: go.Figure,
    flags: list[dict[str, Any]] | None,
    pivot: pd.DataFrame,
    side: str,
    px_per_unit: float,
    stacked: bool = False,
) -> float:
    """Add flag annotations for top datapoints — 🚩 reach flags (publisher/author
    + reach) and ⭐ "top week by volume" flags (in `MEDIA_SPLIT_VOLUME_COLOR`).

    Returns the largest pixel distance (from the zero line) spanned by any flag's
    box, so callers can extend the axis range to keep every box inside the plot.
    """
    if not flags or pivot.empty:
        return 0.0
    week_index = pivot.index
    totals = pivot.sum(axis=1) if stacked else pivot.max(axis=1)
    sign = 1 if side == "trad" else -1
    week_slot: dict[pd.Timestamp, int] = {}
    placements: list[tuple[int, pd.Timestamp, float, dict[str, Any]]] = []
    for flag in flags:
        date = pd.to_datetime(flag.get("date"), errors="coerce")
        if pd.isna(date):
            continue
        week_start = (date - pd.Timedelta(days=date.weekday())).normalize()
        if week_start not in week_index:
            idx = week_index.get_indexer([week_start], method="nearest")[0]
            week_start = week_index[idx]
        base = float(totals.get(week_start, 0))
        slot = week_slot.get(week_start, 0)
        week_slot[week_start] = slot + 1
        placements.append((slot, week_start, base, flag))

    # Draw the farther-offset (higher-slot) flags first so their longer arrows
    # sit behind the closer flags' labels/arrows instead of covering them.
    placements.sort(key=lambda p: p[0], reverse=True)
    max_required_px = 0.0
    for slot, week_start, base, flag in placements:
        offset = 10 + slot * MEDIA_SPLIT_FLAG_SLOT_PX
        if flag.get("kind") == "volume":
            text = f"⭐ {flag['label']}: {flag['value']:,.0f}"
            accent = MEDIA_SPLIT_VOLUME_COLOR
            box_height = MEDIA_SPLIT_FLAG_BOX_HEIGHT_VOLUME
        else:
            text = f"\U0001F6A9 {flag['label']}<br>Reach: {flag['value']:,.0f}"
            accent = THEME_BORDER
            box_height = MEDIA_SPLIT_FLAG_BOX_HEIGHT_REACH
        fig.add_annotation(
            x=week_start,
            y=sign * base,
            text=text,
            showarrow=True,
            arrowhead=2,
            arrowsize=0.8,
            arrowcolor="#444",
            ax=0,
            ay=-offset if side == "trad" else offset,
            align="left",
            font=dict(size=10, color=THEME_TEXT),
            bgcolor=THEME_SURFACE,
            bordercolor=accent,
            borderwidth=1,
            borderpad=4,
            yanchor="bottom" if side == "trad" else "top",
        )
        required_px = abs(base) * px_per_unit + offset + box_height
        max_required_px = max(max_required_px, required_px)
    return max_required_px


def _smooth_nonnegative_curve(
    index: pd.DatetimeIndex, values: pd.Series, points_per_segment: int = 8
) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Upsample a weekly series with shape-preserving (PCHIP) interpolation so
    the rendered line looks smooth without the overshoot a cardinal/spline
    curve produces — e.g. dipping below zero between a zero week and a sharply
    rising one. PCHIP never exceeds the local min/max of neighbouring points,
    so a series that never goes negative stays non-negative once interpolated.
    """
    if len(values) < 3:
        return index, values.to_numpy()
    x_numeric = index.values.astype("datetime64[ns]").astype("int64")
    interpolator = PchipInterpolator(x_numeric, values.to_numpy())
    x_dense = np.linspace(x_numeric[0], x_numeric[-1], (len(x_numeric) - 1) * points_per_segment + 1)
    return pd.to_datetime(x_dense, unit="ns"), interpolator(x_dense)


MEDIA_SPLIT_AXIS_PIXELS_PER_TICK = 68
MEDIA_SPLIT_MARGIN_TOP_BASE = 20
MEDIA_SPLIT_MARGIN_BOTTOM_BASE = 40
MEDIA_SPLIT_MARGIN_LEFT = 70
MEDIA_SPLIT_MARGIN_RIGHT = 150
MEDIA_SPLIT_FLAG_SLOT_PX = 50
MEDIA_SPLIT_FLAG_BOX_HEIGHT_REACH = 38
MEDIA_SPLIT_FLAG_BOX_HEIGHT_VOLUME = 24
MEDIA_SPLIT_MIN_HEIGHT_PX = 480
MEDIA_SPLIT_VOLUME_COLOR = "#D3B745"


def media_split_timeline_figure(
    trad_df: pd.DataFrame,
    some_df: pd.DataFrame,
    stacked: bool = False,
    trad_flags: list[dict[str, Any]] | None = None,
    some_flags: list[dict[str, Any]] | None = None,
) -> tuple[go.Figure, int]:
    """Mirrored weekly timeline: Trad media types stacked/lined above zero, SoMe
    platforms below zero (plotted as negative but labelled/hover'd as positive).

    Returns ``(figure, height_px)`` — the height is sized to the data actually
    rendered (no leftover empty space at top/bottom) while keeping the same
    pixels-per-unit step on both halves of the y-axis, so equal Trad/SoMe
    values remain directly comparable even though their axis limits differ.
    """
    fig = go.Figure()

    trad_pivot = _media_split_weekly_pivot(trad_df, "media_type", "publications")
    some_pivot = _media_split_weekly_pivot(some_df, "platform", "posts")

    trad_extent = 0.0
    some_extent = 0.0

    if trad_pivot.empty and some_pivot.empty:
        fig.add_annotation(
            text="No weekly data",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )
    else:
        all_weeks = pd.DatetimeIndex(sorted(set(trad_pivot.index) | set(some_pivot.index)))
        if not trad_pivot.empty:
            trad_pivot = trad_pivot.reindex(all_weeks, fill_value=0)
        if not some_pivot.empty:
            some_pivot = some_pivot.reindex(all_weeks, fill_value=0)

        # Axis extent reflects what's actually drawn: the stacked total when
        # `stacked`, or the tallest individual line otherwise.
        if stacked:
            trad_extent = float(trad_pivot.sum(axis=1).max()) if not trad_pivot.empty else 0.0
            some_extent = float(some_pivot.sum(axis=1).max()) if not some_pivot.empty else 0.0
        else:
            trad_extent = float(trad_pivot.max().max()) if not trad_pivot.empty else 0.0
            some_extent = float(some_pivot.max().max()) if not some_pivot.empty else 0.0

        fill_mode = "tonexty" if stacked else "tozeroy"
        fill_alpha = 0.28 if stacked else 0.12
        stack_kwargs = {"stackgroup": "trad"} if stacked else {}

        for media_type in trad_pivot.columns:
            color = media_label_color(media_type, "Trad")
            smooth_x, smooth_y = _smooth_nonnegative_curve(trad_pivot.index, trad_pivot[media_type])
            fig.add_trace(
                go.Scatter(
                    x=smooth_x,
                    y=smooth_y,
                    name=f"Trad – {media_type}",
                    legendgroup="Trad",
                    mode="lines",
                    line=dict(width=2, color=color, shape="linear"),
                    fill=fill_mode,
                    fillcolor=_hex_to_rgba(color, fill_alpha),
                    hovertemplate=(
                        f"<b>Trad – {media_type}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        "Publications: %{y:,.0f}<extra></extra>"
                    ),
                    **stack_kwargs,
                )
            )

        stack_kwargs = {"stackgroup": "some"} if stacked else {}
        for platform in some_pivot.columns:
            color = media_label_color(platform, "SoMe")
            smooth_x, smooth_y = _smooth_nonnegative_curve(some_pivot.index, -some_pivot[platform])
            fig.add_trace(
                go.Scatter(
                    x=smooth_x,
                    y=smooth_y,
                    name=f"SoMe – {platform}",
                    legendgroup="SoMe",
                    mode="lines",
                    line=dict(width=2, color=color, dash="dot", shape="linear"),
                    fill=fill_mode,
                    fillcolor=_hex_to_rgba(color, fill_alpha),
                    customdata=-smooth_y,
                    hovertemplate=(
                        f"<b>SoMe – {platform}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        "Posts: %{customdata:,.0f}<extra></extra>"
                    ),
                    **stack_kwargs,
                )
            )

    # Both halves use the same step (pixels-per-unit), so equal Trad/SoMe
    # values sit the same distance from zero — but each half only extends as
    # far as its own data needs, instead of forcing a shared axis limit.
    step = _nice_axis_step(max(trad_extent, some_extent))
    trad_tick_count = max(1, math.ceil(trad_extent / step)) if trad_extent > 0 else 1
    some_tick_count = max(1, math.ceil(some_extent / step)) if some_extent > 0 else 1
    tickvals = (
        [-i * step for i in range(some_tick_count, 0, -1)]
        + [0]
        + [i * step for i in range(1, trad_tick_count + 1)]
    )
    ticktext = [f"{abs(v):,.0f}" for v in tickvals]

    px_per_unit = MEDIA_SPLIT_AXIS_PIXELS_PER_TICK / step

    trad_volume_flag = _top_volume_week_flag(trad_pivot, stacked, "pub.")
    some_volume_flag = _top_volume_week_flag(some_pivot, stacked, "posts")
    all_trad_flags = [*(trad_flags or []), *([trad_volume_flag] if trad_volume_flag else [])]
    all_some_flags = [*(some_flags or []), *([some_volume_flag] if some_volume_flag else [])]

    trad_required_px = _add_reach_flag_annotations(fig, all_trad_flags, trad_pivot, "trad", px_per_unit, stacked=stacked)
    some_required_px = _add_reach_flag_annotations(fig, all_some_flags, some_pivot, "some", px_per_unit, stacked=stacked)

    if trad_flags or some_flags:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=8, color=THEME_TEXT_MUTED, symbol="triangle-up"),
                name="Top 5 pub. by reach",
                showlegend=True,
                hoverinfo="skip",
            )
        )
    if trad_volume_flag or some_volume_flag:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=8, color=MEDIA_SPLIT_VOLUME_COLOR, symbol="star"),
                name="Top week by pub.",
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Flag stacks extend the axis range beyond the data extent so their boxes
    # land inside the plot area instead of bleeding into the margins — that's
    # what keeps margins (and thus `height_px`) tight while still leaving room
    # for every flag.
    trad_tick_px = trad_tick_count * step * 1.05 * px_per_unit
    some_tick_px = some_tick_count * step * 1.05 * px_per_unit
    top_extra_px = max(0.0, trad_required_px - trad_tick_px)
    bottom_extra_px = max(0.0, some_required_px - some_tick_px)
    trad_edge = trad_tick_count * step * 1.05 + top_extra_px / px_per_unit
    some_edge = some_tick_count * step * 1.05 + bottom_extra_px / px_per_unit

    margin_t = MEDIA_SPLIT_MARGIN_TOP_BASE
    margin_b = MEDIA_SPLIT_MARGIN_BOTTOM_BASE
    axis_height = (trad_tick_count + some_tick_count) * MEDIA_SPLIT_AXIS_PIXELS_PER_TICK + top_extra_px + bottom_extra_px
    height_px = max(MEDIA_SPLIT_MIN_HEIGHT_PX, int(axis_height + margin_t + margin_b))

    # Section labels replace the old single (misleading) axis title — one
    # centred in the Trad half (above zero) and one in the SoMe half (below).
    fig.add_annotation(
        text="Trad publications",
        xref="paper",
        x=0,
        xshift=-58,
        yref="y",
        y=trad_edge / 2,
        showarrow=False,
        textangle=-90,
        font=dict(size=11, color=THEME_TEXT_MUTED),
        xanchor="center",
        yanchor="middle",
    )
    fig.add_annotation(
        text="SoMe posts",
        xref="paper",
        x=0,
        xshift=-58,
        yref="y",
        y=-some_edge / 2,
        showarrow=False,
        textangle=-90,
        font=dict(size=11, color=THEME_TEXT_MUTED),
        xanchor="center",
        yanchor="middle",
    )

    # Explicit zero line drawn above the data traces — with many overlapping
    # filled lines converging on zero, the axis's own zeroline gets lost
    # underneath them, so draw a same-thickness gray line on top instead.
    fig.add_shape(
        type="line",
        xref="paper",
        x0=0,
        x1=1,
        yref="y",
        y0=0,
        y1=0,
        line=dict(color=THEME_TEXT_MUTED, width=2),
        layer="above",
    )

    fig.update_layout(
        title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=MEDIA_SPLIT_MARGIN_LEFT, r=MEDIA_SPLIT_MARGIN_RIGHT, t=margin_t, b=margin_b),
        hovermode="x unified",
        legend=dict(orientation="v", y=1, x=1.02, xanchor="left", yanchor="top", title=None, font=dict(size=11)),
        xaxis=dict(
            title=None,
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        yaxis=dict(
            title=None,
            tickvals=tickvals,
            ticktext=ticktext,
            range=[-some_edge, trad_edge],
            showgrid=True,
            gridcolor=THEME_GRID,
            zeroline=False,
        ),
        hoverlabel=dict(bgcolor=THEME_SURFACE, bordercolor=THEME_BORDER, font=dict(color=THEME_TEXT, size=13)),
    )
    return fig, height_px


TIMELINE_BASE_HEIGHT_PX = 380
_NARRATIVE_ROW_HEIGHT_PX = 130


def _timeline_with_narratives_figure(
    timeline_data: dict[str, Any],
    source_filter: list[str] | str | None,
    id_field: str = "publisher_uid",
) -> tuple[go.Figure, int]:
    """Returns (figure, height_px). Sentiment timeline on top plus one sub-chart per
    associated narrative below, all sharing the main chart's x-limits.

    Expects ``timeline_data`` to additionally carry ``narrative_labels`` and
    ``narrative_trad_timeline`` / ``narrative_some_timeline`` records keyed by
    ``narrative_label`` (same shape as the main timeline records).
    """
    labels = [str(label) for label in (timeline_data.get("narrative_labels") or [])]
    main_fig = _timeline_figure(timeline_data, source_filter, id_field)
    if not labels:
        return main_fig, TIMELINE_BASE_HEIGHT_PX

    available_sources = _timeline_available_sources(timeline_data)
    selected_sources = _normalize_sources(source_filter, available_sources)
    trad_metric = str(timeline_data.get("trad_metric", "publications"))
    some_metric = str(timeline_data.get("some_metric", "posts"))
    use_secondary = len(selected_sources) > 1 and not _timeline_uses_shared_count_scale(trad_metric, some_metric)

    n = len(labels)
    gap_before_first_subplot_px = 40
    gap_between_subplots_px = 15
    title_offset_px = 8
    row_heights_px = [TIMELINE_BASE_HEIGHT_PX] + [_NARRATIVE_ROW_HEIGHT_PX] * n
    gaps_px = [gap_before_first_subplot_px] + [gap_between_subplots_px] * (n - 1)
    total_plot_px = sum(row_heights_px) + sum(gaps_px)
    total_px = total_plot_px + 60
    titles = [""] + [(t[:60] + "…" if len(t) > 61 else t) for t in labels]
    fig = make_subplots(
        rows=n + 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=min(0.03, gap_between_subplots_px / total_plot_px),
        row_heights=[h / total_plot_px for h in row_heights_px],
        subplot_titles=titles,
        specs=[[{"secondary_y": True}]] * (n + 1),
    )

    row_domains: list[tuple[float, float]] = []
    cursor = 1.0
    for row_index, height_px in enumerate(row_heights_px):
        height_frac = height_px / total_plot_px
        top = cursor
        bottom = top - height_frac
        row_domains.append((bottom, top))
        if row_index < len(gaps_px):
            cursor = bottom - gaps_px[row_index] / total_plot_px
        else:
            cursor = bottom
    for row_index, domain in enumerate(row_domains):
        clamped = [max(0.0, min(1.0, value)) for value in domain]
        fig.update_yaxes(domain=clamped, row=row_index + 1, col=1, secondary_y=False)

    title_offset_frac = title_offset_px / total_plot_px
    for annotation, domain in zip(fig.layout.annotations, row_domains[1:]):
        annotation.update(y=domain[1] - title_offset_frac)

    for trace in main_fig.data:
        fig.add_trace(trace, row=1, col=1, secondary_y=getattr(trace, "yaxis", "y") == "y2")

    source_configs = {
        "Trad": {
            "records": timeline_data.get("narrative_trad_timeline", []),
            "metric": trad_metric,
            "metric_labels": {"publications": "Publications", "reach": "Reach"},
            "secondary": False,
            "dash": "solid",
            "marker": "circle",
        },
        "SoMe": {
            "records": timeline_data.get("narrative_some_timeline", []),
            "metric": some_metric,
            "metric_labels": {"posts": "Posts", "engagement": "Engagement"},
            "secondary": use_secondary,
            "dash": "dot",
            "marker": "diamond",
        },
    }
    shared_week_index = _timeline_week_index(timeline_data, id_field)
    combined_mode = len(selected_sources) > 1
    primary_max = 0.0
    secondary_max = 0.0

    for row_offset, label in enumerate(labels):
        row = row_offset + 2
        for source_label in selected_sources:
            config = source_configs.get(source_label)
            if not config:
                continue
            metric = config["metric"]
            metric_label = config["metric_labels"].get(metric, metric.title())
            source_df = _timeline_series_frame(
                config["records"], label, metric, shared_week_index, "narrative_label"
            )
            if source_df.empty:
                continue
            for sentiment in SENTIMENT_ORDER:
                sub = source_df[source_df["sentiment"] == sentiment]
                if sub.empty:
                    continue
                trace_name = f"{source_label} {sentiment}" if combined_mode else sentiment
                series_max = float(sub["metric_value"].max() or 0)
                if config["secondary"]:
                    secondary_max = max(secondary_max, series_max)
                else:
                    primary_max = max(primary_max, series_max)
                fig.add_trace(
                    go.Scatter(
                        x=sub["week_start"],
                        y=sub["metric_value"],
                        name=trace_name,
                        mode="lines+markers",
                        line=dict(
                            width=1.5,
                            color=SENTIMENT_COLORS.get(sentiment),
                            shape="spline",
                            smoothing=0.45,
                            dash=config["dash"],
                        ),
                        marker=dict(size=4, color=SENTIMENT_COLORS.get(sentiment), symbol=config["marker"]),
                        fill="tozeroy",
                        fillcolor=_hex_to_rgba(SENTIMENT_COLORS.get(sentiment), 0.08),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{trace_name}</b><br>"
                            "Week: %{x|%d %b %Y}<br>"
                            f"{metric_label}: %{{y:,.0f}}<extra></extra>"
                        ),
                    ),
                    row=row,
                    col=1,
                    secondary_y=config["secondary"],
                )

    main_layout = main_fig.layout
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=60, r=60 if use_secondary else 26, t=18, b=46),
        hovermode="x unified",
        legend=main_layout.legend,
        hoverlabel=main_layout.hoverlabel,
    )
    x_range = _timeline_xaxis_range(timeline_data, id_field)
    for row in range(1, n + 2):
        fig.update_xaxes(
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            range=x_range,
            showgrid=True,
            gridcolor=THEME_GRID,
            row=row,
            col=1,
        )
    fig.update_yaxes(
        title=main_layout.yaxis.title,
        tickformat=",",
        rangemode="tozero",
        showgrid=True,
        gridcolor=THEME_GRID,
        row=1,
        col=1,
        secondary_y=False,
    )
    if use_secondary and getattr(main_layout, "yaxis2", None) is not None:
        fig.update_yaxes(
            title=main_layout.yaxis2.title,
            tickformat=",",
            rangemode="tozero",
            showgrid=False,
            zeroline=False,
            row=1,
            col=1,
            secondary_y=True,
        )
    narrative_primary_title = _timeline_axis_title(
        selected_sources[0] if selected_sources else None, trad_metric, some_metric
    )
    narrative_secondary_title = _timeline_axis_title("SoMe", trad_metric, some_metric)
    for row in range(2, n + 2):
        fig.update_yaxes(
            title=dict(text=narrative_primary_title, font=dict(size=10)),
            range=[0, (primary_max or 1) * 1.08],
            tickformat=",",
            showgrid=True,
            gridcolor=THEME_GRID,
            row=row,
            col=1,
            secondary_y=False,
        )
        if use_secondary:
            fig.update_yaxes(
                title=dict(text=narrative_secondary_title, font=dict(size=10)),
                range=[0, (secondary_max or 1) * 1.08],
                tickformat=",",
                showgrid=False,
                zeroline=False,
                row=row,
                col=1,
                secondary_y=True,
            )
    fig.update_annotations(font=dict(color=THEME_TEXT_MUTED, size=10))
    return fig, total_px


# ---------------------------------------------------------------------------
# Top Publications / Posts table (shared across pages)
# ---------------------------------------------------------------------------

TABLE_STYLE_CELL = {
    "backgroundColor": THEME_ROW_EVEN,
    "border": f"1px solid {THEME_BORDER}",
    "color": THEME_TEXT,
    "fontSize": "12px",
    "height": "34px",
    "padding": "5px 9px",
    "textAlign": "left",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
    "whiteSpace": "nowrap",
}

TABLE_STYLE_HEADER = {
    "backgroundColor": THEME_SURFACE_ALT,
    "border": f"1px solid {THEME_BORDER}",
    "color": THEME_TEXT,
    "fontWeight": "700",
    "height": "32px",
}

TABLE_STYLE_DATA = {"height": "34px", "lineHeight": "1.2"}

TABLE_STYLE_DATA_CONDITIONAL = [
    {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
    {
        "if": {"state": "active"},
        "backgroundColor": "var(--bs-primary-bg-subtle)",
        "border": "1px solid var(--bs-primary-bg-subtle)",
    },
]

TOP_PUBLICATIONS_STYLE_DATA_CONDITIONAL = TABLE_STYLE_DATA_CONDITIONAL + [
    {"if": {"column_id": "Reach"}, "textAlign": "right"},
]

TOP_POSTS_STYLE_DATA_CONDITIONAL = TABLE_STYLE_DATA_CONDITIONAL + [
    {"if": {"column_id": "Reach"}, "textAlign": "right"},
    {"if": {"column_id": "Engagement"}, "textAlign": "right"},
]

ROW_SELECTED_STYLE = {
    "backgroundColor": "var(--bs-primary-bg-subtle)",
}


def selected_row_style_data_conditional(base: list[dict], active_cell: dict | None) -> list[dict]:
    if not active_cell:
        return base
    return base + [{"if": {"row_index": active_cell.get("row")}, **ROW_SELECTED_STYLE}]


OVERVIEW_TABLE_STYLE_CELL = {
    "backgroundColor": THEME_ROW_EVEN,
    "border": f"1px solid {THEME_BORDER}",
    "color": THEME_TEXT,
    "fontSize": "12px",
    "height": "38px",
    "padding": "5px 9px",
    "textAlign": "right",
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}

OVERVIEW_TABLE_STYLE_HEADER = {
    "backgroundColor": "var(--amazon-publishers-header-bg)",
    "border": f"1px solid {THEME_BORDER}",
    "color": THEME_TEXT,
    "fontWeight": "700",
    "height": "34px",
    "textAlign": "center",
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}

# "Top N" tables (Narratives/Campaigns top publishers/journalists/publications) share the
# Overview table's cell style, but their headers sit directly under chart controls
# rather than a panel title, so they drop the header's top border.
TOP_TABLE_STYLE_CELL = OVERVIEW_TABLE_STYLE_CELL
TOP_TABLE_STYLE_HEADER = {**OVERVIEW_TABLE_STYLE_HEADER, "borderTop": "none"}

OVERVIEW_TABLE_CSS = [
    {"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"},
    {
        "selector": "td[data-dash-column='display_name'] .dash-cell-value",
        "rule": "pointer-events: none; cursor: pointer;",
    },
    {
        "selector": ".dash-header",
        "rule": "white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;",
    },
    {
        "selector": ".current-page",
        "rule": (
            "color: var(--amazon-publishers-text) !important; "
            "background: var(--amazon-publishers-surface) !important; "
            "border-color: var(--amazon-publishers-border) !important;"
        ),
    },
    {
        "selector": ".current-page, .current-page input, .page-number, .page-number *, .dash-table-pagination, .dash-table-pagination *",
        "rule": (
            "color: var(--amazon-publishers-text) !important; "
            "-webkit-text-fill-color: var(--amazon-publishers-text) !important; "
            "opacity: 1 !important;"
        ),
    },
    {
        "selector": ".first-page, .previous-page, .next-page, .last-page",
        "rule": "color: var(--amazon-publishers-text) !important;",
    },
]


def na_panel(title: Any, children: Any, *, box: str = "panel", controls: Any = None) -> html.Div:
    """Wrap ``children`` in the shared `panel` (boxed), `outline` (bordered, no fill), or `flat` (unboxed) box style.

    All styles share the same `.na-element-title` title treatment; only the
    border/background/padding differ (defined in assets/native_analytics.css).

    If ``controls`` is given (e.g. a `dcc.RadioItems`/`dcc.Checklist` source
    toggle), it is placed alongside the title in a flex header row
    (`.na-panel-header`), title on the left and controls on the right, with
    no separator line — matching the P2S4G1/P2S2G1 layout.
    """
    content = children if isinstance(children, list) else [children]
    if box == "panel":
        class_name = "na-panel"
    elif box == "outline":
        class_name = "na-panel na-panel--outline"
    else:
        class_name = "na-panel na-panel--flat"
    if not title:
        title_node: list[Any] = []
    elif controls is not None:
        title_node = [
            html.Div(
                className="na-panel-header",
                children=[html.Div(title, className="na-element-title"), controls],
            )
        ]
    else:
        title_node = [html.Div(title, className="na-element-title")]
    return html.Div(className=class_name, children=[*title_node, *content])


def build_overview_table_section(
    *,
    records: list[dict[str, Any]],
    store_id: str,
    section_title: Any,
    controls: Any,
    dev_label: Any,
    table_id: str,
    table_data: list[dict[str, Any]],
    columns: list[dict[str, Any]],
    style_cell_conditional: list[dict[str, Any]],
    style_header_conditional: list[dict[str, Any]],
    style_data_conditional: list[dict[str, Any]],
    pre_table_children: list[Any] | None = None,
) -> html.Div:
    section_children: list[Any] = [
        dcc.Store(id=store_id, data=records),
        html.Div(
            className="amazon-publishers-section-header",
            children=[html.H2(section_title)],
        ),
        *(pre_table_children or []),
        controls,
        dev_label,
        dash_table.DataTable(
            id=table_id,
            data=table_data,
            columns=columns,
            merge_duplicate_headers=True,
            page_size=12,
            sort_action="native",
            filter_action="none",
            fixed_columns={"headers": True, "data": 0},
            cell_selectable=True,
            style_as_list_view=True,
            style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
            style_cell=OVERVIEW_TABLE_STYLE_CELL,
            style_header=OVERVIEW_TABLE_STYLE_HEADER,
            style_cell_conditional=style_cell_conditional,
            style_header_conditional=style_header_conditional,
            style_data_conditional=style_data_conditional,
            css=OVERVIEW_TABLE_CSS,
        ),
    ]
    return html.Div(className="amazon-publishers-section", children=section_children)


def build_top_publications_table(table_id: str, table_data: list[dict[str, Any]], show_publication_col: bool = False) -> Any:
    if not table_data:
        return html.Div("No publications data available.", className="amazon-publishers-empty")
    columns = [
        {"name": "Date", "id": "Date"},
        {"name": "Media Type", "id": "Media_Type"},
    ]
    cell_widths = [
        {"if": {"column_id": "Date"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px"},
        {"if": {"column_id": "Media_Type"}, "width": "100px", "minWidth": "100px", "maxWidth": "100px"},
    ]
    if show_publication_col:
        columns.append({"name": "Publication", "id": "Publication"})
        cell_widths.append({"if": {"column_id": "Publication"}, "width": "180px", "minWidth": "180px", "maxWidth": "180px"})
    columns.extend(
        [
            {"name": "Title", "id": "Title"},
            {"name": "Summary", "id": "Summary"},
            {"name": "Link", "id": "URL", "presentation": "markdown"},
            {"name": "Sentiment", "id": "Sentiment"},
            {"name": "Reach", "id": "Reach"},
        ]
    )
    cell_widths.extend(
        [
            {"if": {"column_id": "Title"}, "width": "240px", "minWidth": "240px", "maxWidth": "240px"},
            {
                "if": {"column_id": "Summary"},
                "width": "360px",
                "minWidth": "360px",
                "maxWidth": "360px",
                "whiteSpace": "nowrap",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            {"if": {"column_id": "URL"}, "width": "70px", "minWidth": "70px", "maxWidth": "70px"},
            {"if": {"column_id": "Sentiment"}, "width": "100px", "minWidth": "100px", "maxWidth": "100px"},
            {"if": {"column_id": "Reach"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px", "textAlign": "right"},
        ]
    )
    return dash_table.DataTable(
        id=table_id,
        data=table_data,
        columns=columns,
        tooltip_data=[{"Summary": {"value": str(row.get("Summary", "")), "type": "text"}} for row in table_data],
        tooltip_delay=0,
        tooltip_duration=None,
        markdown_options={"link_target": "_blank"},
        page_size=10,
        sort_action="native",
        filter_action="none",
        style_as_list_view=True,
        style_table={"overflowX": "auto", "overflowY": "hidden", "minWidth": "100%"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data=TABLE_STYLE_DATA,
        style_data_conditional=TOP_PUBLICATIONS_STYLE_DATA_CONDITIONAL,
        style_cell_conditional=cell_widths,
        css=TOOLTIP_CSS,
    )


def build_top_posts_table(table_id: str, table_data: list[dict[str, Any]], show_author_col: bool = False) -> Any:
    if not table_data:
        return html.Div("No SoMe posts data available.", className="amazon-publishers-empty")
    columns = [
        {"name": "Date", "id": "Date"},
        {"name": "Platform", "id": "Platform"},
    ]
    cell_widths = [
        {"if": {"column_id": "Date"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px"},
        {"if": {"column_id": "Platform"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px"},
    ]
    if show_author_col:
        columns.append({"name": "Author", "id": "Author"})
        cell_widths.append({"if": {"column_id": "Author"}, "width": "180px", "minWidth": "180px", "maxWidth": "180px"})
    columns.extend(
        [
            {"name": "Post Content", "id": "Post_Content"},
            {"name": "Link", "id": "URL", "presentation": "markdown"},
            {"name": "Sentiment", "id": "Sentiment"},
            {"name": "Reach", "id": "Reach"},
            {"name": "Engagement", "id": "Engagement"},
        ]
    )
    cell_widths.extend(
        [
            {
                "if": {"column_id": "Post_Content"},
                "width": "360px",
                "minWidth": "360px",
                "maxWidth": "360px",
                "whiteSpace": "nowrap",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            {"if": {"column_id": "URL"}, "width": "70px", "minWidth": "70px", "maxWidth": "70px"},
            {"if": {"column_id": "Sentiment"}, "width": "100px", "minWidth": "100px", "maxWidth": "100px"},
            {"if": {"column_id": "Reach"}, "width": "90px", "minWidth": "90px", "maxWidth": "90px", "textAlign": "right"},
            {"if": {"column_id": "Engagement"}, "width": "110px", "minWidth": "110px", "maxWidth": "110px", "textAlign": "right"},
        ]
    )
    return dash_table.DataTable(
        id=table_id,
        data=table_data,
        columns=columns,
        tooltip_data=[{"Post_Content": {"value": str(row.get("Post_Content", "")), "type": "text"}} for row in table_data],
        tooltip_delay=0,
        tooltip_duration=None,
        markdown_options={"link_target": "_blank"},
        page_size=10,
        sort_action="native",
        filter_action="none",
        style_as_list_view=True,
        style_table={"overflowX": "auto", "overflowY": "hidden", "minWidth": "100%"},
        style_cell=TABLE_STYLE_CELL,
        style_header=TABLE_STYLE_HEADER,
        style_data=TABLE_STYLE_DATA,
        style_data_conditional=TOP_POSTS_STYLE_DATA_CONDITIONAL,
        style_cell_conditional=cell_widths,
        css=TOOLTIP_CSS,
    )


def build_top_items_panel(
    id_prefix: str,
    panel_title: Any,
    trad_table_data: list[dict[str, Any]],
    some_table_data: list[dict[str, Any]],
    show_publication_col: bool = False,
    show_author_col: bool = False,
    box: str = "panel",
) -> html.Div:
    has_trad = bool(trad_table_data)
    has_some = bool(some_table_data)
    available_sources = (["Trad"] if has_trad else []) + (["SoMe"] if has_some else [])
    default_source = available_sources[0] if available_sources else "Trad"
    options = [
        {"label": opt["label"], "value": opt["value"], "disabled": opt["value"] not in available_sources}
        for opt in TRAD_SOME_OPTIONS
    ]
    controls = html.Div(
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if len(available_sources) <= 1 else None,
        children=[
            dcc.RadioItems(
                id=f"{id_prefix}-top-items-source",
                options=options,
                value=default_source,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )
    initial_table = (
        build_top_publications_table(f"{id_prefix}-top-publications", trad_table_data, show_publication_col)
        if default_source == "Trad"
        else build_top_posts_table(f"{id_prefix}-top-posts", some_table_data, show_author_col)
    )
    return na_panel(
        panel_title,
        [
            controls,
            dcc.Store(id=f"{id_prefix}-top-items-data", data={"trad": trad_table_data, "some": some_table_data}),
            html.Div(id=f"{id_prefix}-top-items-table", children=initial_table),
        ],
        box=box,
    )


def register_top_items_callback(id_prefix: str, show_publication_col: bool = False, show_author_col: bool = False) -> None:
    @callback(
        Output(f"{id_prefix}-top-items-table", "children"),
        Input(f"{id_prefix}-top-items-source", "value"),
        State(f"{id_prefix}-top-items-data", "data"),
        prevent_initial_call=True,
    )
    def _update_top_items_table(source: str | None, store_data: dict | None) -> Any:
        data = store_data or {}
        if source == "SoMe":
            return build_top_posts_table(f"{id_prefix}-top-posts", data.get("some", []), show_author_col)
        return build_top_publications_table(f"{id_prefix}-top-publications", data.get("trad", []), show_publication_col)
