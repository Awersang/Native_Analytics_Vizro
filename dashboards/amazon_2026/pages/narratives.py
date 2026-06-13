"""Narratives page — thin wiring layer. All components live in charts_narratives."""
from __future__ import annotations

from typing import Any

import pandas as pd
import vizro.models as vm
from dash import Input, Output, State, callback, html, no_update
from vizro.models.types import capture

from dashboards.amazon_2026.charts_narratives import (
    _angles_data_bar_styles,
    _angles_table_columns,
    _angles_table_rows,
    _filter_top_items_by_angle,
    _narrative_data_bar_styles,
    _narrative_detail_combined_weekly_figure,
    _narrative_detail_content,
    _narrative_detail_weekly_figure,
    _narrative_header_divider_styles,
    _narrative_small_multiples_figure,
    _narrative_weekly_figure,
    _norm_source,
    _overview_table_rows,
    _top_publishers_data_bar_styles,
    _top_publishers_table_rows,
    build_narratives_combined_timeline_section,
    build_narratives_detail_section,
    build_narratives_overview_section,
    narratives_kpi_panel,
    overview_table_columns,
)
from dashboards.amazon_2026.charts_shared import (
    _detail_metric_values,
    _timeline_available_sources,
    _timeline_figure,
    _normalize_sources,
    build_top_posts_table,
    build_top_publications_table,
)
from dashboards.amazon_2026.data_common import (
    NARRATIVE_DETAIL_KPI_KEY,
    NARRATIVE_OVERVIEW_KEY,
    NARRATIVE_WEEKLY_REACH_KEY,
    NARRATIVES_KPI_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label
from dashboards.amazon_2026.pages._shared import (
    build_detail_timeline_response,
    metric_parameter,
    select_active_table_value,
)


def build_narratives_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-narratives",
        title=ref_label("Narratives", "P2"),
        path=f"{base_path}/narratives",
        description="Narrative analysis across traditional media and social media.",
        layout=vm.Flex(direction="column", gap="20px"),
        components=[
            vm.Figure(
                id="amazon-2026-narratives-kpi-section",
                figure=narratives_kpi_panel(data_frame=NARRATIVES_KPI_KEY),
            ),
            vm.Figure(
                id="amazon-2026-narratives-weekly-timeline",
                figure=_narratives_timeline_panel(data_frame=NARRATIVE_WEEKLY_REACH_KEY),
            ),
            vm.Figure(
                id="amazon-2026-narratives-overview-section",
                figure=narratives_overview_panel(data_frame=NARRATIVE_OVERVIEW_KEY),
            ),
            vm.Figure(
                id="amazon-2026-narratives-detail-section",
                figure=narratives_detail_panel(data_frame=NARRATIVE_DETAIL_KPI_KEY),
            ),
            vm.Figure(
                id="amazon-2026-narrative-basic-metric-sink",
                figure=narrative_basic_metric_sink(data_frame=NARRATIVES_KPI_KEY),
            ),
        ],
        controls=[
            metric_parameter(
                ["amazon-2026-narrative-basic-metric-sink.basic_metric"],
                selector_id="amazon-2026-narrative-basic-metric",
            )
        ],
    )


@capture("figure")
def narratives_overview_panel(data_frame: pd.DataFrame):
    return build_narratives_overview_section(data_frame)


@capture("figure")
def _narratives_timeline_panel(data_frame: pd.DataFrame):
    return build_narratives_combined_timeline_section(data_frame)


@capture("figure")
def narrative_basic_metric_sink(data_frame: pd.DataFrame, basic_metric: str = "publications"):
    return html.Div(basic_metric, className="amazon-publishers-control-sink")


@capture("figure")
def narratives_detail_panel(data_frame: pd.DataFrame):
    return build_narratives_detail_section(data_frame)


@callback(
    Output("amazon-2026-narrative-detail-select", "value"),
    Input("amazon-2026-narratives-overview-table", "active_cell"),
    State("amazon-2026-narratives-overview-table", "derived_viewport_data"),
    State("amazon-2026-narratives-overview-table", "data"),
    prevent_initial_call=True,
)
def _select_narrative_from_table(active_cell, viewport_rows, table_rows):
    return select_active_table_value(
        active_cell,
        viewport_rows,
        table_rows,
        expected_column="narrative_label",
        fallback_value=no_update,
        row_id_first=True,
        value_keys=["narrative_label"],
    )


@callback(
    Output("amazon-2026-narrative-details-content", "children"),
    Input("amazon-2026-narrative-detail-select", "value"),
    State("amazon-2026-narrative-detail-store", "data"),
    State("amazon-2026-narratives-overview-data", "data"),
)
def _update_narrative_details(
    selected_label: str | None,
    records: list[dict[str, Any]] | None,
    overview_records: list[dict[str, Any]] | None,
):
    return _narrative_detail_content(records or [], selected_label, overview_records or [])


@callback(
    Output("amazon-2026-narratives-timeline-graph", "figure"),
    Output("amazon-2026-narratives-timeline-graph", "style"),
    Output("amazon-2026-narratives-timeline-title", "children"),
    Input("amazon-2026-narratives-timeline-source", "value"),
    State("amazon-2026-narratives-timeline-store", "data"),
)
def _update_narratives_timeline(source: str | None, store_data: dict | None):
    data = store_data or {}
    color_map = data.get("color_map") or {}
    x_range = data.get("x_range") or None

    if source == "SoMe":
        df = pd.DataFrame(data.get("some") or [])
        fig = _narrative_weekly_figure(df, "weekly_engagement", "weekly_posts", "posts", "Weekly Engagement", color_map=color_map, x_range=x_range)
        return fig, {"height": "520px"}, ref_label("Weekly Engagement by Narrative", "P2S2G1")

    if source == "Trad-Multi":
        df = pd.DataFrame(data.get("trad") or [])
        fig, height_px = _narrative_small_multiples_figure(df, "weekly_reach", "weekly_publications", "pubs", "Weekly Reach", color_map=color_map, x_range=x_range)
        return fig, {"height": f"{height_px}px"}, ref_label("Weekly Reach by Narrative — Faceted", "P2S2G1")

    if source == "SoMe-Multi":
        df = pd.DataFrame(data.get("some") or [])
        fig, height_px = _narrative_small_multiples_figure(df, "weekly_engagement", "weekly_posts", "posts", "Weekly Engagement", color_map=color_map, x_range=x_range)
        return fig, {"height": f"{height_px}px"}, ref_label("Weekly Engagement by Narrative — Faceted", "P2S2G1")

    # default: Trad combined
    df = pd.DataFrame(data.get("trad") or [])
    fig = _narrative_weekly_figure(df, "weekly_reach", "weekly_publications", "pubs", "Weekly Reach", color_map=color_map, x_range=x_range)
    return fig, {"height": "520px"}, ref_label("Weekly Reach by Narrative", "P2S2G1")


@callback(
    Output("amazon-2026-narrative-detail-timeline-graph", "figure"),
    Output("amazon-2026-narrative-detail-timeline-title", "children"),
    Input("amazon-2026-narrative-detail-timeline-source", "value"),
    Input("amazon-2026-narrative-basic-metric", "value"),
    State("amazon-2026-narrative-detail-timeline-store", "data"),
    prevent_initial_call=True,
)
def _update_narrative_detail_timeline(source: list[str] | None, basic_metric: str | None, store_data: dict | None):
    return build_detail_timeline_response(
        source,
        basic_metric,
        store_data,
        ref_code="P2S4G1",
        make_ref_label=ref_label,
        combined_builder=_narrative_detail_combined_weekly_figure,
        single_builder=_narrative_detail_weekly_figure,
    )


@callback(
    Output("amazon-2026-narrative-sentiment-timeline-graph", "figure"),
    Output("amazon-2026-narrative-sentiment-timeline-source", "value"),
    Input("amazon-2026-narrative-sentiment-timeline-source", "value"),
    Input("amazon-2026-narrative-basic-metric", "value"),
    State("amazon-2026-narrative-sentiment-timeline-data", "data"),
    prevent_initial_call=True,
)
def _update_narrative_sentiment_timeline(
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
    return _timeline_figure(payload, selected_sources, id_field="narrative_label"), selected_sources


@callback(
    Output("amazon-2026-narrative-angles-table", "data"),
    Output("amazon-2026-narrative-angles-table", "style_data_conditional"),
    Input("amazon-2026-narrative-angles-sentiment", "value"),
    State("amazon-2026-narrative-angles-store", "data"),
    prevent_initial_call=True,
)
def _update_narrative_angles_table(
    sentiments: list[str] | None,
    records: list[dict[str, Any]] | None,
):
    table_rows = _angles_table_rows(records or [], sentiments)
    table_cols = _angles_table_columns()
    return table_rows, _angles_data_bar_styles(table_rows, table_cols)


@callback(
    Output("amazon-2026-narrative-angles-filter", "value"),
    Input("amazon-2026-narrative-angles-table", "active_cell"),
    State("amazon-2026-narrative-angles-table", "derived_viewport_data"),
    State("amazon-2026-narrative-angles-table", "data"),
    prevent_initial_call=True,
)
def _select_angle_from_table(active_cell, viewport_rows, table_rows):
    return select_active_table_value(
        active_cell,
        viewport_rows,
        table_rows,
        expected_column="angle_label",
        fallback_value=no_update,
        row_id_first=True,
        value_keys=["angle_label"],
    )


@callback(
    Output("amazon-2026-narrative-top-items-table", "children"),
    Input("amazon-2026-narrative-top-items-source", "value"),
    Input("amazon-2026-narrative-angles-filter", "value"),
    State("amazon-2026-narrative-top-items-data", "data"),
    prevent_initial_call=True,
)
def _update_narrative_top_items_table(source, angle, store_data):
    data = store_data or {}
    trad_raw = data.get("trad", [])
    some_raw = data.get("some", [])
    trad = _filter_top_items_by_angle(trad_raw, angle)
    some = _filter_top_items_by_angle(some_raw, angle)
    if source == "SoMe":
        return build_top_posts_table("amazon-2026-narrative-top-posts", some, show_author_col=True)
    return build_top_publications_table("amazon-2026-narrative-top-publications", trad, show_publication_col=True)


@callback(
    Output("amazon-2026-narrative-top-publishers-table", "data"),
    Output("amazon-2026-narrative-top-publishers-table", "style_data_conditional"),
    Input("amazon-2026-narrative-top-publishers-source", "value"),
    State("amazon-2026-narrative-top-publishers-store", "data"),
    prevent_initial_call=True,
)
def _update_narrative_top_publishers_table(
    source: str | None,
    records: list[dict[str, Any]] | None,
):
    table_rows = _top_publishers_table_rows(records or [], source)
    return table_rows, _top_publishers_data_bar_styles(table_rows)


@callback(
    Output("amazon-2026-narratives-overview-table", "data"),
    Output("amazon-2026-narratives-overview-table", "columns"),
    Output("amazon-2026-narratives-overview-table", "style_header_conditional"),
    Output("amazon-2026-narratives-overview-table", "style_data_conditional"),
    Input("amazon-2026-narratives-source-filter", "value"),
    State("amazon-2026-narratives-overview-data", "data"),
)
def _update_narratives_overview_table(
    source_filter: str | None,
    records: list[dict[str, Any]] | None,
):
    norm = _norm_source(source_filter or "All")
    table_data = _overview_table_rows(records or [], norm)
    columns = overview_table_columns(norm)
    return (
        table_data,
        columns,
        _narrative_header_divider_styles(norm),
        _narrative_data_bar_styles(table_data, columns),
    )
