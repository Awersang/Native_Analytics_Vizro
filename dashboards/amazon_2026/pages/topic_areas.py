"""Topic Areas page — thin wiring layer. All components live in charts_topic_areas."""
from __future__ import annotations

from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, html, no_update
from vizro.models.types import capture

from dashboards.amazon_2026.charts_campaigns import _campaign_detail_content
from dashboards.amazon_2026.charts_narratives import (
    _narrative_detail_combined_weekly_figure,
    _narrative_detail_weekly_figure,
    _top_publishers_data_bar_styles,
    _top_publishers_table_rows,
)
from dashboards.amazon_2026.charts_publishers import (
    _data_bar_styles,
    _filter_records,
    _header_divider_styles,
    _table_columns,
    _table_records,
)
from dashboards.amazon_2026.charts_shared import (
    _detail_metric_values,
    _normalize_sources,
    _timeline_available_sources,
    _timeline_figure,
    register_top_items_callback,
)
from dashboards.amazon_2026.charts_topic_areas import (
    _topic_area_available_sources,
    _topic_area_breakdown_records,
    _topic_area_media_available_sources,
    _topic_area_media_records,
    _topic_area_media_sankey_figure,
    _topic_area_theme_treemap_figure,
    build_topic_area_details_section,
    build_topic_area_media_sankey_section,
    build_topic_area_overview_section,
    build_topic_area_treemap_section,
)
from dashboards.amazon_2026.data_common import (
    TOPIC_AREA_BREAKDOWN_KEY,
    TOPIC_AREA_MEDIA_KEY,
    TOPIC_AREA_OVERVIEW_KEY,
    TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY,
    TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY,
    TOPIC_AREA_TOP_JOURNALISTS_KEY,
    TOPIC_AREA_TOP_PUBLICATIONS_KEY,
    TOPIC_AREA_TOP_PUBLISHERS_KEY,
    TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY,
    TOPIC_AREA_WEEKLY_REACH_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label
from dashboards.amazon_2026.pages._shared import (
    build_detail_timeline_response,
    build_overview_table_response,
    metric_parameter,
    select_active_table_value,
)

register_top_items_callback("amazon-2026-ta-topicarea", show_publication_col=True, show_author_col=True)


def build_topic_areas_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-topic-areas",
        title=ref_label("Topic Areas", "P6"),
        path=f"{base_path}/topic-areas",
        description="Breakdown of coverage by topic area and theme.",
        components=[
            vm.Figure(
                id="amazon-2026-topic-area-treemap-section",
                figure=topic_area_treemap_panel(data_frame=TOPIC_AREA_BREAKDOWN_KEY),
            ),
            vm.Figure(
                id="amazon-2026-topic-area-media-sankey-section",
                figure=topic_area_media_sankey_panel(data_frame=TOPIC_AREA_MEDIA_KEY),
            ),
            vm.Figure(
                id="amazon-2026-topic-area-overview-section",
                figure=topic_area_overview_panel(data_frame=TOPIC_AREA_OVERVIEW_KEY),
            ),
            vm.Figure(
                id="amazon-2026-topic-area-details-section",
                figure=topic_area_details_panel(data_frame=TOPIC_AREA_OVERVIEW_KEY),
            ),
            vm.Figure(
                id="amazon-2026-topic-area-basic-metric-sink",
                figure=topic_area_basic_metric_sink(data_frame=TOPIC_AREA_BREAKDOWN_KEY),
            ),
        ],
        layout=vm.Flex(direction="column", gap="20px"),
        controls=[
            metric_parameter(
                ["amazon-2026-topic-area-basic-metric-sink.basic_metric"],
                selector_id="amazon-2026-topic-area-basic-metric",
            )
        ],
    )


@capture("figure")
def topic_area_treemap_panel(data_frame: pd.DataFrame):
    records = _topic_area_breakdown_records(data_frame)
    return build_topic_area_treemap_section(records)


@capture("figure")
def topic_area_media_sankey_panel(data_frame: pd.DataFrame):
    records = _topic_area_media_records(data_frame)
    return build_topic_area_media_sankey_section(records)


@capture("figure")
def topic_area_overview_panel(data_frame: pd.DataFrame):
    return build_topic_area_overview_section(data_frame)


@capture("figure")
def topic_area_details_panel(data_frame: pd.DataFrame):
    return build_topic_area_details_section(data_frame)


@capture("figure")
def topic_area_basic_metric_sink(data_frame: pd.DataFrame, basic_metric: str = "publications"):
    return html.Div(basic_metric, className="amazon-publishers-control-sink")


@callback(
    Output("amazon-2026-topic-area-treemap", "figure"),
    Output("amazon-2026-topic-area-source", "value"),
    Input("amazon-2026-topic-area-source", "value"),
    Input("amazon-2026-topic-area-basic-metric", "value"),
    State("amazon-2026-topic-area-data", "data"),
)
def _update_topic_area_treemap(
    source_filter: list[str] | str | None,
    basic_metric: str | None,
    records: list[dict[str, Any]] | None,
):
    records = records or []
    available_sources = _topic_area_available_sources(records)
    selected_sources = _normalize_sources(source_filter, available_sources)
    fig = _topic_area_theme_treemap_figure(records, selected_sources, basic_metric or "publications")
    return fig, selected_sources


@callback(
    Output("amazon-2026-topic-area-media-sankey", "figure"),
    Output("amazon-2026-topic-area-media-source", "value"),
    Input("amazon-2026-topic-area-media-source", "value"),
    Input("amazon-2026-topic-area-basic-metric", "value"),
    State("amazon-2026-topic-area-media-data", "data"),
)
def _update_topic_area_media_sankey(
    source_filter: list[str] | str | None,
    basic_metric: str | None,
    records: list[dict[str, Any]] | None,
):
    records = records or []
    available_sources = _topic_area_media_available_sources(records)
    selected_sources = _normalize_sources(source_filter, available_sources)
    fig = _topic_area_media_sankey_figure(records, selected_sources, basic_metric or "publications")
    return fig, selected_sources


@callback(
    Output("amazon-2026-topic-area-overview-table", "data"),
    Output("amazon-2026-topic-area-overview-table", "columns"),
    Output("amazon-2026-topic-area-overview-table", "style_header_conditional"),
    Output("amazon-2026-topic-area-overview-table", "style_data_conditional"),
    Input("amazon-2026-topic-area-overview-source-filter", "value"),
    State("amazon-2026-topic-area-overview-data", "data"),
)
def _update_topic_area_overview_table(
    source_filter: str | None,
    records: list[dict[str, Any]] | None,
):
    return build_overview_table_response(
        records=records,
        source_filter=source_filter,
        filter_records=_filter_records,
        table_records=_table_records,
        table_columns=_table_columns,
        header_styles=_header_divider_styles,
        data_styles=_data_bar_styles,
        first_column_label="Topic Area",
    )


@callback(
    Output("amazon-2026-ta-topicarea-detail-select", "value"),
    Input("amazon-2026-topic-area-overview-table", "active_cell"),
    State("amazon-2026-topic-area-overview-table", "derived_viewport_data"),
    State("amazon-2026-topic-area-overview-table", "data"),
    prevent_initial_call=True,
)
def _select_topic_area_from_table(active_cell, viewport_rows, table_rows):
    return select_active_table_value(
        active_cell,
        viewport_rows,
        table_rows,
        expected_column="display_name",
        fallback_value=no_update,
        value_keys=["display_name"],
    )


@callback(
    Output("amazon-2026-ta-topicarea-details-content", "children"),
    Input("amazon-2026-ta-topicarea-detail-select", "value"),
    State("amazon-2026-topic-area-overview-data", "data"),
)
def _update_topic_area_details(selected_topic_area: str | None, records: list[dict[str, Any]] | None):
    return _campaign_detail_content(
        selected_topic_area,
        "amazon-2026-ta-topicarea",
        "P6S4",
        records or [],
        filter_column="topic_area",
        weekly_reach_key=TOPIC_AREA_WEEKLY_REACH_KEY,
        some_weekly_engagement_key=TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY,
        trad_sentiment_key=TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY,
        some_sentiment_key=TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY,
        top_publishers_key=TOPIC_AREA_TOP_PUBLISHERS_KEY,
        top_journalists_key=TOPIC_AREA_TOP_JOURNALISTS_KEY,
        top_publications_key=TOPIC_AREA_TOP_PUBLICATIONS_KEY,
        empty_label="Select a topic area to see details.",
        top_publishers_title="Top Topic Area Publishers",
        show_top_journalists_inline=True,
        show_profile=False,
    )


@callback(
    Output("amazon-2026-ta-topicarea-detail-timeline-graph", "figure"),
    Output("amazon-2026-ta-topicarea-detail-timeline-title", "children"),
    Input("amazon-2026-ta-topicarea-detail-timeline-source", "value"),
    Input("amazon-2026-topic-area-basic-metric", "value"),
    State("amazon-2026-ta-topicarea-detail-timeline-store", "data"),
    prevent_initial_call=True,
)
def _update_topic_area_detail_timeline(source: list[str] | None, basic_metric: str | None, store_data: dict | None):
    return build_detail_timeline_response(
        source,
        basic_metric,
        store_data,
        ref_code="P6S4G1",
        make_ref_label=ref_label,
        combined_builder=_narrative_detail_combined_weekly_figure,
        single_builder=_narrative_detail_weekly_figure,
        dtick=7 * 24 * 60 * 60 * 1000,
    )


@callback(
    Output("amazon-2026-ta-topicarea-sentiment-timeline-graph", "figure"),
    Output("amazon-2026-ta-topicarea-sentiment-timeline-source", "value"),
    Input("amazon-2026-ta-topicarea-sentiment-timeline-source", "value"),
    Input("amazon-2026-topic-area-basic-metric", "value"),
    State("amazon-2026-ta-topicarea-sentiment-timeline-data", "data"),
    prevent_initial_call=True,
)
def _update_topic_area_sentiment_timeline(
    source_filter: list[str] | str | None,
    basic_metric: str | None,
    timeline_data: dict[str, Any] | None,
):
    payload = dict(timeline_data or {})
    trad_metric, some_metric = _detail_metric_values(basic_metric or "publications")
    payload["trad_metric"] = trad_metric
    payload["some_metric"] = some_metric
    available_sources = _timeline_available_sources(payload)
    selected_sources = _normalize_sources(source_filter, available_sources)
    return _timeline_figure(payload, selected_sources, id_field="topic_area"), selected_sources


@callback(
    Output("amazon-2026-ta-topicarea-top-publishers-table", "data"),
    Output("amazon-2026-ta-topicarea-top-publishers-table", "style_data_conditional"),
    Input("amazon-2026-ta-topicarea-top-publishers-source", "value"),
    State("amazon-2026-ta-topicarea-top-publishers-store", "data"),
    prevent_initial_call=True,
)
def _update_topic_area_top_publishers_table(
    source: str | None,
    records: list[dict[str, Any]] | None,
):
    table_rows = _top_publishers_table_rows(records or [], source)
    return table_rows, _top_publishers_data_bar_styles(table_rows)
