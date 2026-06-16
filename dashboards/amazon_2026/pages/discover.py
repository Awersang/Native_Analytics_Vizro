"""Discover page."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, clientside_callback, ctx, no_update
from vizro.models.types import capture

from dashboards.amazon_2026.charts_archive import _archive_figure, umap_distance_bounds
from dashboards.amazon_2026.charts_discover import (
    _server_discover_data,
    build_discover_clusters_section,
    build_discover_detail_content,
    build_discover_detail_section,
    build_discover_filters_panel,
    build_discover_reference_content,
    build_discover_results_panel,
    build_discover_stores_section,
    discover_cluster_records,
    discover_date_bounds,
    discover_filter_options,
    discover_reference_placeholder,
    discover_results_count_label,
    discover_some_tooltip_data,
    discover_split_table_data,
    discover_trad_tooltip_data,
    filter_discover_records,
    find_discover_record,
)
from dashboards.amazon_2026.charts_shared import TRAD_SOME_OPTIONS
from dashboards.amazon_2026.data_common import DISCOVER_ITEMS_KEY
from dashboards.amazon_2026.dev_ids import ref_label


def build_discover_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-discover",
        title=ref_label("Discover", "P8"),
        path=f"{base_path}/discover",
        description="Explore and search across the dataset.",
        components=[
            vm.Figure(
                id="amazon-2026-discover-stores-section",
                figure=discover_stores_panel(data_frame=DISCOVER_ITEMS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-discover-filters-section",
                figure=discover_filters_panel(data_frame=DISCOVER_ITEMS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-discover-clusters-section",
                figure=discover_clusters_panel(data_frame=DISCOVER_ITEMS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-discover-results-section",
                figure=discover_results_panel(data_frame=DISCOVER_ITEMS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-discover-detail-section",
                figure=discover_detail_panel(data_frame=pd.DataFrame()),
            ),
        ],
        layout=vm.Flex(direction="column", gap="20px"),
    )


@capture("figure")
def discover_stores_panel(data_frame: pd.DataFrame):
    records, _, color_map = _server_discover_data()
    bounds = discover_date_bounds(records)
    return build_discover_stores_section(bounds, color_map)


@capture("figure")
def discover_filters_panel(data_frame: pd.DataFrame):
    records, _, _ = _server_discover_data()
    bounds = discover_date_bounds(records)
    options = discover_filter_options(records)
    return build_discover_filters_panel(records, bounds, options)


@capture("figure")
def discover_clusters_panel(data_frame: pd.DataFrame):
    _, cluster_records, color_map = _server_discover_data()
    return build_discover_clusters_section(cluster_records, color_map)


@capture("figure")
def discover_results_panel(data_frame: pd.DataFrame):
    records, _, _ = _server_discover_data()
    trad_data, some_data = discover_split_table_data(records)
    return build_discover_results_panel(trad_data, some_data)


@capture("figure")
def discover_detail_panel(data_frame: pd.DataFrame):
    return build_discover_detail_section()


@callback(
    Output("amazon-2026-discover-trad-table-wrapper", "style"),
    Output("amazon-2026-discover-top-publications", "data"),
    Output("amazon-2026-discover-top-publications", "tooltip_data"),
    Output("amazon-2026-discover-top-publications", "active_cell"),
    Output("amazon-2026-discover-some-table-wrapper", "style"),
    Output("amazon-2026-discover-top-posts", "data"),
    Output("amazon-2026-discover-top-posts", "tooltip_data"),
    Output("amazon-2026-discover-top-posts", "active_cell"),
    Output("amazon-2026-discover-top-items-source", "value"),
    Output("amazon-2026-discover-top-items-source", "options"),
    Output("amazon-2026-discover-source-controls", "style"),
    Output("amazon-2026-discover-results-count", "children"),
    Input("amazon-2026-discover-source-filter", "value"),
    Input("amazon-2026-discover-sentiment-filter", "value"),
    Input("amazon-2026-discover-publisher-filter", "value"),
    Input("amazon-2026-discover-topicarea-filter", "value"),
    Input("amazon-2026-discover-narrative-filter", "value"),
    Input("amazon-2026-discover-date-range", "value"),
    Input("amazon-2026-discover-search", "value"),
    Input("amazon-2026-discover-search-fulltext", "value"),
    Input("amazon-2026-discover-top-items-source", "value"),
    Input("amazon-2026-discover-selected-ids", "data"),
    Input("amazon-2026-discover-reference-data", "data"),
    Input("amazon-2026-discover-similarity-slider", "value"),
    prevent_initial_call=True,
)
def _update_discover_results(
    source_filter: list[str] | None,
    sentiment_filter: list[str] | None,
    publisher_filter: list[str] | None,
    topic_area_filter: list[str] | None,
    narrative_filter: list[str] | None,
    date_range: list[int] | None,
    search_text: str | None,
    search_fulltext: list[str] | None,
    active_source: str | None,
    selected_ids: list[Any] | None,
    reference_data: dict[str, Any] | None,
    similarity_value: int | None,
):
    records, cluster_records, _ = _server_discover_data()
    similarity_radius = None
    if reference_data:
        diagonal = umap_distance_bounds(cluster_records)
        similarity_radius = (float(similarity_value or 0) / 100.0) * diagonal

    filtered = filter_discover_records(
        records,
        source_filter=source_filter,
        sentiment_filter=sentiment_filter,
        publisher_filter=publisher_filter,
        topic_area_filter=topic_area_filter,
        narrative_filter=narrative_filter,
        date_range=date_range,
        search_text=search_text,
        search_fulltext=bool(search_fulltext),
        selected_ids=selected_ids,
        reference_record=reference_data,
        similarity_radius=similarity_radius,
    )
    trad_data, some_data = discover_split_table_data(filtered)
    available_sources = (["Trad"] if trad_data else []) + (["SoMe"] if some_data else [])

    if active_source in available_sources:
        selected = active_source
    elif available_sources:
        selected = available_sources[0]
    else:
        selected = active_source or "Trad"

    options = [
        {"label": opt["label"], "value": opt["value"], "disabled": opt["value"] not in available_sources}
        for opt in TRAD_SOME_OPTIONS
    ]
    wrap_style = {"display": "none"} if len(available_sources) <= 1 else None
    trad_style = None if selected == "Trad" else {"display": "none"}
    some_style = None if selected == "SoMe" else {"display": "none"}

    return (
        trad_style,
        trad_data,
        discover_trad_tooltip_data(trad_data),
        None,  # reset active_cell so stale row highlight clears
        some_style,
        some_data,
        discover_some_tooltip_data(some_data),
        None,  # reset active_cell so stale row highlight clears
        selected,
        options,
        wrap_style,
        discover_results_count_label(trad_data, some_data),
    )


clientside_callback(
    """
    function(color_value, time_value) {
        var ctx = dash_clientside.callback_context;
        if (!ctx.triggered || !ctx.triggered.length) {
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        var triggered_id = ctx.triggered[0].prop_id.split('.')[0];
        if (triggered_id === 'amazon-2026-discover-clusters-color-toggle'
                && color_value && color_value.length > 0) {
            return [color_value, []];
        }
        if (triggered_id === 'amazon-2026-discover-clusters-time-toggle'
                && time_value && time_value.length > 0) {
            return [[], time_value];
        }
        return [window.dash_clientside.no_update, window.dash_clientside.no_update];
    }
    """,
    Output("amazon-2026-discover-clusters-color-toggle", "value"),
    Output("amazon-2026-discover-clusters-time-toggle", "value"),
    Input("amazon-2026-discover-clusters-color-toggle", "value"),
    Input("amazon-2026-discover-clusters-time-toggle", "value"),
    prevent_initial_call=True,
)


@callback(
    Output("amazon-2026-discover-clusters-graph", "figure"),
    Output("amazon-2026-discover-time-legend", "style"),
    Output("amazon-2026-discover-clusters-relative-toggle", "style"),
    Input("amazon-2026-discover-source-filter", "value"),
    Input("amazon-2026-discover-sentiment-filter", "value"),
    Input("amazon-2026-discover-publisher-filter", "value"),
    Input("amazon-2026-discover-topicarea-filter", "value"),
    Input("amazon-2026-discover-narrative-filter", "value"),
    Input("amazon-2026-discover-date-range", "value"),
    Input("amazon-2026-discover-search", "value"),
    Input("amazon-2026-discover-search-fulltext", "value"),
    Input("amazon-2026-discover-clusters-color-toggle", "value"),
    Input("amazon-2026-discover-clusters-kde-toggle", "value"),
    Input("amazon-2026-discover-clusters-time-toggle", "value"),
    Input("amazon-2026-discover-clusters-relative-toggle", "value"),
    Input("amazon-2026-discover-selection-clear", "n_clicks"),
    Input("amazon-2026-discover-reference-data", "data"),
    Input("amazon-2026-discover-similarity-slider", "value"),
    State("amazon-2026-discover-clusters-colormap", "data"),
    State("amazon-2026-discover-bounds", "data"),
    State("amazon-2026-discover-clusters-selections", "data"),
    prevent_initial_call=True,
)
def _update_discover_clusters(
    source_filter: list[str] | None,
    sentiment_filter: list[str] | None,
    publisher_filter: list[str] | None,
    topic_area_filter: list[str] | None,
    narrative_filter: list[str] | None,
    date_range: list[int] | None,
    search_text: str | None,
    search_fulltext: list[str] | None,
    color_value: list[str] | None,
    kde_value: list[str] | None,
    time_value: list[str] | None,
    relative_value: list[str] | None,
    _clear_clicks: int | None,
    reference_data: dict[str, Any] | None,
    similarity_value: int | None,
    color_map: dict[str, str] | None,
    date_bounds: dict[str, Any] | None,
    selections: list[dict[str, Any]] | None,
):
    records, full_cluster_records, _ = _server_discover_data()
    filtered = filter_discover_records(
        records,
        source_filter=source_filter,
        sentiment_filter=sentiment_filter,
        publisher_filter=publisher_filter,
        topic_area_filter=topic_area_filter,
        narrative_filter=narrative_filter,
        date_range=date_range,
        search_text=search_text,
        search_fulltext=bool(search_fulltext),
    )
    cluster_records = discover_cluster_records(filtered)
    color_on = "color" in (color_value or [])
    show_kde = "kde" in (kde_value or [])
    time_on = "time" in (time_value or [])
    relative_on = "relative" in (relative_value or [])
    legend_style = None if time_on else {"display": "none"}
    relative_style = None if time_on else {"display": "none"}

    date_bounds = dict(date_bounds or {})
    date_bounds.setdefault("min_index", 0)
    if time_on and relative_on and date_range and len(date_range) == 2:
        min_date = pd.Timestamp(date_bounds.get("min_date"))
        date_bounds["min_index"] = int(date_range[0])
        date_bounds["max_index"] = int(date_range[1])
        date_bounds["min_date"] = (min_date + pd.Timedelta(days=int(date_range[0]))).date().isoformat()
        date_bounds["max_date"] = (min_date + pd.Timedelta(days=int(date_range[1]))).date().isoformat()

    ref_point = None
    ref_radius = None
    if reference_data:
        rx, ry = reference_data.get("umap_x"), reference_data.get("umap_y")
        if rx is not None and ry is not None:
            try:
                ref_point = (float(rx), float(ry))
                diagonal = umap_distance_bounds(full_cluster_records)
                ref_radius = (float(similarity_value or 0) / 100.0) * diagonal
            except (TypeError, ValueError):
                ref_point = None

    fig = _archive_figure(
        cluster_records, color_map or {}, color_on, show_kde, time_on, date_bounds,
        reference_point=ref_point, reference_radius=ref_radius,
    )
    if ctx.triggered_id != "amazon-2026-discover-selection-clear" and selections:
        fig.update_layout(selections=selections)
    return fig, legend_style, relative_style


@callback(
    Output("amazon-2026-discover-selected-ids", "data"),
    Output("amazon-2026-discover-selection-banner", "style"),
    Output("amazon-2026-discover-selection-text", "children"),
    Input("amazon-2026-discover-clusters-graph", "selectedData"),
    Input("amazon-2026-discover-selection-clear", "n_clicks"),
    prevent_initial_call=True,
)
def _update_discover_selection(selected_data: dict[str, Any] | None, _clear_clicks: int | None):
    if ctx.triggered_id == "amazon-2026-discover-selection-clear":
        return None, {"display": "none"}, ""

    points = (selected_data or {}).get("points") or []
    ids = [point["customdata"][0] for point in points if point.get("customdata")]
    if not ids:
        # A figure rebuild (e.g. from a filter change) re-applies the stored
        # selection shape and fires selectedData=None before the points
        # repopulate — ignore it so the selection survives the redraw.
        return no_update, no_update, no_update

    count = len(ids)
    text = (
        f"{count} point{'s' if count != 1 else ''} selected on the chart — "
        "results table filtered to this selection."
    )
    return ids, None, text


@callback(
    Output("amazon-2026-discover-clusters-selections", "data"),
    Input("amazon-2026-discover-clusters-graph", "relayoutData"),
    Input("amazon-2026-discover-selection-clear", "n_clicks"),
    prevent_initial_call=True,
)
def _update_discover_clusters_selections(relayout_data: dict[str, Any] | None, _clear_clicks: int | None):
    if ctx.triggered_id == "amazon-2026-discover-selection-clear":
        return None

    selections = _selections_from_relayout(relayout_data)
    if not selections:
        # A redraw-triggered relayout (or the user clicking empty space)
        # reports no/empty selection shapes — keep the previously stored shape.
        return no_update

    return selections


_SELECTION_KEY_RE = re.compile(r"^selections\[(\d+)\]\.(.+)$")


def _selections_from_relayout(relayout_data: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not relayout_data:
        return None
    if "selections" in relayout_data:
        return relayout_data["selections"] or None

    # plotly_relayout often reports new shapes as flattened keys, e.g.
    # "selections[0].x0", "selections[0].x1", ...
    entries: dict[int, dict[str, Any]] = {}
    for key, value in relayout_data.items():
        match = _SELECTION_KEY_RE.match(key)
        if not match:
            continue
        index, attr = int(match.group(1)), match.group(2)
        entries.setdefault(index, {})[attr] = value
    if not entries:
        return None
    return [entries[index] for index in sorted(entries)]


def _discover_detail_from_active_cell(
    active_cell: dict[str, Any] | None,
    rows: list[dict[str, Any]] | None,
    records: list[dict[str, Any]] | None,
):
    if not active_cell or active_cell.get("column_id") == "URL":
        return no_update, no_update

    row_index = active_cell.get("row")
    rows = rows or []
    if row_index is None or row_index >= len(rows):
        return no_update, no_update

    record = find_discover_record(records or [], rows[row_index].get("_id"))
    return build_discover_detail_content(record), record.get("_id") if record else None


@callback(
    Output("amazon-2026-discover-detail-content", "children", allow_duplicate=True),
    Output("amazon-2026-discover-detail-id", "data", allow_duplicate=True),
    Input("amazon-2026-discover-top-publications", "active_cell"),
    State("amazon-2026-discover-top-publications", "derived_viewport_data"),
    prevent_initial_call=True,
)
def _update_discover_detail_trad(
    active_cell: dict[str, Any] | None,
    rows: list[dict[str, Any]] | None,
):
    records, _, _ = _server_discover_data()
    return _discover_detail_from_active_cell(active_cell, rows, records)


@callback(
    Output("amazon-2026-discover-detail-content", "children", allow_duplicate=True),
    Output("amazon-2026-discover-detail-id", "data", allow_duplicate=True),
    Input("amazon-2026-discover-top-posts", "active_cell"),
    State("amazon-2026-discover-top-posts", "derived_viewport_data"),
    prevent_initial_call=True,
)
def _update_discover_detail_some(
    active_cell: dict[str, Any] | None,
    rows: list[dict[str, Any]] | None,
):
    records, _, _ = _server_discover_data()
    return _discover_detail_from_active_cell(active_cell, rows, records)


@callback(
    Output("amazon-2026-discover-reference-data", "data"),
    Output("amazon-2026-discover-reference-content", "children"),
    Input("amazon-2026-discover-use-as-reference-btn", "n_clicks"),
    Input("amazon-2026-discover-reference-clear", "n_clicks"),
    State("amazon-2026-discover-detail-id", "data"),
    prevent_initial_call=True,
)
def _update_discover_reference(
    use_clicks: int | None,
    clear_clicks: int | None,
    detail_id: Any,
):
    if ctx.triggered_id == "amazon-2026-discover-reference-clear":
        return None, discover_reference_placeholder()

    records, _, _ = _server_discover_data()
    record = find_discover_record(records, detail_id)
    if not record:
        return no_update, no_update
    return record, build_discover_reference_content(record)


clientside_callback(
    """
    function(active_cell, _data) {
        return [];
    }
    """,
    Output("amazon-2026-discover-top-publications", "selected_cells"),
    Input("amazon-2026-discover-top-publications", "active_cell"),
    Input("amazon-2026-discover-top-publications", "data"),
    prevent_initial_call=True,
)

clientside_callback(
    """
    function(active_cell, _data) {
        return [];
    }
    """,
    Output("amazon-2026-discover-top-posts", "selected_cells"),
    Input("amazon-2026-discover-top-posts", "active_cell"),
    Input("amazon-2026-discover-top-posts", "data"),
    prevent_initial_call=True,
)


clientside_callback(
    """
    function(date_range, bounds) {
        if (!date_range || !bounds || !bounds.min_date) return '';
        var min_ts = new Date(bounds.min_date).getTime();
        function fmtDate(ts) {
            var d = new Date(ts);
            var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            var day = String(d.getUTCDate()).padStart(2, '0');
            return day + ' ' + months[d.getUTCMonth()] + ' ' + d.getUTCFullYear();
        }
        return fmtDate(min_ts + date_range[0] * 86400000) + ' to ' + fmtDate(min_ts + date_range[1] * 86400000);
    }
    """,
    Output("amazon-2026-discover-date-label", "children"),
    Input("amazon-2026-discover-date-range", "value"),
    State("amazon-2026-discover-bounds", "data"),
)

clientside_callback(
    """
    function(n_clicks, is_open) {
        var new_open = !is_open;
        if (new_open) {
            setTimeout(function() {
                var el = document.getElementById('amazon-2026-discover-clusters-graph');
                if (el && window.Plotly) window.Plotly.Plots.resize(el);
            }, 50);
        }
        return [new_open, new_open ? null : {"display": "none"}, new_open ? "Hide" : "Show"];
    }
    """,
    Output("amazon-2026-discover-umap-open", "data"),
    Output("amazon-2026-discover-umap-container", "style"),
    Output("amazon-2026-discover-umap-toggle", "children"),
    Input("amazon-2026-discover-umap-toggle", "n_clicks"),
    State("amazon-2026-discover-umap-open", "data"),
    prevent_initial_call=True,
)
