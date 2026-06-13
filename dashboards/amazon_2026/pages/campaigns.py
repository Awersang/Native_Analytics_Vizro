"""Campaigns page."""
from __future__ import annotations

from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, html, no_update
from vizro.models.types import capture

from dashboards.amazon_2026.charts_campaigns import (
    _campaign_detail_content,
    build_campaign_campaigns_section,
    build_campaign_details_section,
    build_campaign_timeline_panel,
)
from dashboards.amazon_2026.charts_publishers import (
    _data_bar_styles,
    _filter_records,
    _header_divider_styles,
    _table_columns,
    _table_records,
)
from dashboards.amazon_2026.charts_narratives import (
    _narrative_detail_combined_weekly_figure,
    _narrative_detail_weekly_figure,
    _top_publishers_data_bar_styles,
    _top_publishers_table_rows,
)
from dashboards.amazon_2026.charts_shared import (
    TIMELINE_BASE_HEIGHT_PX,
    _detail_metric_values,
    _normalize_sources,
    _timeline_available_sources,
    _timeline_figure,
    _timeline_with_narratives_figure,
    register_top_items_callback,
)
from dashboards.amazon_2026.data_common import (
    CAMPAIGN_NARRATIVES_KEY,
    CAMPAIGN_TIMELINE_KEY,
    TOPIC_AREA_CAMPAIGNS_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label
from dashboards.amazon_2026.pages._shared import (
    build_detail_timeline_response,
    build_overview_table_response,
    metric_parameter,
    select_active_table_value,
)


def build_campaigns_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-campaigns",
        title=ref_label("Campaigns", "P7"),
        path=f"{base_path}/campaigns",
        description="Campaign performance and narrative interactions.",
        layout=vm.Flex(direction="column", gap="20px"),
        components=[
            vm.Figure(
                id="amazon-2026-campaign-timeline",
                figure=campaign_timeline_panel(data_frame=CAMPAIGN_TIMELINE_KEY),
            ),
            vm.Figure(
                id="amazon-2026-campaign-campaigns-section",
                figure=campaign_campaigns_panel(data_frame=TOPIC_AREA_CAMPAIGNS_KEY),
            ),
            vm.Figure(
                id="amazon-2026-campaign-details-section",
                figure=campaign_details_panel(data_frame=CAMPAIGN_TIMELINE_KEY),
            ),
            vm.Figure(
                id="amazon-2026-campaign-basic-metric-sink",
                figure=campaign_basic_metric_sink(data_frame=CAMPAIGN_TIMELINE_KEY),
            ),
        ],
        controls=[
            metric_parameter(
                ["amazon-2026-campaign-basic-metric-sink.basic_metric"],
                selector_id="amazon-2026-campaign-basic-metric",
            )
        ],
    )


@capture("figure")
def campaign_timeline_panel(data_frame: pd.DataFrame):
    return build_campaign_timeline_panel(data_frame)


@capture("figure")
def campaign_campaigns_panel(data_frame: pd.DataFrame):
    return build_campaign_campaigns_section(data_frame)


@capture("figure")
def campaign_details_panel(data_frame: pd.DataFrame):
    return build_campaign_details_section(data_frame)


@capture("figure")
def campaign_basic_metric_sink(data_frame: pd.DataFrame, basic_metric: str = "publications"):
    return html.Div(basic_metric, className="amazon-publishers-control-sink")


@callback(
    Output("amazon-2026-campaign-campaigns-table", "data"),
    Output("amazon-2026-campaign-campaigns-table", "columns"),
    Output("amazon-2026-campaign-campaigns-table", "style_header_conditional"),
    Output("amazon-2026-campaign-campaigns-table", "style_data_conditional"),
    Input("amazon-2026-campaign-campaign-source-filter", "value"),
    State("amazon-2026-campaign-campaigns-data", "data"),
)
def _update_campaign_campaigns_table(
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
        first_column_label="Campaign",
    )


@callback(
    Output("amazon-2026-campaign-detail-select", "value"),
    Input("amazon-2026-campaign-campaigns-table", "active_cell"),
    State("amazon-2026-campaign-campaigns-table", "derived_viewport_data"),
    State("amazon-2026-campaign-campaigns-table", "data"),
    prevent_initial_call=True,
)
def _select_campaign_from_campaigns_table(active_cell, viewport_rows, table_rows):
    return select_active_table_value(
        active_cell,
        viewport_rows,
        table_rows,
        expected_column="display_name",
        fallback_value=no_update,
        value_keys=["display_name"],
    )


@callback(
    Output("amazon-2026-campaign-details-content", "children"),
    Input("amazon-2026-campaign-detail-select", "value"),
    State("amazon-2026-campaign-campaigns-data", "data"),
)
def _update_campaign_details(selected_campaign: str | None, records: list[dict[str, Any]] | None):
    return _campaign_detail_content(
        selected_campaign,
        records=records or [],
        narratives_key=CAMPAIGN_NARRATIVES_KEY,
        show_top_journalists=False,
    )


@callback(
    Output("amazon-2026-campaign-detail-timeline-graph", "figure"),
    Output("amazon-2026-campaign-detail-timeline-title", "children"),
    Input("amazon-2026-campaign-detail-timeline-source", "value"),
    Input("amazon-2026-campaign-basic-metric", "value"),
    State("amazon-2026-campaign-detail-timeline-store", "data"),
    prevent_initial_call=True,
)
def _update_campaign_detail_timeline(source: list[str] | None, basic_metric: str | None, store_data: dict | None):
    return build_detail_timeline_response(
        source,
        basic_metric,
        store_data,
        ref_code="P7S2G1",
        make_ref_label=ref_label,
        combined_builder=_narrative_detail_combined_weekly_figure,
        single_builder=_narrative_detail_weekly_figure,
    )


@callback(
    Output("amazon-2026-campaign-sentiment-timeline-graph", "figure"),
    Output("amazon-2026-campaign-sentiment-timeline-graph", "style"),
    Output("amazon-2026-campaign-sentiment-timeline-source", "value"),
    Input("amazon-2026-campaign-sentiment-timeline-source", "value"),
    Input("amazon-2026-campaign-basic-metric", "value"),
    State("amazon-2026-campaign-sentiment-timeline-data", "data"),
    prevent_initial_call=True,
)
def _update_campaign_sentiment_timeline(
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
    raw_values = source_filter if isinstance(source_filter, list) else [source_filter] if source_filter else []
    narratives_on = "Narratives" in raw_values and bool(payload.get("narrative_labels"))
    if narratives_on:
        fig, height_px = _timeline_with_narratives_figure(payload, selected_sources, id_field="campaign")
        return fig, {"height": f"{height_px}px"}, [*selected_sources, "Narratives"]
    fig = _timeline_figure(payload, selected_sources, id_field="campaign")
    return fig, {"height": f"{TIMELINE_BASE_HEIGHT_PX}px"}, selected_sources


@callback(
    Output("amazon-2026-campaign-top-publishers-table", "data"),
    Output("amazon-2026-campaign-top-publishers-table", "style_data_conditional"),
    Input("amazon-2026-campaign-top-publishers-source", "value"),
    State("amazon-2026-campaign-top-publishers-store", "data"),
    prevent_initial_call=True,
)
def _update_campaign_top_publishers_table(
    source: str | None,
    records: list[dict[str, Any]] | None,
):
    table_rows = _top_publishers_table_rows(records or [], source)
    return table_rows, _top_publishers_data_bar_styles(table_rows)


register_top_items_callback("amazon-2026-campaign", show_publication_col=True, show_author_col=True)
