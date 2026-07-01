"""Publisher page components — chart builders, data transforms, and style helpers."""
from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, dcc, html

from dashboards.amazon_2026.theme import (
    ACCENT_SOME,
    ACCENT_TRAD,
    DONUT_COLORS,
    THEME_BORDER,
    THEME_ROW_EVEN,
    THEME_SURFACE,
    THEME_SURFACE_ALT,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    hex_to_rgba,
    topic_area_color_map,
)
from dashboards.amazon_2026.timeline_charts import (
    _as_list,
    _filter_trad_some,
    _normalized_narrative_sources,
    _timeline_chart_title,
    normalize_sources,
    timeline_available_sources,
    timeline_figure,
)
from dashboards.amazon_2026.ui_components import (
    NARRATIVE_SOME_COLUMNS,
    NARRATIVE_TRAD_COLUMNS,
    SOURCE_OPTIONS,
    TOOLTIP_CSS,
    _coerce_float,
    chart_menu_button,
    _narrative_data_bar_styles,
    _narrative_header_divider_styles,
    _narratives_table_columns,
    build_overview_table_section,
    build_top_items_panel,
    build_top_items_table_data,
    cell_width_styles,
    data_bar_styles,
    detail_kpi_groups,
    dev_inline_label,
    donut_figure,
    donut_panel,
    empty_donut_panel,
    find_record,
    header_divider_styles,
    json_safe,
    kpi_card,
    na_panel,
    num,
    table_columns,
    table_records,
    trad_some_controls,
)
from dashboards.amazon_2026.dev_ids import ref_label

# ---------------------------------------------------------------------------
# Public section builders (called by @capture wrappers in publishers.py)
# ---------------------------------------------------------------------------


def build_publishers_overview_section(data_frame: pd.DataFrame) -> html.Div:
    records = _records_from_frame(data_frame)
    table_data = table_records(records)
    columns = table_columns("All")
    controls = html.Div(
        className="amazon-publishers-controls",
        children=[
            html.Div(
                className="amazon-publishers-control amazon-publishers-source-control",
                children=[
                    html.Div("Source", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-publisher-source-filter",
                        options=SOURCE_OPTIONS,
                        value="All",
                        clearable=False,
                        searchable=False,
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
            html.Div(
                className="amazon-publishers-control",
                children=[
                    html.Div("TML", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-publisher-tml-filter",
                        options=_filter_options(records, "tml_labels"),
                        multi=True,
                        searchable=True,
                        placeholder="All",
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
            html.Div(
                className="amazon-publishers-control",
                children=[
                    html.Div("Media Type", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-publisher-media-filter",
                        options=_filter_options(records, "media_types"),
                        multi=True,
                        searchable=True,
                        placeholder="All",
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
        ],
    )
    return build_overview_table_section(
        records=records,
        store_id="amazon-2026-publishers-data",
        section_title=ref_label("Overview", "P3S1"),
        controls=controls,
        dev_label=dev_inline_label("P3S1T1", "Overview Table"),
        table_id="amazon-2026-publishers-table",
        table_data=table_data,
        columns=columns,
        style_cell_conditional=cell_width_styles(),
        style_header_conditional=header_divider_styles(columns),
        style_data_conditional=data_bar_styles(table_data, columns),
        pre_table_children=[html.Div(id="amazon-2026-publishers-kpis", children=_kpi_cards(records))],
    )


def build_publishers_details_section(data_frame: pd.DataFrame) -> html.Div:
    records = _records_from_frame(data_frame)
    return html.Div(
        className="amazon-publishers-section amazon-publishers-details",
        children=[
            html.Div(
                className="amazon-publishers-section-header",
                children=[html.H2(ref_label("Details", "P3S2"))],
            ),
            html.Div(
                className="amazon-publishers-detail-selector",
                children=[
                    html.Div("Author", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-publisher-detail-select",
                        options=_author_options(records),
                        value=None,
                        searchable=True,
                        clearable=True,
                        persistence=True,
                        persistence_type="session",
                        placeholder="Select author",
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
            # Content lives in its own vm.Figure (see pages/publishers.py + detail_content_scope):
            # keeps shell and populated content as separate single-source props so a click can't
            # revert the content. Nonce bumped by a clientside callback after _on_page_load rebuilds
            # this shell, re-populating the current selection.
            dcc.Store(id="amazon-2026-publisher-detail-nonce"),
        ],
    )


# ---------------------------------------------------------------------------
# Data transforms
# ---------------------------------------------------------------------------


def _records_from_frame(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in [
        "publisher_uid",
        "display_name",
        "publisher_type",
        "is_tml",
        "platforms_url",
        "website_url",
        "profile_description",
        "combined_top_narratives",
        "trad_top_narratives",
        "some_top_narratives",
        "tml_values",
        "media_types",
        "trad_dominant_media_type",
        "some_dominant_platform",
    ]:
        if column not in df.columns:
            df[column] = ""
    for column in [
        "total_items",
        "trad_article_count",
        "trad_total_reach",
        "trad_positive_pct",
        "trad_negative_pct",
        "some_post_count",
        "some_total_reach",
        "some_total_engagement",
        "some_avg_engagement",
        "some_positive_pct",
        "some_negative_pct",
        "some_engagement_positive",
        "some_engagement_negative",
        "some_engagement_neutral",
    ]:
        if column not in df.columns:
            df[column] = 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["display_name"] = df["display_name"].fillna("").astype(str)
    df["publisher_uid"] = df["publisher_uid"].fillna("").astype(str)
    df.loc[df["publisher_uid"].eq(""), "publisher_uid"] = df.loc[df["publisher_uid"].eq(""), "display_name"]
    df["tml_labels"] = df.apply(_publisher_tml_labels, axis=1)
    df = df.sort_values(["total_items", "display_name"], ascending=[False, True]).reset_index(drop=True)
    return [json_safe(record) for record in df.to_dict("records")]


def _publisher_tml_labels(row: pd.Series) -> str:
    labels = _normalize_tml_labels(row.get("is_tml"))
    if not labels:
        labels = _normalize_tml_labels(row.get("tml_values"))
    return ", ".join(labels)


def _top_publications_from_frame(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in ["publisher_uid", "Date", "Source", "Type", "Title", "Summary", "URL", "Sentiment", "Reach", "Engagement"]:
        if column not in df.columns:
            df[column] = ""
    df["Reach"] = pd.to_numeric(df["Reach"], errors="coerce").fillna(0).astype(int)
    df["Engagement"] = pd.to_numeric(df["Engagement"], errors="coerce").fillna(0).astype(int)
    return [json_safe(record) for record in df.to_dict("records")]


def _topic_area_records_from_frame(
    data_frame: pd.DataFrame,
    value_column: str = "publication_count",
) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in ["publisher_uid", "topic_area"]:
        if column not in df.columns:
            df[column] = ""
    if value_column not in df.columns:
        df[value_column] = 0
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce").fillna(0)
    return [json_safe(record) for record in df.to_dict("records")]


# ---------------------------------------------------------------------------
# Overview table helpers
# ---------------------------------------------------------------------------


def _filter_records(
    records: list[dict[str, Any]],
    source_filter: str,
    tml_filter: list[str] | str | None,
    media_filter: list[str] | str | None,
) -> list[dict[str, Any]]:
    tml_values = set(_as_list(tml_filter))
    media_values = set(_as_list(media_filter))
    filtered = []
    for record in records:
        if source_filter == "Trad" and num(record, "trad_article_count") <= 0:
            continue
        if source_filter == "SoMe" and num(record, "some_post_count") <= 0:
            continue
        if source_filter == "Trad+SoMe" and (
            num(record, "trad_article_count") <= 0 or num(record, "some_post_count") <= 0
        ):
            continue
        record_tml_values = set(
            _normalize_tml_labels(record.get("tml_labels") or record.get("is_tml") or record.get("tml_values"))
        )
        if tml_values and not tml_values.intersection(record_tml_values):
            continue
        if media_values and not media_values.intersection(_split_values(record.get("media_types", ""))):
            continue
        filtered.append(record)
    return filtered


# ---------------------------------------------------------------------------
# KPI panels and charts
# ---------------------------------------------------------------------------


def _kpi_cards(records: list[dict[str, Any]]) -> html.Div:
    total_publishers = 0
    trad_publishers = 0
    some_publishers = 0
    linked_publishers = 0
    for row in records:
        total_publishers += 1
        has_trad = num(row, "trad_article_count") > 0
        has_some = num(row, "some_post_count") > 0
        trad_publishers += int(has_trad)
        some_publishers += int(has_some)
        linked_publishers += int(has_trad and has_some)
    return html.Div(
        className="amazon-publishers-kpis",
        children=[
            html.Div(
                className="amazon-publishers-kpi-panel amazon-publishers-kpi-panel-summary",
                children=[
                    html.Div(
                        className="amazon-publishers-kpi-panel-summary-kpis",
                        children=[
                            kpi_card("Publishers Total", f"{total_publishers:,.0f}", compact=True),
                            kpi_card("Linked Trad + SoMe", f"{linked_publishers:,.0f}", compact=True),
                        ],
                    ),
                    _publisher_overlap_venn(trad_publishers, some_publishers, linked_publishers),
                ],
            ),
            _distribution_panel(
                "Trad",
                "Trad Publishers",
                trad_publishers,
                records,
                "trad_dominant_media_type",
                "Media type split",
                lambda row: num(row, "trad_article_count") > 0,
            ),
            _distribution_panel(
                "SoMe",
                "SoMe Publishers",
                some_publishers,
                records,
                "some_dominant_platform",
                "Platform split",
                lambda row: num(row, "some_post_count") > 0,
            ),
        ],
    )


def _distribution_panel(
    title: str,
    stat_label: str,
    stat_value: int,
    records: list[dict[str, Any]],
    category_key: str,
    chart_title: str,
    row_filter,
) -> html.Div:
    donut = _mini_donut_chart(records, category_key, chart_title, row_filter)
    return html.Div(
        className="amazon-publishers-kpi-panel",
        children=[
            html.Div(title, className="amazon-publishers-kpi-group-title"),
            html.Div(
                className="amazon-publishers-kpi-panel-body",
                children=[kpi_card(stat_label, f"{stat_value:,.0f}", compact=True), donut],
            ),
        ],
    )


def _mini_donut_chart(
    records: list[dict[str, Any]],
    category_key: str,
    chart_title: str,
    row_filter,
) -> html.Div:
    distribution = _category_distribution(records, category_key, row_filter)
    if not distribution:
        return empty_donut_panel()

    labels = [item["label"] for item in distribution]
    values = [item["count"] for item in distribution]
    colors = _donut_colors(len(distribution))
    figure = donut_figure(
        labels, values, colors, hovertemplate="%{label}: %{value} publishers (%{percent})<extra></extra>"
    )
    return donut_panel(chart_title, figure)


def _publisher_overlap_venn(trad_publishers: int, some_publishers: int, linked_publishers: int) -> html.Div:
    max_total = max(trad_publishers, some_publishers, 1)
    max_radius = 0.3
    min_radius = 0.18
    trad_radius = max(min_radius, max_radius * math.sqrt(trad_publishers / max_total))
    some_radius = max(min_radius, max_radius * math.sqrt(some_publishers / max_total))
    overlap_ratio = linked_publishers / max(min(trad_publishers, some_publishers), 1)
    overlap_ratio = min(max(overlap_ratio, 0), 1)

    overlap_depth = min(trad_radius, some_radius) * (0.18 + 0.82 * overlap_ratio)
    center_distance = max(
        abs(trad_radius - some_radius) + 0.03,
        trad_radius + some_radius - overlap_depth,
    )
    overlap_span = trad_radius + center_distance + some_radius
    left_edge = 0.04
    right_edge = 0.96
    scale = min(1.0, (right_edge - left_edge) / overlap_span)
    trad_radius *= scale
    some_radius *= scale
    center_distance *= scale

    left_edge = 0.5 - (trad_radius + center_distance + some_radius) / 2
    trad_center_x = left_edge + trad_radius
    some_center_x = trad_center_x + center_distance
    trad_center_y = 0.5
    some_center_y = 0.5

    trad_x, trad_y = _circle_points(trad_center_x, trad_center_y, trad_radius)
    some_x, some_y = _circle_points(some_center_x, some_center_y, some_radius)
    overlap_x = (trad_center_x + some_center_x) / 2
    overlap_y = 0.5
    trad_label_y = min(0.9, trad_center_y + trad_radius + 0.06)
    some_label_y = min(0.9, some_center_y + some_radius + 0.06)
    trad_value_x = trad_center_x - trad_radius * 0.38
    some_value_x = some_center_x + some_radius * 0.38

    figure = go.Figure(
        [
            go.Scatter(
                x=trad_x,
                y=trad_y,
                mode="lines",
                fill="toself",
                fillcolor=hex_to_rgba(ACCENT_TRAD, 0.28),
                line={"color": ACCENT_TRAD, "width": 1.5},
                hoverinfo="skip",
                showlegend=False,
            ),
            go.Scatter(
                x=some_x,
                y=some_y,
                mode="lines",
                fill="toself",
                fillcolor=hex_to_rgba(ACCENT_SOME, 0.28),
                line={"color": ACCENT_SOME, "width": 1.5},
                hoverinfo="skip",
                showlegend=False,
            ),
            go.Scatter(
                x=[trad_center_x, some_center_x],
                y=[trad_label_y, some_label_y],
                mode="text",
                text=["Trad", "SoMe"],
                textposition="middle center",
                textfont={"size": 14, "color": THEME_TEXT, "family": "Arial Black, Arial, sans-serif"},
                hoverinfo="skip",
                showlegend=False,
            ),
            go.Scatter(
                x=[trad_value_x, some_value_x, overlap_x],
                y=[0.5, 0.5, overlap_y],
                mode="text",
                text=[
                    f"<b>{trad_publishers:.0f}</b>",
                    f"<b>{some_publishers:.0f}</b>",
                    f"<b>{linked_publishers:.0f}</b>",
                ],
                textposition="middle center",
                textfont={"size": 15, "color": THEME_TEXT, "family": "Arial Black, Arial, sans-serif"},
                hoverinfo="skip",
                showlegend=False,
            ),
        ]
    )
    figure.update_xaxes(visible=False, range=[0, 1], fixedrange=True, constrain="domain")
    figure.update_yaxes(
        visible=False,
        range=[0.12, 0.88],
        fixedrange=True,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
    )
    figure.update_layout(
        autosize=True,
        width=None,
        height=None,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return html.Div(
        className="amazon-publishers-venn na-chart-menu-host",
        children=[
            dcc.Graph(
                figure=figure,
                responsive=True,
                config={"displayModeBar": False},
                className="amazon-publishers-venn-graph",
                style={"width": "100%", "height": "100%", "minWidth": 0},
            ),
            chart_menu_button(has_plot=True, has_table=False),
        ],
    )


def _circle_points(center_x: float, center_y: float, radius: float, steps: int = 96) -> tuple[list[float], list[float]]:
    points = [
        (
            center_x + radius * math.cos(2 * math.pi * index / steps),
            center_y + radius * math.sin(2 * math.pi * index / steps),
        )
        for index in range(steps + 1)
    ]
    return [point[0] for point in points], [point[1] for point in points]


def _category_distribution(
    records: list[dict[str, Any]],
    category_key: str,
    row_filter,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for row in records:
        if not row_filter(row):
            continue
        label = str(row.get(category_key, "")).strip() or "Unknown"
        counts[label] = counts.get(label, 0) + 1
    return [
        {"label": label, "count": count}
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    ]


def _donut_colors(count: int) -> list[str]:
    if count <= 0:
        return []
    return [DONUT_COLORS[index % len(DONUT_COLORS)] for index in range(count)]


# ---------------------------------------------------------------------------
# Detail panel builders
# ---------------------------------------------------------------------------


def _details_content(
    records: list[dict[str, Any]],
    selected_uid: str | None,
    trad_metric: str = "publications",
    some_metric: str = "posts",
    trad_timeline: list[dict[str, Any]] | None = None,
    some_timeline: list[dict[str, Any]] | None = None,
    topic_areas: list[dict[str, Any]] | None = None,
    some_topic_areas: list[dict[str, Any]] | None = None,
    top_publications: list[dict[str, Any]] | None = None,
    timeline_load_failed: bool = False,
):
    if not records:
        return html.Div(className="amazon-publishers-empty", children="No publisher data available.")
    if not selected_uid:
        return html.Div(className="amazon-publishers-empty", children="No author selected.")
    selected = find_record(records, selected_uid)
    if selected is None:
        return html.Div(className="amazon-publishers-empty", children="No publisher data available.")
    raw_platform_links = selected.get("platforms_url", "")
    raw_website_links = selected.get("website_url", "")
    profile_urls = _split_link_items(raw_platform_links)
    external_urls = _split_link_items(raw_website_links)
    link_blocks = [
        block
        for block in [
            _links_block("Website", external_urls),
            _links_block("Platforms", profile_urls),
        ]
        if block is not None
    ]
    timeline_panel = _timeline_panel(
        selected,
        trad_metric,
        some_metric,
        trad_timeline or [],
        some_timeline or [],
        load_failed=timeline_load_failed,
    )
    selected_narratives = _combined_narratives_from_record(selected)
    topic_area_panel = _topic_area_panel(selected, topic_areas or [], some_topic_areas or [])
    top_items_panel = _top_items_panel(top_publications or [])
    return html.Div(
        className="amazon-publishers-detail-content",
        children=[
            html.Div(
                className="amazon-publishers-detail-grid",
                children=[
                    html.Div(className="amazon-publishers-detail-kpis", children=_detail_kpis(selected)),
                    html.Div(
                        className="amazon-publishers-profile",
                        children=[
                            html.Div(
                                className="amazon-publishers-avatar",
                                children=_initials(str(selected.get("display_name", ""))),
                            ),
                            html.Div(
                                className="amazon-publishers-profile-body",
                                children=[
                                    html.Div(_profile_badges(selected), className="amazon-publishers-badge-row"),
                                    html.H3(selected.get("display_name", "Unknown")),
                                    _profile_block(selected),
                                    html.Div(className="amazon-publishers-links-row", children=link_blocks)
                                    if link_blocks
                                    else None,
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(className="amazon-publishers-timelines", children=[timeline_panel]),
            topic_area_panel,
            _narratives_table(selected_narratives),
            top_items_panel,
        ],
    )


def _detail_kpis(record: dict[str, Any]) -> list[html.Div]:
    trad_cards, some_cards = detail_kpi_groups(record)
    cards = trad_cards + some_cards
    return cards or [kpi_card("Items", f"{num(record, 'total_items'):,.0f}")]


def _profile_block(record: dict[str, Any]) -> html.Div:
    profile_text = _normalize_profile_text(record.get("profile_description", ""))
    if not profile_text:
        has_narratives = bool(_parsed_top_narratives(record.get("combined_top_narratives", "")))
        profile_text = (
            "Top narrative coverage is concentrated in the topics below."
            if has_narratives
            else "No publisher profile description available."
        )
    return html.Div(className="amazon-publishers-profile-summary", children=[html.P(profile_text)])


def _profile_badges(record: dict[str, Any]) -> list[html.Div]:
    badges: list[html.Div] = []
    for label in _publisher_source_labels(record):
        badges.append(html.Div(label, className="amazon-publishers-type"))
    for label in _normalize_tml_labels(record.get("is_tml") or record.get("tml_values")):
        badges.append(html.Div(label, className="amazon-publishers-type amazon-publishers-type-tml"))
    if not badges:
        badges.append(
            html.Div(
                str(record.get("publisher_type", "Unknown") or "Unknown"),
                className="amazon-publishers-type",
            )
        )
    return badges


def _publisher_source_labels(record: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    if num(record, "trad_article_count") > 0:
        labels.append("Trad")
    if num(record, "some_post_count") > 0:
        labels.append("SoMe")
    if labels:
        return labels
    publisher_type = str(record.get("publisher_type", "") or "").casefold()
    if "trad" in publisher_type:
        labels.append("Trad")
    if "some" in publisher_type:
        labels.append("SoMe")
    return labels


def _links_block(title: str, links: list[dict[str, str]]) -> html.Div | None:
    normalized_links = [
        {"label": str(link.get("label") or "").strip(), "url": normalized}
        for link in links
        if (normalized := _normalize_url(link.get("url")))
    ]
    if not normalized_links:
        return None
    return html.Div(
        className="amazon-publishers-links",
        children=[
            html.Div(title, className="amazon-publishers-links-title"),
            html.Div(
                className="amazon-publishers-link-list",
                children=[
                    html.A(
                        link["label"] or _display_url_label(link["url"]),
                        href=link["url"],
                        target="_blank",
                        rel="noopener noreferrer",
                    )
                    for link in normalized_links
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Timeline panel and figure
# ---------------------------------------------------------------------------


def _timeline_panel(
    selected: dict[str, Any],
    trad_metric: str,
    some_metric: str,
    trad_timeline: list[dict[str, Any]],
    some_timeline: list[dict[str, Any]],
    load_failed: bool = False,
) -> html.Div:
    timeline_data = {
        "publisher_uid": str(selected.get("publisher_uid", "")),
        "trad_metric": trad_metric,
        "some_metric": some_metric,
        "trad_timeline": trad_timeline,
        "some_timeline": some_timeline,
        "has_trad": num(selected, "trad_article_count") > 0,
        "has_some": num(selected, "some_post_count") > 0,
        "load_failed": load_failed,
    }
    available_sources = timeline_available_sources(timeline_data)
    selected_sources = normalize_sources(available_sources, available_sources)
    return na_panel(
        _timeline_panel_title(selected_sources, trad_metric, some_metric),
        [
            dcc.Store(id="amazon-2026-publisher-timeline-data", data=timeline_data),
            dcc.Graph(
                id="amazon-2026-publisher-timeline-graph",
                figure=timeline_figure(timeline_data, selected_sources),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=trad_some_controls(
            "amazon-2026-publisher-timeline-source",
            available_sources,
            selected_sources,
            disable_unavailable=True,
            hide_when_single=False,
        ),
    )


def _timeline_panel_title(selected_sources: list[str], trad_metric: str, some_metric: str) -> Any:
    refs = [
        ref
        for ref, condition in [
            ("P3S2G2", "Trad" in selected_sources),
            ("P3S2G3", "SoMe" in selected_sources),
        ]
        if condition
    ]
    if not refs:
        return _timeline_chart_title(trad_metric, some_metric)
    return ref_label(_timeline_chart_title(trad_metric, some_metric), " / ".join(refs))


# ---------------------------------------------------------------------------
# Topic area panel and treemap
# ---------------------------------------------------------------------------


def _topic_area_panel(
    selected: dict[str, Any],
    trad_topic_area_rows: list[dict[str, Any]],
    some_topic_area_rows: list[dict[str, Any]],
) -> html.Div:
    payload = {
        "publisher_uid": str(selected.get("publisher_uid", "")),
        "trad_topic_areas": trad_topic_area_rows,
        "some_topic_areas": some_topic_area_rows,
        "has_trad": num(selected, "trad_article_count") > 0,
        "has_some": num(selected, "some_post_count") > 0,
    }
    available_sources = _topic_area_available_sources(payload)
    selected_sources = normalize_sources(available_sources, available_sources)
    panel_title = ref_label("Publications by Topic Area", "P3S2G4")
    rows = _topic_area_rows(payload, selected_sources)
    controls = trad_some_controls(
        "amazon-2026-publisher-topic-area-source",
        available_sources,
        selected_sources,
    )
    data_child = (
        html.Div("No topic area data available.", className="amazon-publishers-empty")
        if not rows
        else dcc.Graph(
            id="amazon-2026-publisher-topic-area-treemap",
            figure=_topic_area_treemap_figure(payload, selected_sources),
            config={"displayModeBar": False, "responsive": True},
            className="amazon-publishers-timeline-graph",
        )
    )
    return na_panel(
        panel_title,
        [dcc.Store(id="amazon-2026-publisher-topic-area-data", data=payload), data_child],
        controls=controls,
    )


def _topic_area_treemap_figure(
    topic_area_data: dict[str, Any],
    selected_sources: list[str] | None = None,
) -> go.Figure:
    payload = topic_area_data or {}
    selected_sources = normalize_sources(selected_sources, _topic_area_available_sources(payload))
    rows = _topic_area_rows(payload, selected_sources)
    total_label = "Total publications and posts" if len(selected_sources) > 1 else (
        "Total posts" if selected_sources == ["SoMe"] else "Total publications"
    )
    hover_label = "Posts" if selected_sources == ["SoMe"] else (
        "Publications and Posts" if len(selected_sources) > 1 else "Publications"
    )
    labels = [str(row.get("topic_area", "Unknown")) for row in rows]
    values = [_coerce_float(row.get("value", 0)) for row in rows]
    color_map = topic_area_color_map(labels)
    fig = go.Figure()
    fig.add_trace(
        go.Treemap(
            labels=labels,
            parents=[""] * len(labels),
            values=values,
            branchvalues="total",
            marker={"colors": [color_map[label] for label in labels], "line": {"color": THEME_SURFACE, "width": 2}},
            texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}",
            textfont={"color": THEME_TEXT, "size": 14},
            hovertemplate=(
                f"%{{label}}<br>Share: %{{percentRoot:.1%}}"
                f"<br>{hover_label}: %{{value:,.0f}}<extra></extra>"
            ),
            tiling={"packing": "squarify"},
            root={"color": THEME_SURFACE_ALT},
            pathbar={"visible": False},
        )
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 25, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_TEXT},
        uniformtext={"minsize": 12, "mode": "hide"},
        annotations=[
            {
                "text": f"{total_label}: {sum(values):,.0f}",
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": 1.03,
                "showarrow": False,
                "font": {"size": 12, "color": THEME_TEXT_MUTED},
                "xanchor": "left",
            }
        ],
    )
    return fig


def _topic_area_available_sources(topic_area_data: dict[str, Any] | None) -> list[str]:
    payload = topic_area_data or {}
    available_sources: list[str] = []
    if payload.get("has_trad"):
        available_sources.append("Trad")
    if payload.get("has_some"):
        available_sources.append("SoMe")
    return available_sources


def _topic_area_rows(topic_area_data: dict[str, Any], selected_sources: list[str]) -> list[dict[str, Any]]:
    # trad_topic_areas / some_topic_areas are already filtered to the selected publisher
    combined: dict[str, float] = {}
    if "Trad" in selected_sources:
        for label, value in _topic_area_counts(
            topic_area_data.get("trad_topic_areas", []), value_key="publication_count"
        ).items():
            combined[label] = combined.get(label, 0) + value
    if "SoMe" in selected_sources:
        for label, value in _topic_area_counts(
            topic_area_data.get("some_topic_areas", []), value_key="post_count"
        ).items():
            combined[label] = combined.get(label, 0) + value
    return [
        {"topic_area": label, "value": value}
        for label, value in sorted(combined.items(), key=lambda item: (-item[1], item[0].lower()))
    ]


def _topic_area_counts(
    rows: list[dict[str, Any]],
    value_key: str = "publication_count",
) -> dict[str, float]:
    counts: dict[str, float] = {}
    for row in rows:
        label = str(row.get("topic_area", "")).strip() or "Unknown"
        counts[label] = counts.get(label, 0) + _coerce_float(row.get(value_key, 0))
    return counts


# ---------------------------------------------------------------------------
# Narratives table
# ---------------------------------------------------------------------------


def _narratives_table(rows: list[dict[str, Any]]) -> html.Div:
    title = ref_label("Top Narratives", "P3S2T1")
    available_sources = _narrative_available_sources(rows)
    selected_sources = _normalized_narrative_sources(available_sources, available_sources)
    controls = trad_some_controls(
        "amazon-2026-publisher-narratives-source",
        available_sources,
        selected_sources,
    )
    table_rows = _narratives_table_rows(rows, selected_sources)
    table_cols = _narratives_table_columns(selected_sources)
    table = dash_table.DataTable(
        id="amazon-2026-publisher-narratives-table",
        data=table_rows,
        columns=table_cols,
        merge_duplicate_headers=True,
        page_action="none",
        sort_action="native",
        style_as_list_view=True,
        style_table={"width": "100%", "overflowX": "auto", "minWidth": "100%"},
        style_cell={
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
        },
        style_header={
            "backgroundColor": THEME_SURFACE_ALT,
            "border": f"1px solid {THEME_BORDER}",
            "color": THEME_TEXT,
            "fontWeight": "700",
            "height": "34px",
            "textAlign": "center",
        },
        style_cell_conditional=_narrative_cell_width_styles(),
        style_header_conditional=_narrative_header_divider_styles(selected_sources),
        style_data_conditional=_narrative_data_bar_styles(table_rows, table_cols),
        style_data={"height": "38px"},
        css=TOOLTIP_CSS,
    )
    return na_panel(
        title,
        [
            dcc.Store(id="amazon-2026-publisher-narratives-data", data=rows),
            table,
            html.Div("No narrative data available.", className="amazon-publishers-empty") if not rows else None,
        ],
        controls=controls,
    )


def _narrative_available_sources(rows: list[dict[str, Any]]) -> list[str]:
    available_sources: list[str] = []
    if any(num(row, "trad_publications") > 0 or num(row, "trad_reach") > 0 for row in rows):
        available_sources.append("Trad")
    if any(num(row, "some_posts") > 0 or num(row, "some_reach") > 0 for row in rows):
        available_sources.append("SoMe")
    return available_sources





def _narrative_cell_width_styles() -> list[dict[str, Any]]:
    metric_width = {"width": "140px", "maxWidth": "140px", "minWidth": "140px"}
    return [
        {
            "if": {"column_id": "narrative_label"},
            "width": "320px",
            "maxWidth": "320px",
            "minWidth": "320px",
            "textAlign": "left",
            "fontWeight": "700",
        },
        *[
            {"if": {"column_id": column}, **metric_width, "textAlign": "right"}
            for column in [*NARRATIVE_TRAD_COLUMNS, *NARRATIVE_SOME_COLUMNS]
        ],
    ]


def _narratives_table_rows(rows: list[dict[str, Any]], source_filter: list[str] | str | None) -> list[dict[str, Any]]:
    selected_sources = _filter_trad_some(source_filter)
    if not selected_sources:
        return []
    show_trad = "Trad" in selected_sources
    show_some = "SoMe" in selected_sources
    selected_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        trad_publications = num(row, "trad_publications")
        trad_reach = num(row, "trad_reach")
        some_posts = num(row, "some_posts")
        some_reach = num(row, "some_reach")
        if show_trad and not show_some and trad_publications <= 0 and trad_reach <= 0:
            continue
        if show_some and not show_trad and some_posts <= 0 and some_reach <= 0:
            continue
        if show_trad and show_some and trad_publications <= 0 and trad_reach <= 0 and some_posts <= 0 and some_reach <= 0:
            continue
        selected_rows.append(
            {
                "row_id": idx,
                "narrative_label": row.get("narrative_label", ""),
                **{column: num(row, column) if show_trad else 0 for column in NARRATIVE_TRAD_COLUMNS},
                **{column: num(row, column) if show_some else 0 for column in NARRATIVE_SOME_COLUMNS},
            }
        )
    return sorted(
        selected_rows,
        key=lambda item: (
            -(num(item, "trad_reach") + num(item, "some_reach")),
            -num(item, "trad_reach"),
            -num(item, "some_reach"),
            -num(item, "trad_publications"),
            -num(item, "some_posts"),
            str(item.get("narrative_label", "")),
        ),
    )[:12]


def _combined_narratives_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    sources = [
        (
            "trad_top_narratives",
            {
                "publications": "trad_publications",
                "reach": "trad_reach",
                "positive_share_of_reach": "trad_positive_share_of_reach",
                "negative_share_of_reach": "trad_negative_share_of_reach",
            },
        ),
        (
            "some_top_narratives",
            {
                "posts": "some_posts",
                "reach": "some_reach",
                "engagement": "some_engagement",
                "average_engagement": "some_average_engagement",
                "positive_share_of_reach": "some_positive_share_of_reach",
                "negative_share_of_reach": "some_negative_share_of_reach",
            },
        ),
    ]
    for field_name, field_map in sources:
        for item in _parsed_top_narratives(record.get(field_name, "")):
            item_key = str(item.get("narrative_id") or "").strip() or str(item.get("narrative_label", "")).casefold()
            if not item_key:
                continue
            current = combined.setdefault(
                item_key,
                {
                    "narrative_id": item.get("narrative_id", ""),
                    "narrative_label": item.get("narrative_label", "")
                    or str(item.get("narrative_id", "") or "").strip(),
                    **{column: 0.0 for column in [*NARRATIVE_TRAD_COLUMNS, *NARRATIVE_SOME_COLUMNS]},
                    "total_reach": 0.0,
                },
            )
            if item.get("narrative_label"):
                current["narrative_label"] = item["narrative_label"]
            elif not current.get("narrative_label") and item.get("narrative_id"):
                current["narrative_label"] = str(item["narrative_id"]).strip()
            if not current.get("narrative_id") and item.get("narrative_id"):
                current["narrative_id"] = item["narrative_id"]
            for source_key, target_key in field_map.items():
                current[target_key] = _coerce_float(current.get(target_key, 0)) + _coerce_float(item.get(source_key, 0))

    rows = []
    for row in combined.values():
        row["total_reach"] = _coerce_float(row.get("trad_reach", 0)) + _coerce_float(row.get("some_reach", 0))
        rows.append(row)
    return sorted(
        rows,
        key=lambda item: (
            -num(item, "total_reach"),
            -num(item, "trad_publications"),
            -num(item, "some_posts"),
            str(item.get("narrative_label", "")),
        ),
    )


# ---------------------------------------------------------------------------
# Top items panel and tables
# ---------------------------------------------------------------------------


def _top_items_panel(top_publications: list[dict[str, Any]]) -> html.Div:
    trad_table_data, some_table_data = build_top_items_table_data(top_publications)
    return build_top_items_panel(
        "amazon-2026-publisher",
        ref_label("Top Publications / Posts", "P3S2T2"),
        trad_table_data,
        some_table_data,
    )


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Narrative data helpers
# ---------------------------------------------------------------------------


def _parsed_top_narratives(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    decoded = _decode_jsonish_value(value)
    if not isinstance(decoded, list):
        return []
    items = []
    for item in decoded:
        if not isinstance(item, dict):
            continue
        narrative_id = str(item.get("narrative_id") or "").strip()
        label = str(item.get("label") or item.get("narrative_label") or narrative_id or "").strip()
        if not label and not narrative_id:
            continue
        items.append(
            {
                "narrative_id": narrative_id,
                "narrative_label": label or narrative_id,
                "publications": _coerce_float(item.get("publications", 0)),
                "posts": _coerce_float(item.get("posts", 0)),
                "reach": _coerce_float(item.get("reach", 0)),
                "engagement": _coerce_float(item.get("engagement", 0)),
                "average_engagement": _coerce_float(item.get("average_engagement", 0)),
                "positive_share_of_reach": _coerce_float(
                    item.get("share_of_positive_reach", item.get("positive_sentiment_share_of_reach", 0))
                ) / 100,
                "negative_share_of_reach": _coerce_float(
                    item.get("share_of_negative_reach", item.get("negative_sentiment_share_of_reach", 0))
                ) / 100,
            }
        )
    return items


def _decode_jsonish_value(value: Any) -> Any:
    decoded = value
    for _ in range(2):
        if not isinstance(decoded, str):
            break
        stripped = decoded.strip()
        if not stripped:
            return ""
        try:
            decoded = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            return stripped
    return decoded


# ---------------------------------------------------------------------------
# URL and string utilities
# ---------------------------------------------------------------------------


def _split_link_items(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, list):
        nested: list[dict[str, str]] = []
        for item in value:
            nested.extend(_split_link_items(item))
        return nested
    if isinstance(value, dict):
        return _dict_to_link_items(value)
    value_str = str(value).strip()
    if not value_str:
        return []
    decoded_full = _decode_link_value(value_str)
    if isinstance(decoded_full, dict):
        return _dict_to_link_items(decoded_full)
    if isinstance(decoded_full, list):
        nested = []
        for item in decoded_full:
            nested.extend(_split_link_items(item))
        return nested
    if isinstance(decoded_full, str):
        normalized = decoded_full.strip()
        return [{"label": "", "url": normalized}] if normalized else []

    values: list[dict[str, str]] = []
    for item in _split_values(value_str):
        decoded = _decode_link_value(item)
        if isinstance(decoded, dict):
            values.extend(_dict_to_link_items(decoded))
        elif isinstance(decoded, list):
            values.extend(_split_link_items(decoded))
        else:
            cleaned = str(decoded).strip().strip('"')
            if cleaned:
                values.append({"label": "", "url": cleaned})
    seen: set[tuple[str, str]] = set()
    unique_urls: list[dict[str, str]] = []
    for item in values:
        label = str(item.get("label") or "").strip()
        cleaned = str(item.get("url") or "").strip()
        if not cleaned:
            continue
        dedupe_key = (label.casefold(), cleaned.casefold())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique_urls.append({"label": label, "url": cleaned})
    return unique_urls


def _dict_to_link_items(value: dict[Any, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key, raw_url in value.items():
        label = str(key).strip()
        if isinstance(raw_url, list):
            for nested_url in raw_url:
                cleaned = str(nested_url).strip().strip('"')
                if cleaned:
                    items.append({"label": label, "url": cleaned})
            continue
        cleaned = str(raw_url).strip().strip('"')
        if cleaned:
            items.append({"label": label, "url": cleaned})
    return items


def _decode_link_value(value: Any) -> Any:
    decoded = value
    for _ in range(4):
        if isinstance(decoded, (dict, list)):
            return decoded
        value_str = str(decoded).strip()
        if not value_str:
            return ""
        try:
            next_decoded = json.loads(value_str)
        except (json.JSONDecodeError, TypeError):
            return value_str
        if next_decoded == decoded:
            return next_decoded
        decoded = next_decoded
    return decoded


def _normalize_url(value: Any) -> str:
    if value is None:
        return ""
    url = str(value).strip().strip('"').strip("'")
    if not url:
        return ""
    if url.lower().startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if "." in url and " " not in url:
        return f"https://{url}"
    return ""


def _display_url_label(url: str) -> str:
    display = url.removeprefix("https://").removeprefix("http://")
    return display[:-1] if display.endswith("/") else display


def _normalize_profile_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    idx = next((i for i, c in enumerate(text) if c.isalpha()), -1)
    if idx == -1:
        return text
    return text[:idx] + text[idx].upper() + text[idx + 1:]


def _normalize_tml_labels(value: Any) -> list[str]:
    labels: list[str] = []
    for item in _split_values(value):
        normalized = str(item).strip().casefold()
        if normalized in {"true", "treu", "tml", "yes", "1"}:
            label = "TML"
        elif normalized in {"false", "non-tml", "non tml", "no", "0"}:
            label = "non-TML"
        else:
            continue
        if label not in labels:
            labels.append(label)
    return labels


def _split_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = str(value).replace("|", ",").split(",")
    return [str(item).strip() for item in raw_values if str(item).strip()]


def _author_options(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"label": str(record.get("display_name", "Unknown")), "value": str(record.get("publisher_uid", ""))}
        for record in records
    ]


def _filter_options(records: list[dict[str, Any]], column: str) -> list[dict[str, str]]:
    values = sorted({value for record in records for value in _split_values(record.get(column, ""))})
    return [{"label": value, "value": value} for value in values]


# ---------------------------------------------------------------------------
# Primitive utilities
# ---------------------------------------------------------------------------


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part]
    if not parts:
        return "NA"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][0]}{parts[-1][0]}".upper()
