"""Publishers page — thin wiring layer. All components live in charts_publishers."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, clientside_callback, no_update

from dashboards.amazon_2026.charts_publishers import (
    _details_content,
    _filter_records,
    _records_from_frame,
    _kpi_cards,
    _narrative_available_sources,
    _narratives_table_rows,
    _topic_area_available_sources,
    _topic_area_records_from_frame,
    _topic_area_treemap_figure,
    _top_publications_from_frame,
    build_publishers_details_section,
    build_publishers_overview_section,
)
from dashboards.amazon_2026.timeline_charts import (
    _normalized_narrative_sources,
    normalize_sources,
    timeline_available_sources,
    timeline_figure,
)
from dashboards.amazon_2026.ui_components import (
    _narrative_data_bar_styles,
    _narrative_header_divider_styles,
    _narratives_table_columns,
    capture,
    data_bar_styles,
    data_load_failed,
    detail_metric_values,
    header_divider_styles,
    register_top_items_callback,
    safe_load,
    table_columns,
    table_records,
    timeline_records_from_frame,
)
from dashboards.amazon_2026.data_common import (
    PARAM_SINK_KEY,
    PUBLISHER_SOME_TIMELINE_KEY,
    PUBLISHER_SOME_TOPIC_AREAS_KEY,
    PUBLISHER_TOPIC_AREAS_KEY,
    PUBLISHER_TOP_PUBLICATIONS_KEY,
    PUBLISHER_TRAD_TIMELINE_KEY,
    PUBLISHERS_KEY,
)
from dashboards.amazon_2026.pages._shared import (
    basic_metric_sink,
    build_overview_table_response,
    build_standard_page,
    detail_content_scope,
    metric_parameter,
    select_active_table_value,
)

register_top_items_callback("amazon-2026-publisher")


def build_publishers_page(base_path: str) -> vm.Page:
    return build_standard_page(
        base_path=base_path,
        slug="publishers",
        display_name="Publishers",
        ref_code="P3",
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
            # Content in its own figure — see topic_areas.py / detail_content_scope for why.
            vm.Figure(
                id="amazon-2026-publisher-details-content",
                figure=publishers_content_panel(data_frame=PUBLISHERS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-publisher-basic-metric-sink",
                figure=basic_metric_sink(data_frame=PARAM_SINK_KEY),
            ),
        ],
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
def publishers_content_panel(data_frame: pd.DataFrame):
    # Renders the placeholder (no author selected); the populate callback fills it.
    return detail_content_scope(_details_content(_records_from_frame(data_frame), None))


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
    return build_overview_table_response(
        records=records,
        source_filter=source_filter,
        filter_records=_filter_records,
        table_records=table_records,
        table_columns=table_columns,
        header_styles=header_divider_styles,
        data_styles=data_bar_styles,
        tml_filter=tml_filter,
        media_filter=media_filter,
        extra_output=lambda filtered, _source: _kpi_cards(filtered),
    )


@callback(
    Output("amazon-2026-publisher-detail-select", "value"),
    Input("amazon-2026-publishers-table", "active_cell"),
    State("amazon-2026-publishers-table", "derived_viewport_data"),
    State("amazon-2026-publishers-table", "data"),
    prevent_initial_call=True,
)
def _select_author_from_table(active_cell, viewport_rows, table_rows):
    return select_active_table_value(
        active_cell,
        viewport_rows,
        table_rows,
        expected_column="display_name",
        fallback_value=no_update,
        row_id_first=True,
        value_keys=["publisher_uid", "id"],
    )


clientside_callback(
    "function(_children){ return Date.now(); }",
    Output("amazon-2026-publisher-detail-nonce", "data"),
    Input("amazon-2026-publishers-details-section", "children"),
    prevent_initial_call=True,
)


@callback(
    Output("amazon-2026-publisher-details-content", "children", allow_duplicate=True),
    Input("amazon-2026-publisher-detail-select", "value"),
    Input("amazon-2026-publisher-basic-metric", "value"),
    Input("amazon-2026-publisher-detail-nonce", "data"),
    State("amazon-2026-publishers-data", "data"),
    prevent_initial_call=True,
)
def _update_author_details(
    selected_uid: str | None,
    basic_metric: str | None,
    _nonce: Any,
    records: list[dict[str, Any]] | None,
):
    trad_metric, some_metric = detail_metric_values(basic_metric or "publications")
    trad_timeline = []
    some_timeline = []
    topic_areas = []
    some_topic_areas = []
    top_publications = []
    timeline_load_failed = False
    if selected_uid:
        detail_keys = [
            PUBLISHER_TRAD_TIMELINE_KEY,
            PUBLISHER_SOME_TIMELINE_KEY,
            PUBLISHER_TOPIC_AREAS_KEY,
            PUBLISHER_SOME_TOPIC_AREAS_KEY,
            PUBLISHER_TOP_PUBLICATIONS_KEY,
        ]
        with ThreadPoolExecutor(max_workers=5) as executor:
            def _load_uid_rows(key: str) -> pd.DataFrame:
                df = safe_load(key)
                if df.empty or "publisher_uid" not in df.columns:
                    return pd.DataFrame()
                return df[df["publisher_uid"] == selected_uid]

            loaded = list(executor.map(_load_uid_rows, detail_keys))
        timeline_load_failed = data_load_failed(loaded[0], loaded[1])
        trad_timeline = timeline_records_from_frame(loaded[0])
        some_timeline = timeline_records_from_frame(loaded[1])
        topic_areas = _topic_area_records_from_frame(loaded[2])
        some_topic_areas = _topic_area_records_from_frame(loaded[3], value_column="post_count")
        top_publications = _top_publications_from_frame(loaded[4])
    return detail_content_scope(_details_content(
        records or [],
        selected_uid,
        trad_metric,
        some_metric,
        trad_timeline,
        some_timeline,
        topic_areas,
        some_topic_areas,
        top_publications,
        timeline_load_failed,
    ))


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
    available_sources = timeline_available_sources(payload)
    selected_sources = normalize_sources(source_filter, available_sources)
    return timeline_figure(payload, selected_sources), selected_sources


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
    selected_sources = normalize_sources(source_filter, available_sources)
    return _topic_area_treemap_figure(payload, selected_sources), selected_sources
