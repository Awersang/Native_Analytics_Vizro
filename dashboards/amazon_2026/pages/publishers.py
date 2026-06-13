"""Publishers page — thin wiring layer. All components live in charts_publishers."""
from __future__ import annotations

from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, html, no_update
from vizro.managers import data_manager
from vizro.models.types import capture

from dashboards.amazon_2026.charts_publishers import (
    _data_bar_styles,
    _detail_metric_values,
    _details_content,
    _filter_records,
    _header_divider_styles,
    _kpi_cards,
    _narrative_available_sources,
    _narrative_data_bar_styles,
    _narrative_header_divider_styles,
    _narratives_table_columns,
    _narratives_table_rows,
    _normalized_narrative_sources,
    _normalize_sources,
    _table_columns,
    _table_records,
    _timeline_available_sources,
    _timeline_figure,
    _timeline_records_from_frame,
    _topic_area_available_sources,
    _topic_area_records_from_frame,
    _topic_area_treemap_figure,
    _top_publications_from_frame,
    build_publishers_details_section,
    build_publishers_overview_section,
)
from dashboards.amazon_2026.data_common import (
    PUBLISHER_SOME_TIMELINE_KEY,
    PUBLISHER_SOME_TOPIC_AREAS_KEY,
    PUBLISHER_TOPIC_AREAS_KEY,
    PUBLISHER_TOP_PUBLICATIONS_KEY,
    PUBLISHER_TRAD_TIMELINE_KEY,
    PUBLISHERS_KEY,
)
from dashboards.amazon_2026.charts_shared import register_top_items_callback
from dashboards.amazon_2026.dev_ids import ref_label
from dashboards.amazon_2026.pages._shared import metric_parameter

register_top_items_callback("amazon-2026-publisher")


def _uid_rows(df: pd.DataFrame, uid: str) -> pd.DataFrame:
    if "publisher_uid" in df.columns:
        return df[df["publisher_uid"] == uid]
    return df


def build_publishers_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-publishers",
        title=ref_label("Publishers", "P3"),
        path=f"{base_path}/publishers",
        description="Publisher-level footprint across traditional media and social media.",
        components=[
            vm.Figure(
                id="amazon-2026-publishers-overview-section",
                figure=publishers_overview_panel(data_frame=PUBLISHERS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-publishers-details-section",
                figure=publishers_details_panel(data_frame=PUBLISHERS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-publisher-basic-metric-sink",
                figure=publisher_basic_metric_sink(data_frame=PUBLISHERS_KEY),
            ),
        ],
        layout=vm.Flex(direction="column", gap="20px"),
        controls=[
            metric_parameter(
                ["amazon-2026-publisher-basic-metric-sink.basic_metric"],
                selector_id="amazon-2026-publisher-basic-metric",
            )
        ],
    )


@capture("figure")
def publishers_overview_panel(data_frame: pd.DataFrame):
    return build_publishers_overview_section(data_frame)


@capture("figure")
def publishers_details_panel(data_frame: pd.DataFrame):
    return build_publishers_details_section(data_frame)


@capture("figure")
def publisher_basic_metric_sink(data_frame: pd.DataFrame, basic_metric: str = "publications"):
    return html.Div(basic_metric, className="amazon-publishers-control-sink")


@callback(
    Output("amazon-2026-publishers-table", "data"),
    Output("amazon-2026-publishers-table", "columns"),
    Output("amazon-2026-publishers-table", "style_header_conditional"),
    Output("amazon-2026-publishers-table", "style_data_conditional"),
    Output("amazon-2026-publishers-kpis", "children"),
    Input("amazon-2026-publisher-source-filter", "value"),
    Input("amazon-2026-publisher-tml-filter", "value"),
    Input("amazon-2026-publisher-media-filter", "value"),
    State("amazon-2026-publishers-data", "data"),
)
def _update_publishers_table(
    source_filter: str | None,
    tml_filter: list[str] | str | None,
    media_filter: list[str] | str | None,
    records: list[dict[str, Any]] | None,
):
    filtered = _filter_records(records or [], source_filter or "All", tml_filter, media_filter)
    table_data = _table_records(filtered)
    columns = _table_columns(source_filter or "All")
    return (
        table_data,
        columns,
        _header_divider_styles(columns),
        _data_bar_styles(table_data, columns),
        _kpi_cards(filtered, source_filter or "All"),
    )


@callback(
    Output("amazon-2026-publisher-detail-select", "value"),
    Input("amazon-2026-publishers-table", "active_cell"),
    State("amazon-2026-publishers-table", "derived_viewport_data"),
    State("amazon-2026-publishers-table", "data"),
    prevent_initial_call=True,
)
def _select_author_from_table(active_cell, viewport_rows, table_rows):
    if not active_cell or active_cell.get("column_id") != "display_name":
        return no_update
    if active_cell.get("row_id"):
        return active_cell["row_id"]
    row_index = active_cell.get("row")
    if row_index is None:
        return no_update
    rows = viewport_rows or table_rows or []
    if row_index >= len(rows):
        return no_update
    selected_row = rows[row_index]
    return selected_row.get("publisher_uid") or selected_row.get("id") or no_update


@callback(
    Output("amazon-2026-publisher-details-content", "children"),
    Input("amazon-2026-publisher-detail-select", "value"),
    Input("amazon-2026-publisher-basic-metric", "value"),
    State("amazon-2026-publishers-data", "data"),
)
def _update_author_details(
    selected_uid: str | None,
    basic_metric: str | None,
    records: list[dict[str, Any]] | None,
):
    trad_metric, some_metric = _detail_metric_values(basic_metric or "publications")
    trad_timeline = []
    some_timeline = []
    topic_areas = []
    some_topic_areas = []
    top_publications = []
    if selected_uid:
        trad_timeline = _timeline_records_from_frame(_uid_rows(data_manager[PUBLISHER_TRAD_TIMELINE_KEY].load(), selected_uid))
        some_timeline = _timeline_records_from_frame(_uid_rows(data_manager[PUBLISHER_SOME_TIMELINE_KEY].load(), selected_uid))
        topic_areas = _topic_area_records_from_frame(_uid_rows(data_manager[PUBLISHER_TOPIC_AREAS_KEY].load(), selected_uid))
        some_topic_areas = _topic_area_records_from_frame(
            _uid_rows(data_manager[PUBLISHER_SOME_TOPIC_AREAS_KEY].load(), selected_uid),
            value_column="post_count",
        )
        top_publications = _top_publications_from_frame(_uid_rows(data_manager[PUBLISHER_TOP_PUBLICATIONS_KEY].load(), selected_uid))
    return _details_content(
        records or [],
        selected_uid,
        trad_metric,
        some_metric,
        trad_timeline,
        some_timeline,
        topic_areas,
        some_topic_areas,
        top_publications,
    )


@callback(
    Output("amazon-2026-publisher-narratives-table", "data"),
    Output("amazon-2026-publisher-narratives-table", "columns"),
    Output("amazon-2026-publisher-narratives-table", "style_header_conditional"),
    Output("amazon-2026-publisher-narratives-table", "style_data_conditional"),
    Output("amazon-2026-publisher-narratives-source", "value"),
    Input("amazon-2026-publisher-narratives-source", "value"),
    Input("amazon-2026-publisher-narratives-data", "data"),
    prevent_initial_call=True,
)
def _update_publisher_narratives_table(
    source_filter: list[str] | str | None,
    narrative_rows: list[dict[str, Any]] | None,
):
    available_sources = _narrative_available_sources(narrative_rows or [])
    selected_sources = _normalized_narrative_sources(source_filter, available_sources)
    table_rows = _narratives_table_rows(narrative_rows or [], selected_sources)
    table_columns = _narratives_table_columns(selected_sources)
    return (
        table_rows,
        table_columns,
        _narrative_header_divider_styles(selected_sources),
        _narrative_data_bar_styles(table_rows, table_columns),
        selected_sources,
    )


@callback(
    Output("amazon-2026-publisher-timeline-graph", "figure"),
    Output("amazon-2026-publisher-timeline-source", "value"),
    Input("amazon-2026-publisher-timeline-source", "value"),
    State("amazon-2026-publisher-timeline-data", "data"),
)
def _update_publisher_timeline_figure(
    source_filter: list[str] | str | None,
    timeline_data: dict[str, Any] | None,
):
    payload = timeline_data or {}
    available_sources = _timeline_available_sources(payload)
    selected_sources = _normalize_sources(source_filter, available_sources)
    return _timeline_figure(payload, selected_sources), selected_sources


@callback(
    Output("amazon-2026-publisher-topic-area-treemap", "figure"),
    Output("amazon-2026-publisher-topic-area-source", "value"),
    Input("amazon-2026-publisher-topic-area-source", "value"),
    State("amazon-2026-publisher-topic-area-data", "data"),
)
def _update_publisher_topic_area_treemap(
    source_filter: list[str] | str | None,
    topic_area_data: dict[str, Any] | None,
):
    payload = topic_area_data or {}
    available_sources = _topic_area_available_sources(payload)
    selected_sources = _normalize_sources(source_filter, available_sources)
    return _topic_area_treemap_figure(payload, selected_sources), selected_sources


