"""Discover page components — unified Trad/SoMe item browser with filters and search."""
from __future__ import annotations

from typing import Any

import pandas as pd
from dash import dcc, html

import plotly.graph_objects as go

from dashboards.amazon_2026.charts_archive import _archive_figure, _build_color_map
from dashboards.amazon_2026.charts_shared import (
    SENTIMENT_COLORS,
    THEME_BORDER,
    THEME_SURFACE,
    THEME_TEXT,
    TOP_POSTS_STYLE_DATA_CONDITIONAL,
    TOP_PUBLICATIONS_STYLE_DATA_CONDITIONAL,
    TRAD_SOME_OPTIONS,
    _filter_trad_some,
    _json_safe,
    _kpi_card,
    _num,
    build_top_posts_table,
    build_top_publications_table,
    na_panel,
)
from dashboards.amazon_2026.data_common import SENTIMENT_ORDER
from dashboards.amazon_2026.dev_ids import ref_label

SENTIMENT_OPTIONS = [{"label": value, "value": value} for value in SENTIMENT_ORDER]


# ---------------------------------------------------------------------------
# Record preparation
# ---------------------------------------------------------------------------


def discover_records(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    if data_frame.empty:
        return []
    frame = data_frame.copy().reset_index(drop=True)
    dates = pd.to_datetime(frame["Date"], errors="coerce")
    min_date = dates.min()
    frame["_date_index"] = (dates - min_date).dt.days.fillna(0).astype(int)
    frame["_id"] = frame.index
    frame["_search"] = (
        frame["Publisher"].fillna("").astype(str)
        + " "
        + frame["Title"].fillna("").astype(str)
        + " "
        + frame["Summary"].fillna("").astype(str)
    ).str.lower()
    frame["_search_fulltext"] = (frame["_search"] + " " + frame["Full_Text"].fillna("").astype(str).str.lower())
    if "umap_x" in frame.columns:
        frame["umap_x"] = pd.to_numeric(frame["umap_x"], errors="coerce")
    if "umap_y" in frame.columns:
        frame["umap_y"] = pd.to_numeric(frame["umap_y"], errors="coerce")
    return [_json_safe(row) for row in frame.to_dict("records")]


def discover_date_bounds(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"min_date": "", "max_date": "", "max_index": 0}
    dates = sorted(record.get("Date", "") for record in records if record.get("Date"))
    max_index = max(int(record.get("_date_index", 0)) for record in records)
    return {"min_date": dates[0], "max_date": dates[-1], "max_index": max_index}


def discover_date_marks(date_bounds: dict[str, Any]) -> dict[int, str]:
    min_date = pd.to_datetime(date_bounds.get("min_date") or None, errors="coerce")
    max_date = pd.to_datetime(date_bounds.get("max_date") or None, errors="coerce")
    if pd.isna(min_date) or pd.isna(max_date):
        return {0: ""}

    max_index = int((max_date - min_date).days)
    marks: dict[int, str] = {0: min_date.strftime("%d %b %Y")}
    for month_start in pd.date_range(min_date.to_period("M").to_timestamp(), max_date, freq="MS"):
        if month_start <= min_date:
            continue
        index = int((month_start - min_date).days)
        if 0 < index < max_index:
            marks[index] = month_start.strftime("%b %Y")
    marks[max_index] = max_date.strftime("%d %b %Y")
    return marks


def _sorted_unique(records: list[dict[str, Any]], field: str) -> list[str]:
    values = {str(record.get(field, "")).strip() for record in records}
    values.discard("")
    return sorted(values)


def discover_filter_options(records: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    return {
        "publisher": [{"label": v, "value": v} for v in _sorted_unique(records, "Publisher")],
        "topic_area": [{"label": v, "value": v} for v in _sorted_unique(records, "Topic_Area")],
        "narrative": [{"label": v, "value": v} for v in _sorted_unique(records, "Narrative")],
    }


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_discover_records(
    records: list[dict[str, Any]],
    *,
    source_filter: list[str] | str | None,
    sentiment_filter: list[str] | str | None,
    publisher_filter: list[str] | str | None,
    topic_area_filter: list[str] | str | None,
    narrative_filter: list[str] | str | None,
    date_range: list[int] | None,
    search_text: str | None,
    search_fulltext: bool = False,
    selected_ids: list[Any] | set[Any] | None = None,
    reference_record: dict[str, Any] | None = None,
    similarity_radius: float | None = None,
) -> list[dict[str, Any]]:
    sources = set(_filter_trad_some(source_filter))
    sentiments = set(sentiment_filter or [])
    publishers = set(publisher_filter or [])
    topic_areas = set(topic_area_filter or [])
    narratives = set(narrative_filter or [])
    selected_id_set = set(selected_ids) if selected_ids else None
    search = (search_text or "").strip().lower()
    search_field = "_search_fulltext" if search_fulltext else "_search"

    if date_range and len(date_range) == 2:
        date_lo, date_hi = int(date_range[0]), int(date_range[1])
    else:
        date_lo, date_hi = None, None

    ref_point = _umap_point(reference_record) if reference_record else None
    use_similarity = ref_point is not None and similarity_radius is not None and similarity_radius > 0

    filtered = []
    for record in records:
        if sources and record.get("Source") not in sources:
            continue
        if sentiments and record.get("Sentiment") not in sentiments:
            continue
        if publishers and record.get("Publisher") not in publishers:
            continue
        if topic_areas and record.get("Topic_Area") not in topic_areas:
            continue
        if narratives and record.get("Narrative") not in narratives:
            continue
        if date_lo is not None:
            index = int(record.get("_date_index", 0))
            if index < date_lo or index > date_hi:
                continue
        if search and search not in str(record.get(search_field, "")):
            continue
        if selected_id_set is not None and record.get("_id") not in selected_id_set:
            continue
        if use_similarity:
            pt = _umap_point(record)
            if pt is None:
                continue
            x0, y0 = ref_point
            x, y = pt
            if ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5 > similarity_radius:
                continue
        filtered.append(record)
    return filtered


# ---------------------------------------------------------------------------
# Table data mapping
# ---------------------------------------------------------------------------


def discover_trad_table_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "_id": record.get("_id"),
            "Date": record.get("Date", ""),
            "Media_Type": record.get("Media_Type", ""),
            "Publication": record.get("Publisher", ""),
            "Title": record.get("Title", ""),
            "Summary": record.get("Summary", ""),
            "URL": f"[Open]({record['URL']})" if record.get("URL") else "",
            "Sentiment": record.get("Sentiment", ""),
            "Reach": record.get("Reach", 0),
        }
        for record in records
        if record.get("Source") == "Trad"
    ]


def discover_some_table_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "_id": record.get("_id"),
            "Date": record.get("Date", ""),
            "Platform": record.get("Media_Type", ""),
            "Author": record.get("Publisher", ""),
            "Post_Content": record.get("Title", ""),
            "URL": f"[Open]({record['URL']})" if record.get("URL") else "",
            "Sentiment": record.get("Sentiment", ""),
            "Reach": record.get("Reach", 0),
            "Engagement": record.get("Engagement", 0),
        }
        for record in records
        if record.get("Source") == "SoMe"
    ]


# ---------------------------------------------------------------------------
# UI builders
# ---------------------------------------------------------------------------


def _control(label: str, dropdown_id: str, options: list[dict[str, str]]) -> html.Div:
    return html.Div(
        className="amazon-publishers-control",
        children=[
            html.Div(label, className="amazon-publishers-control-label"),
            dcc.Dropdown(
                id=dropdown_id,
                options=options,
                value=[],
                multi=True,
                searchable=True,
                placeholder="All",
                className="amazon-publishers-dropdown",
            ),
        ],
    )


def build_discover_filters_panel(
    records: list[dict[str, Any]],
    date_bounds: dict[str, Any],
    options: dict[str, list[dict[str, str]]],
) -> html.Div:
    max_index = int(date_bounds.get("max_index", 0))
    marks = discover_date_marks(date_bounds)
    return na_panel(
        ref_label("Filters", "P8S1"),
        [
            html.Div(
                className="amazon-discover-search-row",
                children=[
                    html.Div(
                        className="amazon-discover-search-col",
                        children=[
                            html.Div("Search", className="amazon-publishers-control-label"),
                            dcc.Input(
                                id="amazon-2026-discover-search",
                                type="text",
                                placeholder="Search author, publisher, title, or text...",
                                debounce=True,
                                className="amazon-discover-search",
                            ),
                            dcc.Checklist(
                                id="amazon-2026-discover-search-fulltext",
                                options=[{"label": "Search full text", "value": "fulltext"}],
                                value=[],
                                className="amazon-discover-search-fulltext",
                            ),
                        ],
                    ),
                    html.Div(
                        className="amazon-discover-reference-col",
                        children=[
                            html.Div("Reference Publication", className="amazon-publishers-control-label"),
                            html.Div(
                                id="amazon-2026-discover-reference-box",
                                className="amazon-discover-reference-box",
                                children=[
                                    html.Div(
                                        id="amazon-2026-discover-reference-content",
                                        className="amazon-discover-reference-content",
                                        children=discover_reference_placeholder(),
                                    ),
                                    html.Button(
                                        html.Span("close", className="material-symbols-outlined"),
                                        id="amazon-2026-discover-reference-clear",
                                        className="amazon-discover-reference-clear",
                                        n_clicks=0,
                                        type="button",
                                        title="Clear reference",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="amazon-discover-similarity-row",
                                children=[
                                    html.Div("Similarity", className="amazon-publishers-control-label"),
                                    dcc.Slider(
                                        id="amazon-2026-discover-similarity-slider",
                                        min=0,
                                        max=10,
                                        step=1,
                                        value=5,
                                        marks={0: "Close", 10: "Far"},
                                        tooltip=None,
                                        className="amazon-discover-similarity-slider",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="amazon-discover-controls",
                children=[
                    _control("Source", "amazon-2026-discover-source-filter", TRAD_SOME_OPTIONS),
                    _control("Sentiment", "amazon-2026-discover-sentiment-filter", SENTIMENT_OPTIONS),
                    _control("Publisher", "amazon-2026-discover-publisher-filter", options["publisher"]),
                    _control("Topic Area", "amazon-2026-discover-topicarea-filter", options["topic_area"]),
                    _control("Narrative", "amazon-2026-discover-narrative-filter", options["narrative"]),
                ],
            ),
            html.Div(
                className="amazon-discover-date-row",
                children=[
                    html.Div("Date Range", className="amazon-publishers-control-label"),
                    html.Div(id="amazon-2026-discover-date-label", className="amazon-discover-date-label"),
                    dcc.RangeSlider(
                        id="amazon-2026-discover-date-range",
                        min=0,
                        max=max_index,
                        step=1,
                        value=[0, max_index],
                        marks=marks,
                        allowCross=False,
                        className="amazon-discover-rangeslider",
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Reference article (UMAP similarity anchor)
# ---------------------------------------------------------------------------


def discover_reference_placeholder() -> html.Div:
    return html.Div(
        "No reference article selected.",
        className="amazon-discover-reference-empty",
    )


def discover_short_date(date_value: Any) -> str:
    parsed = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(parsed):
        return str(date_value or "")
    return parsed.strftime("%d %b %Y")


def build_discover_reference_content(record: dict[str, Any] | None) -> html.Div:
    if not record:
        return discover_reference_placeholder()
    return html.Div(
        className="amazon-discover-reference-item",
        children=[
            html.Span(discover_short_date(record.get("Date")), className="amazon-discover-reference-date"),
            html.Span(record.get("Publisher") or "Unknown", className="amazon-discover-reference-publisher"),
            html.Span(record.get("Title") or "(untitled)", className="amazon-discover-reference-title"),
        ],
    )


# ---------------------------------------------------------------------------
# Narrative clusters (UMAP)
# ---------------------------------------------------------------------------


def discover_cluster_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for record in records:
        x, y = record.get("umap_x"), record.get("umap_y")
        if x in (None, "") or y in (None, ""):
            continue
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "_id": record.get("_id"),
                "umap_x": x,
                "umap_y": y,
                "narrative_label": record.get("Narrative") or "",
                "source": record.get("Source") or "",
                "_date_index": record.get("_date_index") or 0,
            }
        )
    return out


def discover_color_map(records: list[dict[str, Any]]) -> dict[str, str]:
    cluster_records = discover_cluster_records(records)
    df = pd.DataFrame(cluster_records)
    return _build_color_map(df) if not df.empty else {}


def build_discover_stores_section(
    records: list[dict[str, Any]],
    date_bounds: dict[str, Any],
    color_map: dict[str, str],
) -> html.Div:
    """Hidden panel holding all dcc.Stores for the Discover page.

    Isolating stores here prevents the visible filter/clusters panels from
    showing a loading overlay when callbacks write to these stores (e.g.
    writing to detail-id on row click no longer flashes the filter panel).
    """
    return html.Div(
        style={"display": "none"},
        children=[
            dcc.Store(id="amazon-2026-discover-data", data=records),
            dcc.Store(id="amazon-2026-discover-bounds", data=date_bounds),
            dcc.Store(id="amazon-2026-discover-detail-id", data=None),
            dcc.Store(id="amazon-2026-discover-reference-data", data=None),
            dcc.Store(id="amazon-2026-discover-selected-ids", data=None),
            dcc.Store(id="amazon-2026-discover-clusters-selections", data=None),
            dcc.Store(id="amazon-2026-discover-clusters-colormap", data=color_map),
            dcc.Store(id="amazon-2026-discover-trad-base-style", data=TOP_PUBLICATIONS_STYLE_DATA_CONDITIONAL),
            dcc.Store(id="amazon-2026-discover-some-base-style", data=TOP_POSTS_STYLE_DATA_CONDITIONAL),
        ],
    )


def build_discover_clusters_section(records: list[dict[str, Any]]) -> html.Div:
    cluster_records = discover_cluster_records(records)
    df = pd.DataFrame(cluster_records)
    color_map = _build_color_map(df) if not df.empty else {}
    initial_fig = _archive_figure(cluster_records, color_map, color_on=True, show_kde=False)

    return na_panel(
        ref_label("Narrative Clusters (UMAP)", "P8S2G1"),
        [
            html.Div(
                className="amazon-publishers-chart-controls",
                children=[
                    dcc.Checklist(
                        id="amazon-2026-discover-clusters-color-toggle",
                        options=[{"label": "Color by narrative", "value": "color"}],
                        value=["color"],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                    dcc.Checklist(
                        id="amazon-2026-discover-clusters-kde-toggle",
                        options=[{"label": "KDE", "value": "kde"}],
                        value=[],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                    dcc.Checklist(
                        id="amazon-2026-discover-clusters-time-toggle",
                        options=[{"label": "Color by time", "value": "time"}],
                        value=[],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                    dcc.Checklist(
                        id="amazon-2026-discover-clusters-relative-toggle",
                        options=[{"label": "Relative to selected range", "value": "relative"}],
                        value=[],
                        inline=True,
                        className="amazon-publishers-radio",
                        style={"display": "none"},
                    ),
                    html.Div(
                        id="amazon-2026-discover-time-legend",
                        className="amazon-discover-time-legend",
                        style={"display": "none"},
                        children=[
                            html.Span("Older"),
                            html.Div(className="amazon-discover-time-legend-bar"),
                            html.Span("Newer"),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="amazon-2026-discover-selection-banner",
                className="amazon-discover-selection-banner",
                style={"display": "none"},
                children=[
                    html.Span(id="amazon-2026-discover-selection-text"),
                    html.Button(
                        [html.Span("close", className="material-symbols-outlined"), "Clear selection"],
                        id="amazon-2026-discover-selection-clear",
                        className="amazon-discover-selection-clear",
                        n_clicks=0,
                    ),
                ],
            ),
            html.Div(
                "Tip: use the lasso or box-select tool in the chart toolbar above to pick points and "
                "filter the results table to that selection.",
                className="amazon-discover-selection-hint",
            ),
            dcc.Graph(
                id="amazon-2026-discover-clusters-graph",
                figure=initial_fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "responsive": True,
                    "toImageButtonOptions": {"format": "svg", "filename": "amazon_2026_discover_umap"},
                },
                style={"height": "800px"},
            ),
        ],
    )


def build_discover_results_panel(trad_table_data: list[dict[str, Any]], some_table_data: list[dict[str, Any]]) -> html.Div:
    has_trad = bool(trad_table_data)
    has_some = bool(some_table_data)
    available_sources = (["Trad"] if has_trad else []) + (["SoMe"] if has_some else [])
    default_source = available_sources[0] if available_sources else "Trad"
    options = [
        {"label": opt["label"], "value": opt["value"], "disabled": opt["value"] not in available_sources}
        for opt in TRAD_SOME_OPTIONS
    ]
    controls = html.Div(
        id="amazon-2026-discover-source-controls",
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if len(available_sources) <= 1 else None,
        children=[
            dcc.RadioItems(
                id="amazon-2026-discover-top-items-source",
                options=options,
                value=default_source,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )
    # Both tables are always in the DOM; visibility is toggled by wrappers.
    # This avoids remounting the DataTable on filter changes, which would
    # reset active_cell and lose row selection.
    trad_visible = default_source == "Trad"
    trad_table = build_top_publications_table(
        "amazon-2026-discover-top-publications", trad_table_data, show_publication_col=True
    )
    some_table = build_top_posts_table(
        "amazon-2026-discover-top-posts", some_table_data, show_author_col=True
    )
    return na_panel(
        ref_label("Results", "P8S3"),
        [
            html.Div(id="amazon-2026-discover-results-count", className="amazon-discover-results-count"),
            controls,
            html.Div(
                id="amazon-2026-discover-trad-table-wrapper",
                style=None if trad_visible else {"display": "none"},
                children=trad_table,
            ),
            html.Div(
                id="amazon-2026-discover-some-table-wrapper",
                style={"display": "none"} if trad_visible else None,
                children=some_table,
            ),
        ],
    )


def discover_results_count_label(trad_table_data: list[dict[str, Any]], some_table_data: list[dict[str, Any]]) -> str:
    total = len(trad_table_data) + len(some_table_data)
    if total == 0:
        return "No items match the current filters."
    if total == 1:
        return "1 item matches the current filters."
    return f"{total} items match the current filters ({len(trad_table_data)} Trad, {len(some_table_data)} SoMe)."


def discover_trad_tooltip_data(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"Summary": {"value": str(row.get("Summary", "")), "type": "text"}} for row in table_data]


def discover_some_tooltip_data(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"Post_Content": {"value": str(row.get("Post_Content", "")), "type": "text"}} for row in table_data]


# ---------------------------------------------------------------------------
# Publication details panel
# ---------------------------------------------------------------------------


def discover_detail_placeholder() -> html.Div:
    return html.Div(
        "Click a row in the results table above to see publication details.",
        className="amazon-publishers-empty",
    )


def find_discover_record(records: list[dict[str, Any]], record_id: Any) -> dict[str, Any] | None:
    if record_id is None:
        return None
    for record in records:
        if record.get("_id") == record_id:
            return record
    return None


# ---------------------------------------------------------------------------
# Similar articles (UMAP nearest neighbours)
# ---------------------------------------------------------------------------

SIMILAR_ITEMS_LIMIT = 10


def _umap_point(record: dict[str, Any]) -> tuple[float, float] | None:
    x, y = record.get("umap_x"), record.get("umap_y")
    if x in (None, "") or y in (None, ""):
        return None
    try:
        return float(x), float(y)
    except (TypeError, ValueError):
        return None


def find_similar_discover_records(
    records: list[dict[str, Any]],
    record: dict[str, Any] | None,
    limit: int = SIMILAR_ITEMS_LIMIT,
) -> list[dict[str, Any]]:
    if not record:
        return []
    origin = _umap_point(record)
    if origin is None:
        return []
    x0, y0 = origin

    candidates: list[tuple[float, dict[str, Any]]] = []
    for other in records:
        if other.get("_id") == record.get("_id"):
            continue
        point = _umap_point(other)
        if point is None:
            continue
        x, y = point
        distance = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
        candidates.append((distance, other))

    candidates.sort(key=lambda item: item[0])
    return [other for _, other in candidates[:limit]]


def discover_similar_table_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "_id": record.get("_id"),
            "Source": record.get("Source", ""),
            "Date": record.get("Date", ""),
            "Publisher": record.get("Publisher", ""),
            "Title": record.get("Title", ""),
            "URL": f"[Open]({record['URL']})" if record.get("URL") else "",
            "Sentiment": record.get("Sentiment", ""),
            "Reach": record.get("Reach", 0),
        }
        for record in records
    ]


_DONUT_GRAPH_HEIGHT = 160


def _discover_engagement_sentiment_donut(record: dict[str, Any]) -> html.Div | None:
    pos = _num(record, "Engagement_Positive")
    neg = _num(record, "Engagement_Negative")
    neu = _num(record, "Engagement_Neutral")
    slices = [("Positive", pos), ("Neutral", neu), ("Negative", neg)]
    slices = [(label, val) for label, val in slices if val > 0]
    if not slices:
        return None
    total = sum(v for _, v in slices)
    labels = [s[0] for s in slices]
    values = [s[1] for s in slices]
    colors = [SENTIMENT_COLORS[label] for label in labels]
    slice_text = [f"{label}<br>{val / total:.1%}" if total and (val / total) >= 0.03 else "" for label, val in slices]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            domain={"x": [0.2, 0.8], "y": [0.12, 0.88]},
            sort=False,
            direction="clockwise",
            marker={"colors": colors, "line": {"color": THEME_SURFACE, "width": 0.5}},
            text=slice_text,
            textinfo="text",
            textposition="outside",
            textfont={"color": THEME_TEXT, "size": 11},
            automargin=True,
            hovertemplate="%{label}: %{value:,.0f} (%{percent:.1%})<extra></extra>",
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
    return html.Div(
        className="amazon-publishers-mini-donut",
        style={"minHeight": f"{_DONUT_GRAPH_HEIGHT + 28}px"},
        children=[
            html.Div(
                className="amazon-publishers-mini-donut-header",
                children=[html.Div("Engagement by sentiment", className="amazon-publishers-mini-title")],
            ),
            dcc.Graph(
                figure=fig,
                responsive=True,
                config={"displayModeBar": False},
                className="amazon-publishers-mini-donut-graph",
                style={"width": "100%", "height": f"{_DONUT_GRAPH_HEIGHT}px", "minWidth": 0},
            ),
        ],
    )


def _discover_detail_kpis(record: dict[str, Any]) -> list[html.Div]:
    source = record.get("Source", "")
    cards = [_kpi_card("Platform" if source == "SoMe" else "Media Type", record.get("Media_Type") or "Unknown")]
    cards.append(_kpi_card("Sentiment", record.get("Sentiment") or "Neutral"))
    cards.append(_kpi_card("Reach", f"{_num(record, 'Reach'):,.0f}"))
    if source == "SoMe":
        cards.append(_kpi_card("Engagement", f"{_num(record, 'Engagement'):,.0f}"))
    return cards


def build_discover_detail_content(record: dict[str, Any] | None) -> html.Div:
    if not record:
        return discover_detail_placeholder()

    source = record.get("Source", "")
    title = record.get("Title") or "(untitled)"
    url = record.get("URL") or ""

    if source == "SoMe":
        body_children = _build_some_post_body(record, url)
    else:
        body_children = _build_trad_body(record, url)

    kpi_left_children: list[Any] = [
        html.Div(_discover_detail_kpis(record), className="amazon-discover-detail-kpis-cards"),
    ]
    if source == "SoMe":
        donut = _discover_engagement_sentiment_donut(record)
        if donut is not None:
            kpi_left_children.append(donut)

    children: list[Any] = [
        html.Div(
            className="amazon-discover-detail-grid",
            children=[
                html.Div(kpi_left_children, className="amazon-discover-detail-kpis"),
                html.Div(body_children, className="amazon-discover-detail-body"),
            ],
        )
    ]

    if source == "Trad":
        full_text = (record.get("Full_Text") or "").strip()
        summary = (record.get("Summary") or "").strip()
        if full_text and full_text != summary and full_text != title:
            children.append(
                html.Details(
                    className="amazon-discover-detail-fulltext",
                    children=[
                        html.Summary("Show full text"),
                        html.P(full_text),
                    ],
                )
            )

    return html.Div(children)


def _build_some_post_body(record: dict[str, Any], url: str) -> list[Any]:
    author = record.get("Publisher") or "Unknown"
    platform = record.get("Media_Type") or "Unknown"
    date = record.get("Date") or "—"
    followers = int(_num(record, "Followers"))
    title = record.get("Title") or "(no content)"

    tag_items = []
    if record.get("Topic_Area"):
        tag_items.append(
            html.Div(
                className="amazon-discover-some-post-tag",
                children=[
                    html.Span("Topic Area", className="amazon-publishers-kpi-label"),
                    html.Div(record["Topic_Area"], className="amazon-publishers-type"),
                ],
            )
        )
    if record.get("Narrative"):
        tag_items.append(
            html.Div(
                className="amazon-discover-some-post-tag",
                children=[
                    html.Span("Narrative", className="amazon-publishers-kpi-label"),
                    html.Div(record["Narrative"], className="amazon-publishers-type"),
                ],
            )
        )

    header = html.Div(
        className="amazon-discover-some-post-header",
        children=[
            html.Div(
                className="amazon-discover-some-post-author-block",
                children=[
                    html.Div(
                        children=[
                            html.Span(author, className="amazon-discover-some-post-author"),
                            html.Span(platform, className="amazon-publishers-type amazon-discover-some-post-platform"),
                        ],
                        className="amazon-discover-some-post-author-row",
                    ),
                    html.Div(
                        children=[
                            html.Span(date, className="amazon-discover-some-post-date"),
                            *(
                                [html.Span(f"{followers:,.0f} followers", className="amazon-discover-some-post-followers")]
                                if followers > 0
                                else []
                            ),
                        ],
                        className="amazon-discover-some-post-meta-row",
                    ),
                ],
            ),
        ],
    )

    body: list[Any] = [
        header,
        html.Div(title, className="amazon-discover-some-post-content"),
    ]
    if tag_items:
        body.append(html.Div(tag_items, className="amazon-discover-some-post-tags"))
    if url:
        body.append(
            html.A(
                "Open post",
                href=url,
                target="_blank",
                rel="noopener noreferrer",
                className="amazon-discover-some-post-link",
            )
        )
    return body


def _build_trad_body(record: dict[str, Any], url: str) -> list[Any]:
    title = record.get("Title") or "(untitled)"
    summary = (record.get("Summary") or "").strip() or "No summary available."
    publisher_label = "Publisher"

    meta_items = [
        ("Date", record.get("Date") or "—"),
        (publisher_label, record.get("Publisher") or "Unknown"),
    ]
    journalist = str(record.get("Journalist") or "").strip()
    if journalist:
        meta_items.append(("Journalist", journalist))
    if record.get("Topic_Area"):
        meta_items.append(("Topic Area", record["Topic_Area"]))
    if record.get("Narrative"):
        meta_items.append(("Narrative", record["Narrative"]))

    badges = [
        html.Div("Trad", className="amazon-publishers-type"),
        html.Div(record.get("Media_Type") or "Unknown", className="amazon-publishers-type"),
    ]

    children: list[Any] = [
        html.Div(badges, className="amazon-publishers-badge-row"),
        html.H3(title),
        html.Div(html.P(summary), className="amazon-publishers-profile-summary"),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(label, className="amazon-publishers-kpi-label"),
                        html.Div(str(value), className="amazon-discover-detail-meta-value"),
                    ],
                    className="amazon-discover-detail-meta-item",
                )
                for label, value in meta_items
            ],
            className="amazon-discover-detail-meta",
        ),
    ]
    if url:
        children.append(
            html.Div(
                className="amazon-publishers-links",
                children=[
                    html.Div("Source", className="amazon-publishers-links-title"),
                    html.Div(
                        className="amazon-publishers-link-list",
                        children=[html.A("Open original", href=url, target="_blank", rel="noopener noreferrer")],
                    ),
                ],
            )
        )
    return children


def build_discover_detail_section() -> html.Div:
    return na_panel(
        ref_label("Publication Details", "P8S4"),
        [html.Div(id="amazon-2026-discover-detail-content", children=discover_detail_placeholder())],
        controls=html.Button(
            [html.Span("bookmark_add", className="material-symbols-outlined"), "Use as reference"],
            id="amazon-2026-discover-use-as-reference-btn",
            className="amazon-discover-reference-btn",
            n_clicks=0,
            type="button",
        ),
    )
