"""Dash UI component builders, the table toolkit, and small generic data helpers
shared across the Amazon 2026 chart modules.

Split out of the old `charts_shared.py` god-file (see IMPROVEMENT_PLAN.md §5.4).
Depends on `theme.py` (tokens/palettes) and `timeline_charts.py` (only for
`_add_empty_figure_annotation`, in the detail-weekly figure builders below) —
never the other way around.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, dcc, html
from dash.dash_table.Format import Format, Scheme
from vizro.managers import data_manager
from vizro.models.types import capture as _vizro_capture

from dashboards.amazon_2026.data_common import SENTIMENT_ORDER
from dashboards.amazon_2026.dev_ids import is_enabled, ref_badge, ref_label
from dashboards.amazon_2026.theme import (
    ACCENT_SOME,
    ACCENT_TRAD,
    SENTIMENT_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_ROW_EVEN,
    THEME_ROW_ODD,
    THEME_SURFACE,
    THEME_SURFACE_ALT,
    THEME_TEXT,
    WEEKLY_DTICK_MS,
    hex_to_rgba,
    theme_hoverlabel,
)
from dashboards.amazon_2026.timeline_charts import _add_empty_figure_annotation, _filter_trad_some

logger = logging.getLogger(__name__)


UNAVAILABLE_MESSAGE = "Data temporarily unavailable"


def capture(mode: str):
    """`vizro.models.types.capture`, timing every `"figure"` build (§5.21).

    Every `@capture("figure")` builder runs as a Dash callback on each page
    load/control change with no caching, so the only way to see where
    server-side time actually goes is to log it directly — wrapping here
    covers every chart module without touching ~25 individual call sites.
    """
    base = _vizro_capture(mode)
    if mode != "figure":
        return base

    def decorator(func):
        @functools.wraps(func)
        def timed(*args, **kwargs):
            started = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                logger.info("%s built in %.3fs", func.__name__, time.perf_counter() - started)

        return base(timed)

    return decorator


def safe_load(key: str) -> pd.DataFrame:
    """Load a registered dataset, tolerating missing data.

    A failure here renders identically to "no data" in the UI, so it must be
    logged — otherwise a real BigQuery outage looks indistinguishable from an
    empty result, defeating the prod-raise policy in `safe_query()`. The empty
    frame is tagged via `.attrs["load_failed"]` so callers can still tell the
    two cases apart when choosing an empty-state message (§5.17).
    """
    try:
        return data_manager[key].load()
    except Exception:
        logger.exception("safe_load(%s) failed; rendering as empty", key)
        empty = pd.DataFrame()
        empty.attrs["load_failed"] = True
        return empty


def load_and_filter(key: str, filter_column: str, value: str) -> pd.DataFrame:
    """Load a registered dataset and filter to rows matching `value`, tolerating missing data."""
    df = safe_load(key)
    if not df.empty and filter_column in df.columns:
        return df[df[filter_column] == value]
    return df.iloc[0:0]


def data_load_failed(*frames: pd.DataFrame) -> bool:
    """True if any frame is the empty placeholder `safe_load()` returns after a swallowed exception.

    `.attrs` survives `.copy()`/boolean-indexing/`.dropna()`/`.sort_values()` (pandas
    `__finalize__`), so this still works after the light reshaping chart builders do —
    but not after a `pd.DataFrame(records)` round-trip through a dict/`dcc.Store`, since
    that reconstructs the frame from scratch. Those call sites carry the flag explicitly
    instead (see `timeline_figure`/`media_split_timeline_figure`).
    """
    return any(df is not None and bool(df.attrs.get("load_failed")) for df in frames)


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


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def num(record: dict[str, Any], key: str) -> float:
    return _coerce_float(record.get(key, 0))


def json_safe(record: dict[str, Any]) -> dict[str, Any]:
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


def kpi_card(
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


def sentiment_donut_slices(positive: float, neutral: float, negative: float) -> tuple[list[str], list[float], list[str]]:
    """Return (labels, values, colors) for the nonzero Positive/Neutral/Negative slices, in that order."""
    pairs = [
        (label, value)
        for label, value in (("Positive", positive), ("Neutral", neutral), ("Negative", negative))
        if value > 0
    ]
    labels = [label for label, _ in pairs]
    values = [value for _, value in pairs]
    colors = [SENTIMENT_COLORS[label] for label in labels]
    return labels, values, colors


def donut_figure(
    labels: list[str],
    values: list[float],
    colors: list[str],
    hovertemplate: str,
    direction: str = "clockwise",
) -> go.Figure:
    """Build the half-donut Pie figure shared by every mini-donut panel in this dashboard."""
    total = sum(values)
    slice_text = [
        f"{label}<br>{value / total:.1%}" if total and (value / total) >= 0.03 else ""
        for label, value in zip(labels, values)
    ]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            domain={"x": [0.2, 0.8], "y": [0.12, 0.88]},
            sort=False,
            direction=direction,
            marker={"colors": colors, "line": {"color": THEME_SURFACE, "width": 0.5}},
            text=slice_text,
            textinfo="text",
            textposition="outside",
            textfont={"color": THEME_TEXT, "size": 11},
            automargin=True,
            hovertemplate=hovertemplate,
            hoverlabel={"bgcolor": THEME_SURFACE, "bordercolor": THEME_BORDER, "font": {"color": THEME_TEXT}},
            showlegend=False,
        )
    )
    fig.update_layout(
        autosize=True,
        width=None,
        height=None,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uniformtext={"minsize": 10, "mode": "hide"},
    )
    return fig


def donut_panel(title: str, figure: go.Figure, *, graph_height: int | None = None) -> html.Div:
    """Wrap a donut_figure() in the mini-donut card shell used on Narratives/Publishers/Discover."""
    graph_style = {"width": "100%", "minWidth": 0}
    graph_style["height"] = f"{graph_height}px" if graph_height else "100%"
    inline_menu = bool(title)
    menu_btn = chart_menu_button(has_plot=True, has_table=False, inline=inline_menu)
    class_name = "amazon-publishers-mini-donut"
    header_children: list[Any] = [html.Div(title, className="amazon-publishers-mini-title")]
    extra_children = []
    if menu_btn is not None:
        class_name += " na-chart-menu-host"
        if inline_menu:
            header_children.append(menu_btn)
        else:
            extra_children.append(menu_btn)
    return html.Div(
        className=class_name,
        style={"minHeight": f"{graph_height + 28}px"} if graph_height else {},
        children=[
            html.Div(className="amazon-publishers-mini-donut-header", children=header_children),
            dcc.Graph(
                figure=figure,
                responsive=True,
                config={"displayModeBar": False},
                className="amazon-publishers-mini-donut-graph",
                style=graph_style,
            ),
            *extra_children,
        ],
    )


def empty_donut_panel(message: str = "No data available") -> html.Div:
    return html.Div(
        className="amazon-publishers-mini-donut amazon-publishers-mini-donut-empty",
        children=[html.Div(message, className="amazon-publishers-mini-empty")],
    )


NARRATIVE_BAR_COLORS = {
    "trad_publications": "var(--na-bar-trad-publications)",
    "trad_reach": "var(--na-bar-trad-reach)",
    "trad_positive_share_of_reach": "var(--na-bar-positive)",
    "trad_negative_share_of_reach": "var(--na-bar-negative)",
    "some_posts": "var(--na-bar-some-posts)",
    "some_reach": "var(--na-bar-some-reach)",
    "some_engagement": "var(--na-bar-some-engagement)",
    "some_average_engagement": "var(--na-bar-some-average)",
    "some_positive_share_of_reach": "var(--na-bar-positive)",
    "some_negative_share_of_reach": "var(--na-bar-negative)",
}


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
            "color": "var(--na-link)",
            "cursor": "pointer",
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
            "fontWeight": "700",
            "textAlign": "left",
        },
        {
            "if": {"state": "active"},
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME_BORDER}",
        },
        {
            "if": {"state": "selected"},
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME_BORDER}",
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
        max_value = max((num(row, column_id) for row in table_data), default=0)
        if max_value <= 0:
            continue
        for row in table_data:
            pct = max(0, min(100, (num(row, column_id) / max_value) * 100))
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


TRAD_SOME_OPTIONS = [
    {"label": "Trad", "value": "Trad"},
    {"label": "SoMe", "value": "SoMe"},
]

SENTIMENT_OPTIONS = [{"label": value, "value": value} for value in SENTIMENT_ORDER]


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


def detail_metric_values(basic_metric: str) -> tuple[str, str]:
    if basic_metric == "reach":
        return "reach", "engagement"
    return "publications", "posts"


def timeline_records_from_frame(data_frame: pd.DataFrame, id_field: str = "publisher_uid") -> list[dict[str, Any]]:
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
    return [json_safe(record) for record in df.to_dict("records")]


# ---------------------------------------------------------------------------
# Top Publications / Posts table (shared across pages)
# ---------------------------------------------------------------------------

TOOLTIP_CSS = [
    {"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"},
    {"selector": "td.focused, td.focused *", "rule": "box-shadow: none !important; outline: none !important; border-color: inherit !important;"},
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
        "backgroundColor": "transparent",
        "border": f"1px solid {THEME_BORDER}",
        "boxShadow": "none",
        "outline": "none",
    },
    {
        "if": {"state": "selected"},
        "backgroundColor": "transparent",
        "border": f"1px solid {THEME_BORDER}",
        "boxShadow": "none",
        "outline": "none",
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
    "backgroundColor": "transparent",
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
    "backgroundColor": "var(--na-header-bg)",
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
            "color: var(--na-text) !important; "
            "background: var(--na-surface) !important; "
            "border-color: var(--na-border) !important;"
        ),
    },
    {
        "selector": ".current-page, .current-page input, .page-number, .page-number *, .dash-table-pagination, .dash-table-pagination *",
        "rule": (
            "color: var(--na-text) !important; "
            "-webkit-text-fill-color: var(--na-text) !important; "
            "opacity: 1 !important;"
        ),
    },
    {
        "selector": ".first-page, .previous-page, .next-page, .last-page",
        "rule": "color: var(--na-text) !important;",
    },
]


_NESTED_MENU_HOST_CLASSES = {"na-panel", "amazon-publishers-mini-donut", "amazon-publishers-venn"}


def _panel_menu_capabilities(children: Any) -> tuple[bool, bool]:
    """Walk a Dash component tree and report whether it contains a Graph and/or a DataTable.

    Used to decide whether a panel gets a chart-menu button at all, and which
    of its export actions are enabled — mirrors what the old JS injector used
    to detect from the rendered DOM (`.js-plotly-plot` / `<table>`).

    Stops descending into a nested `na_panel`/`donut_panel`/Venn panel (e.g. a
    mini-donut nested inside a `box="flat"` KPI panel) — that nested panel
    already renders its own chart-menu button, so counting its graph/table
    here would give the outer panel a second, redundant one.
    """
    has_plot = False
    has_table = False
    stack = list(children) if isinstance(children, (list, tuple)) else [children]
    while stack:
        node = stack.pop()
        if node is None or isinstance(node, (str, int, float)):
            continue
        class_name = getattr(node, "className", None) or ""
        if _NESTED_MENU_HOST_CLASSES.intersection(class_name.split()):
            continue
        if isinstance(node, dcc.Graph):
            has_plot = True
        elif isinstance(node, dash_table.DataTable):
            has_table = True
        kids = getattr(node, "children", None)
        if isinstance(kids, (list, tuple)):
            stack.extend(kids)
        elif kids is not None:
            stack.append(kids)
    return has_plot, has_table


_CHART_MENU_ITEMS = [
    ("copy-image", "⧉", "Copy Image to Clipboard", True),
    ("download-image", "↓", "Download Image", True),
    None,  # separator
    ("copy-data", "⬚", "Copy Data to Clipboard", False),
    ("download-data", "↓", "Download Data", False),
]


def chart_menu_button(has_plot: bool, has_table: bool, *, inline: bool = False) -> html.Div | None:
    """Build the `⋮` chart-options button + dropdown, or None if there's nothing to export.

    Rendered as a normal Dash child (not injected via JS) so Dash/React owns
    it from the start — see native_analytics_chartmenu.js for the click
    handlers, which now only attach behavior to this markup instead of
    creating/inserting it into the live DOM.

    ``inline=True`` renders it as a normal flex item (`.na-chart-menu-btn--inline`,
    always visible, sized to match the Trad/SoMe toggle pills) for panels that
    already have a header row — `na_panel`/`donut_panel` use this whenever
    there's a title and/or `controls`, so the button joins that row instead of
    floating an absolutely-positioned corner button on top of it (which is
    what caused it to overlap the Trad/SoMe toggle). With nothing else in the
    header, the plain hover-to-reveal corner button (`inline=False`, the
    default) stays — there's nothing for it to collide with.
    """
    if not has_plot and not has_table:
        return None
    items: list[Any] = []
    for entry in _CHART_MENU_ITEMS:
        if entry is None:
            items.append(html.Div(className="na-chart-menu-separator"))
            continue
        action, icon, label, requires_plotly = entry
        class_name = "na-chart-menu-item"
        extra: dict[str, str] = {}
        if requires_plotly:
            extra["data-requires-plotly"] = "true"
            if not has_plot:
                class_name += " na-chart-menu-item--disabled"
                extra["title"] = "Not available for this panel type"
        items.append(
            html.Button(
                className=class_name,
                children=[
                    html.Span(icon, className="na-chart-menu-item-icon"),
                    html.Span(label),
                ],
                **{"data-action": action, **extra},
            )
        )
    btn_class = "na-chart-menu-btn na-chart-menu-btn--inline" if inline else "na-chart-menu-btn"
    return html.Div(
        className=btn_class,
        title="Chart options",
        children=["⋮", html.Div(className="na-chart-menu-dropdown", children=items)],
        **{"role": "button", "tabIndex": "0", "aria-label": "Chart options"},
    )


def na_panel(title: Any, children: Any, *, box: str = "panel", controls: Any = None) -> html.Div:
    """Wrap ``children`` in the shared `panel` (boxed), `outline` (bordered, no fill), or `flat` (unboxed) box style.

    All styles share the same `.na-element-title` title treatment; only the
    border/background/padding differ (defined in assets/native_analytics.css).

    If ``controls`` is given (e.g. a `dcc.RadioItems`/`dcc.Checklist` source
    toggle), it is placed alongside the title in a flex header row
    (`.na-panel-header`), title on the left and controls (and the chart-menu
    button, if any) on the right in a `.na-panel-header-actions` group, with
    no separator line — matching the P2S4G1/P2S2G1 layout. With no title and
    no controls, the chart-menu button (if any) falls back to a plain
    hover-to-reveal corner button instead of growing a header row just to
    hold it — see `chart_menu_button()`.
    """
    content = children if isinstance(children, list) else [children]
    if box == "panel":
        class_name = "na-panel"
    elif box == "outline":
        class_name = "na-panel na-panel--outline"
    else:
        class_name = "na-panel na-panel--flat"

    inline_menu = bool(title) or controls is not None
    menu_btn = chart_menu_button(*_panel_menu_capabilities(content), inline=inline_menu)

    right_side: list[Any] = []
    if controls is not None:
        right_side.append(controls)
    if menu_btn is not None and inline_menu:
        right_side.append(menu_btn)

    if not title and not right_side:
        title_node: list[Any] = []
    elif not right_side:
        title_node = [html.Div(title, className="na-element-title")]
    else:
        header_children: list[Any] = []
        if title:
            header_children.append(html.Div(title, className="na-element-title"))
        header_children.append(html.Div(className="na-panel-header-actions", children=right_side))
        title_node = [html.Div(className="na-panel-header", children=header_children)]

    extra_children = []
    if menu_btn is not None:
        class_name += " na-chart-menu-host"
        if not inline_menu:
            extra_children.append(menu_btn)

    return html.Div(className=class_name, children=[*title_node, *content, *extra_children])


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
    menu_btn = chart_menu_button(has_plot=False, has_table=True, inline=True)
    section_class = "amazon-publishers-section"
    header_children: list[Any] = [html.H2(section_title)]
    if menu_btn is not None:
        section_class += " na-chart-menu-host"
        header_children.append(menu_btn)
    section_children: list[Any] = [
        dcc.Store(id=store_id, data=records),
        html.Div(className="amazon-publishers-section-header", children=header_children),
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
    return html.Div(className=section_class, children=section_children)


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


def build_top_items_table_data(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split JSON-safe records into trad/some table row dicts for build_top_items_panel.

    Always includes Publication, Author, Angle, Angle_ID so the DataTable store
    carries them for row-click callbacks; columns not in the table column config
    are silently ignored by Dash DataTable.
    """
    trad_rows = [r for r in records if str(r.get("Source", "")) == "Trad"]
    some_rows = [r for r in records if str(r.get("Source", "")) == "SoMe"]

    def _url(r: dict) -> str:
        url = r.get("URL", "")
        return f"[link]({url})" if str(url).startswith("http") else ""

    trad_data = [
        {
            "Date": str(r.get("Date", "") or ""),
            "Media_Type": str(r.get("Type", "")),
            "Publication": str(r.get("Publication", "") or ""),
            "Title": str(r.get("Title", "")),
            "Summary": str(r.get("Summary", "")),
            "URL": _url(r),
            "Sentiment": str(r.get("Sentiment", "")),
            "Reach": num(r, "Reach"),
            "Angle_ID": str(r.get("Angle_ID", "") or ""),
            "Angle": str(r.get("Angle", "") or ""),
        }
        for r in trad_rows
    ]
    some_data = [
        {
            "Date": str(r.get("Date", "") or ""),
            "Platform": str(r.get("Type", "")),
            "Author": str(r.get("Author", "") or ""),
            "Post_Content": str(r.get("Summary", "")),
            "URL": _url(r),
            "Sentiment": str(r.get("Sentiment", "")),
            "Reach": num(r, "Reach"),
            "Engagement": num(r, "Engagement"),
            "Angle_ID": str(r.get("Angle_ID", "") or ""),
            "Angle": str(r.get("Angle", "") or ""),
        }
        for r in some_rows
    ]
    return trad_data, some_data


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
            dcc.Store(id=f"{id_prefix}-top-items-data", data={"trad": trad_table_data, "some": some_table_data}),
            html.Div(id=f"{id_prefix}-top-items-table", children=initial_table),
        ],
        controls=controls,
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


# ---------------------------------------------------------------------------
# Detail weekly timeline builders (shared by Narratives, Campaigns, Topic Areas)
# ---------------------------------------------------------------------------

# Line style per source — solid/circle for Trad, dotted/diamond for SoMe.
# Cumulative lines reuse the source color with a dashed stroke so they stay
# visually distinct from both the weekly bars and each other.
_DETAIL_SOURCE_STYLE: dict[str, dict] = {
    "Trad": {"color": ACCENT_TRAD, "dash": "solid", "marker": "circle"},
    "SoMe": {"color": ACCENT_SOME, "dash": "dot", "marker": "diamond"},
}
_DETAIL_CUMULATIVE_DASH = "dash"


def _apply_detail_weekly_layout(
    fig: go.Figure, y_title: str, x_range: list[str] | None = None, dtick: int | None = None
) -> None:
    xaxis_cfg: dict = dict(
        title=None,
        tickformat="%d %b",
        hoverformat="%d %b %Y",
        dtick=WEEKLY_DTICK_MS if dtick is None else dtick,
        showgrid=True,
        gridcolor=THEME_GRID,
    )
    if x_range:
        xaxis_cfg["range"] = x_range
    if dtick == 0:
        xaxis_cfg.pop("dtick", None)
    elif dtick:
        xaxis_cfg["dtick"] = dtick

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=95, r=20, t=10, b=46),
        hovermode="x unified",
        legend=dict(
            orientation="v",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor=THEME_SURFACE,
            bordercolor=THEME_BORDER,
            borderwidth=1,
            font=dict(size=10),
            title=None,
        ),
        xaxis=xaxis_cfg,
        yaxis=dict(
            title=y_title,
            tickformat=",",
            rangemode="tozero",
            automargin=False,
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        hoverlabel=theme_hoverlabel(namelength=-1, align="left"),
    )


def detail_weekly_figure(
    data_frame: pd.DataFrame,
    metric_col: str,
    y_title: str,
    cum_title: str,
    source: str = "Trad",
    x_range: list[str] | None = None,
    dtick: int | None = None,
    load_failed: bool = False,
) -> go.Figure:
    """Single-entity weekly line with a cumulative line on a secondary y-axis."""
    style = _DETAIL_SOURCE_STYLE.get(source, _DETAIL_SOURCE_STYLE["Trad"])
    color = style["color"]

    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    failed = load_failed or data_load_failed(df)
    fig = go.Figure()
    if df.empty or "week_start" not in df.columns:
        _add_empty_figure_annotation(fig, UNAVAILABLE_MESSAGE if failed else "No data available")
        _apply_detail_weekly_layout(fig, y_title, x_range, dtick=dtick)
        return fig

    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
    df = df.dropna(subset=["week_start"]).sort_values("week_start")

    if df.empty:
        _add_empty_figure_annotation(fig, UNAVAILABLE_MESSAGE if failed else "No data available")
        _apply_detail_weekly_layout(fig, y_title, x_range, dtick=dtick)
        return fig

    cumulative = df[metric_col].cumsum()

    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=df[metric_col],
            name=y_title,
            mode="lines+markers",
            line=dict(width=2.5, color=color, shape="spline", smoothing=0.45, dash=style["dash"]),
            marker=dict(size=5, color=color, symbol=style["marker"]),
            fill="tozeroy",
            fillcolor=hex_to_rgba(color, 0.12),
            hovertemplate=f"{y_title}: %{{y:,.0f}}<extra></extra>",
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=cumulative,
            name=cum_title,
            mode="lines",
            line=dict(width=2, color=color, dash=_DETAIL_CUMULATIVE_DASH),
            hovertemplate=f"{cum_title}: %{{y:,.0f}}<extra></extra>",
            yaxis="y2",
        )
    )

    _apply_detail_weekly_layout(fig, y_title, x_range, dtick=dtick)
    fig.update_layout(
        hovermode="closest",
        yaxis2=dict(
            title=cum_title,
            tickformat=",",
            rangemode="tozero",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    return fig


def detail_combined_weekly_figure(
    trad_df: pd.DataFrame,
    some_df: pd.DataFrame,
    trad_metric_col: str,
    trad_label: str,
    trad_cum_label: str,
    some_metric_col: str,
    some_label: str,
    some_cum_label: str,
    y_title: str,
    cum_title: str,
    x_range: list[str] | None = None,
    dtick: int | None = None,
    load_failed: bool = False,
) -> go.Figure:
    """Trad + SoMe weekly metric, each with its own cumulative line."""
    failed = load_failed or data_load_failed(trad_df, some_df)
    fig = go.Figure()

    def _prep(data_frame: pd.DataFrame, metric_col: str) -> pd.DataFrame:
        df = data_frame.copy() if data_frame is not None else pd.DataFrame()
        if df.empty or "week_start" not in df.columns:
            return pd.DataFrame()
        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
        df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
        return df.dropna(subset=["week_start"]).sort_values("week_start")

    series = [
        ("Trad", _prep(trad_df, trad_metric_col), trad_metric_col, trad_label, trad_cum_label),
        ("SoMe", _prep(some_df, some_metric_col), some_metric_col, some_label, some_cum_label),
    ]

    for source, df, metric_col, weekly_label, cum_label in series:
        if df.empty:
            continue
        style = _DETAIL_SOURCE_STYLE[source]
        color = style["color"]
        cumulative = df[metric_col].cumsum()
        fig.add_trace(
            go.Scatter(
                x=df["week_start"],
                y=df[metric_col],
                name=weekly_label,
                mode="lines+markers",
                line=dict(width=2.5, color=color, shape="spline", smoothing=0.45, dash=style["dash"]),
                marker=dict(size=5, color=color, symbol=style["marker"]),
                fill="tozeroy",
                fillcolor=hex_to_rgba(color, 0.1),
                hovertemplate=f"{weekly_label}: %{{y:,.0f}}<extra></extra>",
                yaxis="y",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["week_start"],
                y=cumulative,
                name=cum_label,
                mode="lines",
                line=dict(width=2, color=color, dash=_DETAIL_CUMULATIVE_DASH),
                hovertemplate=f"{cum_label}: %{{y:,.0f}}<extra></extra>",
                yaxis="y2",
            )
        )

    if not fig.data:
        _add_empty_figure_annotation(fig, UNAVAILABLE_MESSAGE if failed else "No data available")

    _apply_detail_weekly_layout(fig, y_title, x_range, dtick=dtick)
    fig.update_layout(
        hovermode="closest",
        yaxis2=dict(
            title=cum_title,
            tickformat=",",
            rangemode="tozero",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Generic trad/some metric table + KPI/UI toolkit
# (originally Publishers-only; shared by Publishers, Campaigns, Topic Areas via
# the trad/some metric-column convention any entity's records can be reshaped into)
# ---------------------------------------------------------------------------


SOURCE_OPTIONS = [
    {"label": "All", "value": "All"},
    {"label": "Trad", "value": "Trad"},
    {"label": "SoMe", "value": "SoMe"},
    {"label": "Trad&SoMe", "value": "Trad+SoMe"},
]

TRAD_COLUMNS = [
    "trad_article_count",
    "trad_total_reach",
    "trad_positive_share",
    "trad_negative_share",
]
SOME_COLUMNS = [
    "some_post_count",
    "some_total_reach",
    "some_total_engagement",
    "some_avg_engagement",
    "some_positive_share",
    "some_negative_share",
    "some_engagement_positive_share",
    "some_engagement_negative_share",
]
BAR_COLORS = {
    "trad_article_count": "var(--na-bar-trad-publications)",
    "trad_total_reach": "var(--na-bar-trad-reach)",
    "trad_positive_share": "var(--na-bar-positive)",
    "trad_negative_share": "var(--na-bar-negative)",
    "some_post_count": "var(--na-bar-some-posts)",
    "some_total_reach": "var(--na-bar-some-reach)",
    "some_total_engagement": "var(--na-bar-some-engagement)",
    "some_avg_engagement": "var(--na-bar-some-average)",
    "some_positive_share": "var(--na-bar-positive)",
    "some_negative_share": "var(--na-bar-negative)",
    "some_engagement_positive_share": "var(--na-bar-positive)",
    "some_engagement_negative_share": "var(--na-bar-negative)",
}


def _precompute_bar_styles_by_column() -> dict[str, list[dict[str, Any]]]:
    """Build per-column gradient rules for all 101 percentage buckets × 2 row parities.

    Runs once at import time so data_bar_styles never iterates over table rows.
    Each rule matches on hidden data columns ({col}_pct and row_parity) so the
    DataTable only evaluates O(rules_per_col × rows) instead of O(N²) filter
    expressions. Rules are keyed by column so data_bar_styles can filter to
    only visible columns in O(n_columns) time.
    """
    row_bgs = [
        ("even", THEME_ROW_EVEN),
        ("odd", THEME_ROW_ODD),
    ]
    result: dict[str, list[dict[str, Any]]] = {}
    for col, color in BAR_COLORS.items():
        col_rules: list[dict[str, Any]] = []
        for pct in range(101):
            for parity, row_bg in row_bgs:
                col_rules.append({
                    "if": {
                        "column_id": col,
                        "filter_query": f"{{row_parity}} = '{parity}' && {{{col}_pct}} = {pct}",
                    },
                    "background": (
                        f"linear-gradient(90deg, {color} 0%, {color} {pct}%, "
                        f"{row_bg} {pct}%, {row_bg} 100%)"
                    ),
                })
        result[col] = col_rules
    return result


_BAR_STYLES_BY_COLUMN: dict[str, list[dict[str, Any]]] = _precompute_bar_styles_by_column()


def table_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [
        {
            "id": record.get("publisher_uid", ""),
            "row_id": idx,
            "row_parity": "odd" if idx % 2 else "even",
            "publisher_uid": record.get("publisher_uid", ""),
            "publisher_type": record.get("publisher_type", ""),
            "display_name": record.get("display_name", ""),
            "trad_article_count": num(record, "trad_article_count"),
            "trad_total_reach": num(record, "trad_total_reach"),
            "trad_positive_share": _share_fraction(record, "trad_positive_pct"),
            "trad_negative_share": _share_fraction(record, "trad_negative_pct"),
            "some_post_count": num(record, "some_post_count"),
            "some_total_reach": num(record, "some_total_reach"),
            "some_total_engagement": num(record, "some_total_engagement"),
            "some_avg_engagement": num(record, "some_avg_engagement"),
            "some_positive_share": _share_fraction(record, "some_positive_pct"),
            "some_negative_share": _share_fraction(record, "some_negative_pct"),
            "some_engagement_positive_share": _engagement_sentiment_share(record, "some_engagement_positive"),
            "some_engagement_negative_share": _engagement_sentiment_share(record, "some_engagement_negative"),
        }
        for idx, record in enumerate(records)
    ]
    # Add normalised percentage columns used by _BAR_STYLES_BY_COLUMN filter rules.
    for col in [*TRAD_COLUMNS, *SOME_COLUMNS]:
        max_val = max((num(r, col) for r in rows), default=0)
        for r in rows:
            r[f"{col}_pct"] = round((num(r, col) / max_val) * 100) if max_val > 0 else 0
    return rows


def table_columns(source_filter: str) -> list[dict[str, Any]]:
    visible_metric_columns = []
    if source_filter in {"All", "Trad", "Trad+SoMe"}:
        visible_metric_columns.extend(
            [
                {
                    "name": ["Trad", "Publications"],
                    "id": "trad_article_count",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["Trad", "Reach"],
                    "id": "trad_total_reach",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["Trad", "Positive sentiment share of reach"],
                    "id": "trad_positive_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["Trad", "Negative sentiment share of reach"],
                    "id": "trad_negative_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
            ]
        )
    if source_filter in {"All", "SoMe", "Trad+SoMe"}:
        visible_metric_columns.extend(
            [
                {
                    "name": ["SoMe", "Posts"],
                    "id": "some_post_count",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Reach"],
                    "id": "some_total_reach",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Engagement"],
                    "id": "some_total_engagement",
                    "type": "numeric",
                    "format": Format(group=True, precision=0, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Average Engagement"],
                    "id": "some_avg_engagement",
                    "type": "numeric",
                    "format": Format(group=True, precision=1, scheme=Scheme.fixed),
                },
                {
                    "name": ["SoMe", "Positive sentiment share of reach"],
                    "id": "some_positive_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["SoMe", "Negative sentiment share of reach"],
                    "id": "some_negative_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["SoMe", "Share of positive engagement"],
                    "id": "some_engagement_positive_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
                {
                    "name": ["SoMe", "Share of negative engagement"],
                    "id": "some_engagement_negative_share",
                    "type": "numeric",
                    "format": Format(precision=1, scheme=Scheme.percentage),
                },
            ]
        )
    return [{"name": ["", "Author"], "id": "display_name"}, *visible_metric_columns]


def _has_source_divider(columns: list[dict[str, Any]]) -> bool:
    visible_ids = {column["id"] for column in columns}
    return "some_post_count" in visible_ids and any(column_id in visible_ids for column_id in TRAD_COLUMNS)


def header_divider_styles(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styles = [
        {
            "if": {"column_id": "display_name"},
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
        }
    ]
    if not _has_source_divider(columns):
        return styles
    styles.append(
        {
            "if": {"column_id": "some_post_count"},
            "borderLeft": "none",
            "boxShadow": f"inset 1px 0 0 {THEME_BORDER}",
        }
    )
    return styles


def data_bar_styles(table_data: list[dict[str, Any]], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # table_data is not read here; percentage buckets are pre-baked into row data
    # by table_records and matched via _BAR_STYLES_BY_COLUMN filter rules.
    visible_ids = {column["id"] for column in columns}
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {
            "if": {"column_id": "display_name"},
            "color": "var(--na-link)",
            "cursor": "pointer",
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
            "position": "relative",
            "zIndex": 4,
        },
        {
            "if": {"state": "active"},
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME_BORDER}",
        },
        {
            "if": {"state": "selected"},
            "backgroundColor": "transparent",
            "border": f"1px solid {THEME_BORDER}",
        },
    ]
    if _has_source_divider(columns):
        styles.append({
            "if": {"column_id": "some_post_count"},
            "borderLeft": "none",
            "boxShadow": f"inset 1px 0 0 {THEME_BORDER}",
        })
    for col in [*TRAD_COLUMNS, *SOME_COLUMNS]:
        if col in visible_ids:
            styles.extend(_BAR_STYLES_BY_COLUMN[col])
    return styles


def cell_width_styles() -> list[dict[str, Any]]:
    metric_width = {"width": "150px", "maxWidth": "150px", "minWidth": "150px"}
    return [
        {
            "if": {"column_id": "display_name"},
            "width": "240px",
            "maxWidth": "240px",
            "minWidth": "240px",
            "textAlign": "left",
            "fontWeight": "700",
        },
        *[
            {"if": {"column_id": column}, **metric_width, "textAlign": "right"}
            for column in [*TRAD_COLUMNS, *SOME_COLUMNS]
        ],
    ]


def detail_kpi_groups(record: dict[str, Any]) -> tuple[list[html.Div], list[html.Div]]:
    trad_cards: list[html.Div] = []
    if num(record, "trad_article_count") > 0:
        trad_cards = [
            kpi_card("Trad publications", f"{num(record, 'trad_article_count'):,.0f}"),
            kpi_card("Trad reach", f"{num(record, 'trad_total_reach'):,.0f}"),
            kpi_card("Trad positive share", f"{num(record, 'trad_positive_pct'):,.1f}%"),
            kpi_card("Trad negative share", f"{num(record, 'trad_negative_pct'):,.1f}%"),
        ]
    some_cards: list[html.Div] = []
    if num(record, "some_post_count") > 0:
        some_cards = [
            kpi_card("SoMe posts", f"{num(record, 'some_post_count'):,.0f}"),
            kpi_card("SoMe reach", f"{num(record, 'some_total_reach'):,.0f}"),
            kpi_card("SoMe engagement", f"{num(record, 'some_total_engagement'):,.0f}"),
            kpi_card("Avg. engagement", f"{num(record, 'some_avg_engagement'):,.1f}"),
            kpi_card("SoMe positive share", f"{num(record, 'some_positive_pct'):,.1f}%"),
            kpi_card("SoMe negative share", f"{num(record, 'some_negative_pct'):,.1f}%"),
        ]
    return trad_cards, some_cards


def dev_inline_label(ref: str, label: str = "") -> html.Div | None:
    if not is_enabled():
        return None
    text = ref_label(label, ref) if label else ref_badge(ref)
    return html.Div(text, className="na-dev-inline-label")


def find_record(records: list[dict[str, Any]], selected_uid: str | None) -> dict[str, Any] | None:
    if selected_uid is None:
        return None
    for record in records:
        if record.get("publisher_uid") == selected_uid:
            return record
    return None


def _share_fraction(record: dict[str, Any], key: str) -> float:
    return num(record, key) / 100


def _engagement_sentiment_share(record: dict[str, Any], key: str) -> float:
    total = (
        num(record, "some_engagement_positive")
        + num(record, "some_engagement_negative")
        + num(record, "some_engagement_neutral")
    )
    if total <= 0:
        return 0.0
    return num(record, key) / total


# ---------------------------------------------------------------------------
# Top publishers / top journalists detail tables
# (originally Narratives-only; shared by Narratives, Campaigns, Topic Areas pages)
# ---------------------------------------------------------------------------


def build_shared_x_range(trad_df: pd.DataFrame, some_df: pd.DataFrame) -> list[str] | None:
    weeks: list[pd.Series] = []
    for df, col in [(trad_df, "week_start"), (some_df, "week_start")]:
        if not df.empty and col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce").dropna()
            if not parsed.empty:
                weeks.append(parsed)
    if not weeks:
        return None
    all_weeks = pd.concat(weeks)
    padding = pd.Timedelta(days=3)
    return [
        (all_weeks.min() - padding).isoformat(),
        (all_weeks.max() + padding).isoformat(),
    ]


_TOP_TABLES_LIMIT = 25
TOP_TABLES_PAGE_SIZE = 9


def top_publishers_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "Publisher", "id": "publisher"},
        {"name": "Media Type / Platform", "id": "media_type_platform"},
        {
            "name": "Publications",
            "id": "publications",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": "Reach",
            "id": "reach",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
    ]


def top_publishers_table_rows(records: list[dict[str, Any]], source: str | None) -> list[dict[str, Any]]:
    selected = source if source in ("Trad", "SoMe") else "Trad"
    filtered = [r for r in records if r.get("source") == selected]
    filtered.sort(key=lambda r: num(r, "reach"), reverse=True)
    rows = []
    for idx, record in enumerate(filtered[:_TOP_TABLES_LIMIT]):
        rows.append(
            {
                "id": record.get("publisher", ""),
                "row_id": idx,
                "publisher": record.get("publisher", ""),
                "media_type_platform": record.get("media_type_platform", ""),
                "publications": num(record, "publications"),
                "reach": num(record, "reach"),
                "source": selected,
            }
        )
    return rows


def _data_bar_column_styles(
    table_data: list[dict[str, Any]],
    column_id: str,
    bar_color: Callable[[dict[str, Any]], str] | str,
) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = []
    max_value = max((num(row, column_id) for row in table_data), default=0)
    if max_value <= 0:
        return styles
    for row in table_data:
        pct = max(0, min(100, (num(row, column_id) / max_value) * 100))
        row_bg = THEME_ROW_ODD if int(row["row_id"]) % 2 else THEME_ROW_EVEN
        color = bar_color(row) if callable(bar_color) else bar_color
        styles.append(
            {
                "if": {"filter_query": f"{{row_id}} = {row['row_id']}", "column_id": column_id},
                "background": (
                    f"linear-gradient(90deg, {color} 0%, {color} {pct:.2f}%, "
                    f"{row_bg} {pct:.2f}%, {row_bg} 100%)"
                ),
            }
        )
    return styles


def top_publishers_data_bar_styles(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {"if": {"column_id": "publisher"}, "textAlign": "left", "fontWeight": "500"},
        {"if": {"column_id": "media_type_platform"}, "textAlign": "left"},
    ]
    styles += _data_bar_column_styles(
        table_data,
        "reach",
        lambda row: (
            "var(--na-bar-trad-reach)"
            if row.get("source") == "Trad"
            else "var(--na-bar-some-reach)"
        ),
    )
    styles += _data_bar_column_styles(
        table_data,
        "publications",
        lambda row: (
            "var(--na-bar-trad-publications)"
            if row.get("source") == "Trad"
            else "var(--na-bar-some-posts)"
        ),
    )
    return styles


def top_journalists_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "Journalist", "id": "journalist"},
        {
            "name": "Publications",
            "id": "publications",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": "Reach",
            "id": "reach",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
    ]


def top_journalists_table_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sorted_records = sorted(records, key=lambda r: num(r, "reach"), reverse=True)
    rows = []
    for idx, record in enumerate(sorted_records[:_TOP_TABLES_LIMIT]):
        rows.append(
            {
                "id": record.get("journalist", ""),
                "row_id": idx,
                "journalist": record.get("journalist", ""),
                "publications": num(record, "publications"),
                "reach": num(record, "reach"),
            }
        )
    return rows


def top_journalists_data_bar_styles(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {"if": {"column_id": "journalist"}, "textAlign": "left", "fontWeight": "500"},
    ]
    styles += _data_bar_column_styles(table_data, "reach", "var(--na-bar-trad-reach)")
    styles += _data_bar_column_styles(table_data, "publications", "var(--na-bar-trad-publications)")
    return styles
