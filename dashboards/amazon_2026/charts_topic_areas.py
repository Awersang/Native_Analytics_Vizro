"""Charts and components for the Topic Areas page."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html

from dashboards.amazon_2026.charts_campaigns import _campaign_table_records, build_campaign_details_section
from dashboards.amazon_2026.charts_publishers import (
    SOURCE_OPTIONS,
    _cell_width_styles,
    _data_bar_styles,
    _dev_inline_label,
    _header_divider_styles,
    _table_columns,
    _table_records,
)
from dashboards.amazon_2026.charts_shared import (
    THEME_BORDER,
    THEME_SURFACE,
    THEME_SURFACE_ALT,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    TRAD_SOME_OPTIONS,
    _coerce_float,
    _hex_to_rgba,
    _json_safe,
    _normalize_sources,
    build_overview_table_section,
    media_label_color,
    na_panel,
    topic_area_color_map,
)
from dashboards.amazon_2026.dev_ids import ref_label


def _topic_area_breakdown_records(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in ["topic_area", "theme", "source"]:
        if column not in df.columns:
            df[column] = ""
    for column in ["publications", "reach"]:
        if column not in df.columns:
            df[column] = 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return [_json_safe(record) for record in df.to_dict("records")]


def _topic_area_available_sources(records: list[dict[str, Any]]) -> list[str]:
    sources = {str(record.get("source", "")) for record in records}
    return [source for source in ["Trad", "SoMe"] if source in sources]


def _topic_area_theme_rows(
    records: list[dict[str, Any]],
    selected_sources: list[str],
    basic_metric: str,
) -> list[dict[str, Any]]:
    value_key = "reach" if basic_metric == "reach" else "publications"
    combined: dict[tuple[str, str], float] = {}
    for record in records:
        if str(record.get("source", "")) not in selected_sources:
            continue
        topic_area = str(record.get("topic_area") or "Unknown")
        theme = str(record.get("theme") or "Unknown")
        value = _coerce_float(record.get(value_key, 0))
        key = (topic_area, theme)
        combined[key] = combined.get(key, 0) + value
    return [
        {"topic_area": topic_area, "theme": theme, "value": value}
        for (topic_area, theme), value in combined.items()
        if value > 0
    ]


def _topic_area_theme_treemap_figure(
    records: list[dict[str, Any]],
    selected_sources: list[str] | None,
    basic_metric: str,
) -> go.Figure:
    selected_sources = _normalize_sources(selected_sources, _topic_area_available_sources(records))
    rows = _topic_area_theme_rows(records, selected_sources, basic_metric)

    is_reach = basic_metric == "reach"
    if is_reach:
        total_label = "Total reach and engagement" if len(selected_sources) > 1 else (
            "Total engagement" if selected_sources == ["SoMe"] else "Total reach"
        )
        hover_label = "Engagement" if selected_sources == ["SoMe"] else (
            "Reach and Engagement" if len(selected_sources) > 1 else "Reach"
        )
    else:
        total_label = "Total publications and posts" if len(selected_sources) > 1 else (
            "Total posts" if selected_sources == ["SoMe"] else "Total publications"
        )
        hover_label = "Posts" if selected_sources == ["SoMe"] else (
            "Publications and Posts" if len(selected_sources) > 1 else "Publications"
        )

    fig = go.Figure()

    if not rows:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": THEME_TEXT},
            annotations=[
                {
                    "text": "No topic area data available.",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 14, "color": THEME_TEXT_MUTED},
                }
            ],
        )
        return fig

    topic_area_totals: dict[str, float] = {}
    for row in rows:
        topic_area_totals[row["topic_area"]] = topic_area_totals.get(row["topic_area"], 0) + row["value"]
    topic_areas = sorted(topic_area_totals, key=lambda topic_area: (-topic_area_totals[topic_area], topic_area.lower()))
    color_map = topic_area_color_map(topic_areas)

    ids: list[str] = []
    labels: list[str] = []
    parents: list[str] = []
    values: list[float] = []
    colors: list[str | None] = []

    line_colors: list[str] = []
    line_widths: list[float] = []

    for topic_area in topic_areas:
        ids.append(topic_area)
        labels.append(topic_area)
        parents.append("")
        values.append(topic_area_totals[topic_area])
        colors.append(color_map[topic_area])
        line_colors.append(THEME_SURFACE_ALT)
        line_widths.append(0)

    for row in sorted(rows, key=lambda row: (-row["value"], row["theme"].lower())):
        ids.append(f"{row['topic_area']}::{row['theme']}")
        labels.append(row["theme"])
        parents.append(row["topic_area"])
        values.append(row["value"])
        colors.append(None)
        line_colors.append("rgba(255,255,255,0.55)")
        line_widths.append(1)

    fig.add_trace(
        go.Treemap(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker={"colors": colors, "line": {"color": line_colors, "width": line_widths}},
            texttemplate="<b>%{label}</b><br>%{value:,.0f}",
            textfont={"color": THEME_TEXT, "size": 13},
            hovertemplate=(
                f"%{{label}}<br>{hover_label}: %{{value:,.0f}}"
                f"<br>Share of total: %{{percentRoot:.1%}}<extra></extra>"
            ),
            tiling={"packing": "squarify", "pad": 3},
            pathbar={"visible": True},
        )
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 25, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_TEXT},
        uniformtext={"minsize": 11, "mode": "hide"},
        annotations=[
            {
                "text": f"{total_label}: {sum(topic_area_totals.values()):,.0f}",
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


def build_topic_area_treemap_section(records: list[dict[str, Any]]) -> html.Div:
    available_sources = _topic_area_available_sources(records)
    selected_sources = _normalize_sources(available_sources, available_sources)
    basic_metric = "publications"
    controls = html.Div(
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if len(available_sources) <= 1 else None,
        children=[
            dcc.Checklist(
                id="amazon-2026-topic-area-source",
                options=TRAD_SOME_OPTIONS,
                value=selected_sources,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )
    return na_panel(
        ref_label("Publications by Topic Area and Theme", "P6S1G1"),
        [
            dcc.Store(id="amazon-2026-topic-area-data", data=records),
            dcc.Graph(
                id="amazon-2026-topic-area-treemap",
                figure=_topic_area_theme_treemap_figure(records, selected_sources, basic_metric),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=controls,
    )


# ---------------------------------------------------------------------------
# Media / Platform -> Topic Area sankey
# ---------------------------------------------------------------------------


def _topic_area_media_records(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for column in ["media_label", "topic_area", "source"]:
        if column not in df.columns:
            df[column] = ""
    for column in ["publications", "reach"]:
        if column not in df.columns:
            df[column] = 0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)
    return [_json_safe(record) for record in df.to_dict("records")]


def _topic_area_media_available_sources(records: list[dict[str, Any]]) -> list[str]:
    sources = {str(record.get("source", "")) for record in records}
    return [source for source in ["Trad", "SoMe"] if source in sources]


# Links below this share of total publications are hidden as visual noise.
SANKEY_MIN_SHARE = 0.005


def _topic_area_media_sankey_figure(
    records: list[dict[str, Any]],
    selected_sources: list[str] | None,
    basic_metric: str = "publications",
) -> go.Figure:
    available_sources = _topic_area_media_available_sources(records)
    selected_sources = _normalize_sources(selected_sources, available_sources)
    value_key = "reach" if basic_metric == "reach" else "publications"

    if value_key == "reach":
        value_label = "Engagement" if selected_sources == ["SoMe"] else (
            "Reach and Engagement" if len(selected_sources) > 1 else "Reach"
        )
        total_label = "Total reach and engagement" if len(selected_sources) > 1 else (
            "Total engagement" if selected_sources == ["SoMe"] else "Total reach"
        )
    else:
        value_label = "Posts" if selected_sources == ["SoMe"] else (
            "Publications and Posts" if len(selected_sources) > 1 else "Publications"
        )
        total_label = "Total publications and posts" if len(selected_sources) > 1 else (
            "Total posts" if selected_sources == ["SoMe"] else "Total publications"
        )

    rows: dict[tuple[str, str], float] = {}
    for record in records:
        if str(record.get("source", "")) not in selected_sources:
            continue
        media_label = str(record.get("media_label") or "Unknown")
        topic_area = str(record.get("topic_area") or "Unknown")
        value = _coerce_float(record.get(value_key, 0))
        if value <= 0:
            continue
        key = (media_label, topic_area)
        rows[key] = rows.get(key, 0) + value

    total_value = sum(rows.values())
    if total_value > 0:
        threshold = total_value * SANKEY_MIN_SHARE
        rows = {key: value for key, value in rows.items() if value >= threshold}

    media_labels: list[str] = []
    topic_areas: list[str] = []
    for media_label, topic_area in rows:
        if media_label not in media_labels:
            media_labels.append(media_label)
        if topic_area not in topic_areas:
            topic_areas.append(topic_area)

    fig = go.Figure()

    if not rows:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": THEME_TEXT},
            annotations=[
                {
                    "text": "No topic area media data available.",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 14, "color": THEME_TEXT_MUTED},
                }
            ],
        )
        return fig

    media_labels = sorted(media_labels, key=str.lower)
    topic_area_totals: dict[str, float] = {}
    for (media_label, topic_area), value in rows.items():
        topic_area_totals[topic_area] = topic_area_totals.get(topic_area, 0) + value
    topic_areas = sorted(topic_area_totals, key=lambda topic_area: (-topic_area_totals[topic_area], topic_area.lower()))
    color_map = topic_area_color_map(topic_areas)

    media_sources = {record["media_label"]: record["source"] for record in records}

    nodes = [*media_labels, *topic_areas]
    node_index = {label: index for index, label in enumerate(nodes)}
    node_colors = [
        media_label_color(label, media_sources.get(label)) for label in media_labels
    ] + [color_map[topic_area] for topic_area in topic_areas]

    link_sources: list[int] = []
    link_targets: list[int] = []
    link_values: list[float] = []
    link_colors: list[str] = []
    link_labels: list[str] = []
    for (media_label, topic_area), value in rows.items():
        link_sources.append(node_index[media_label])
        link_targets.append(node_index[topic_area])
        link_values.append(value)
        link_colors.append(_hex_to_rgba(color_map[topic_area], 0.35))
        link_labels.append(f"{media_label} -> {topic_area}")

    fig.add_trace(
        go.Sankey(
            arrangement="snap",
            node={
                "label": nodes,
                "color": node_colors,
                "pad": 14,
                "thickness": 16,
                "line": {"color": THEME_SURFACE_ALT, "width": 0},
                "hovertemplate": f"%{{label}}<br>{value_label}: %{{value:,.0f}}<extra></extra>",
            },
            link={
                "source": link_sources,
                "target": link_targets,
                "value": link_values,
                "color": link_colors,
                "label": link_labels,
                "hovertemplate": f"%{{label}}<br>{value_label}: %{{value:,.0f}}<extra></extra>",
            },
            textfont={"color": THEME_TEXT, "size": 12},
        )
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 25, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_TEXT},
        hoverlabel={"bgcolor": THEME_SURFACE, "bordercolor": THEME_BORDER, "font": {"color": THEME_TEXT, "size": 12}},
        annotations=[
            {
                "text": f"{total_label}: {sum(link_values):,.0f}",
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


def build_topic_area_media_sankey_section(records: list[dict[str, Any]], basic_metric: str = "publications") -> html.Div:
    available_sources = _topic_area_media_available_sources(records)
    selected_sources = _normalize_sources(available_sources, available_sources)
    controls = html.Div(
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if len(available_sources) <= 1 else None,
        children=[
            dcc.Checklist(
                id="amazon-2026-topic-area-media-source",
                options=TRAD_SOME_OPTIONS,
                value=selected_sources,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )
    return na_panel(
        ref_label("Publications by Media Source and Topic Area", "P6S2G1"),
        [
            dcc.Store(id="amazon-2026-topic-area-media-data", data=records),
            dcc.Graph(
                id="amazon-2026-topic-area-media-sankey",
                figure=_topic_area_media_sankey_figure(records, selected_sources, basic_metric),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=controls,
    )


# ---------------------------------------------------------------------------
# Campaigns overview table + details
# ---------------------------------------------------------------------------


def build_topic_area_overview_section(data_frame: pd.DataFrame) -> html.Div:
    records = _campaign_table_records(data_frame, id_column="topic_area")
    table_data = _table_records(records)
    columns = _table_columns("All")
    columns[0] = {"name": ["", "Topic Area"], "id": "display_name"}
    controls = html.Div(
        className="amazon-publishers-controls",
        children=[
            html.Div(
                className="amazon-publishers-control amazon-publishers-source-control",
                children=[
                    html.Div("Source", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-topic-area-overview-source-filter",
                        options=SOURCE_OPTIONS,
                        value="All",
                        clearable=False,
                        searchable=False,
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
        ],
    )
    return build_overview_table_section(
        records=records,
        store_id="amazon-2026-topic-area-overview-data",
        section_title=ref_label("Topic Areas Overview", "P6S3"),
        controls=controls,
        dev_label=_dev_inline_label("P6S3T1", "Topic Areas Table"),
        table_id="amazon-2026-topic-area-overview-table",
        table_data=table_data,
        columns=columns,
        style_cell_conditional=_cell_width_styles(),
        style_header_conditional=_header_divider_styles(columns),
        style_data_conditional=_data_bar_styles(table_data, columns),
    )


def build_topic_area_details_section(data_frame: pd.DataFrame) -> html.Div:
    return build_campaign_details_section(
        data_frame,
        id_prefix="amazon-2026-ta-topicarea",
        ref_prefix="P6S4",
        header_label="Topic Area Details",
        filter_column="topic_area",
        selector_label="Topic Area",
        placeholder="Select topic area…",
        empty_label="Select a topic area to see details.",
    )
