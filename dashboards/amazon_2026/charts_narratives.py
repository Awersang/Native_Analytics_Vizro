"""Narratives page components — chart builders and data transforms."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, dcc, html
from plotly.subplots import make_subplots
from dash.dash_table.Format import Format, Scheme

from dashboards.amazon_2026.theme import (
    NARRATIVE_LINE_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_ROW_ODD,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    WEEKLY_DTICK_MS,
    hex_to_rgba,
    theme_hoverlabel,
)
from dashboards.amazon_2026.timeline_charts import (
    _add_empty_figure_annotation,
    _timeline_chart_title,
    media_split_timeline_figure,
    normalize_sources,
    timeline_available_sources,
    timeline_figure,
    top_reach_flags,
)
from dashboards.amazon_2026.ui_components import (
    NARRATIVE_SOME_COLUMNS,
    NARRATIVE_TRAD_COLUMNS,
    OVERVIEW_TABLE_STYLE_CELL,
    OVERVIEW_TABLE_STYLE_HEADER,
    TOP_TABLES_PAGE_SIZE,
    TOP_TABLE_STYLE_CELL,
    TOP_TABLE_STYLE_HEADER,
    TRAD_SOME_OPTIONS,
    _apply_detail_weekly_layout,
    _data_bar_column_styles,
    _narrative_data_bar_styles,
    capture,
    _narrative_header_divider_styles,
    _narratives_table_columns,
    build_shared_x_range,
    build_top_items_panel,
    build_top_items_table_data,
    data_load_failed,
    detail_weekly_figure,
    donut_figure,
    donut_panel,
    empty_donut_panel,
    json_safe,
    kpi_card,
    load_and_filter,
    na_panel,
    num,
    safe_load,
    sentiment_donut_slices,
    timeline_records_from_frame,
    top_journalists_data_bar_styles,
    top_journalists_table_columns,
    top_journalists_table_rows,
    top_publishers_data_bar_styles,
    top_publishers_table_columns,
    top_publishers_table_rows,
    trad_some_controls,
)

from dashboards.amazon_2026.data_common import (
    ANGLES_KEY,
    NARRATIVE_SOME_PLATFORM_TIMELINE_KEY,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY,
    NARRATIVE_TOP_JOURNALISTS_KEY,
    NARRATIVE_TOP_PUBLISHERS_KEY,
    NARRATIVE_TOP_PUBLICATIONS_KEY,
    NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_WEEKLY_REACH_KEY,
    NARRATIVES_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label

logger = logging.getLogger(__name__)

NARRATIVES_SOURCE_OPTIONS = [
    {"label": "All", "value": "All"},
    {"label": "Trad", "value": "Trad"},
    {"label": "SoMe", "value": "SoMe"},
]

NARRATIVE_MEDIA_SPLIT_HEIGHT_SCALE = 1.3


def _norm_source(sf: str | list[str] | None) -> list[str]:
    """Convert any source filter to the ["Trad", "SoMe"] form that the helpers expect."""
    return normalize_sources(sf, ["Trad", "SoMe"])

# ---------------------------------------------------------------------------
# Public section builder (called by @capture wrapper in narratives.py)
# ---------------------------------------------------------------------------


def build_narratives_overview_section(data_frame: pd.DataFrame) -> html.Div:
    records = _overview_records_from_frame(data_frame)
    norm = _norm_source("All")
    table_rows = _overview_table_rows(records, norm)
    columns = _narratives_table_columns(norm)
    table_label = ref_label("Narratives Overview Table", "P2S3T1")
    return html.Div(
        className="amazon-publishers-section",
        children=[
            dcc.Store(id="amazon-2026-narratives-overview-data", data=records),
            html.Div(
                className="na-element-title",
                children=table_label,
                style={"marginBottom": "8px"},
            ),
            html.Div(
                className="amazon-publishers-controls",
                children=[
                    html.Div(
                        className="amazon-publishers-control amazon-publishers-source-control",
                        children=[
                            html.Div("Source", className="amazon-publishers-control-label"),
                            dcc.Dropdown(
                                id="amazon-2026-narratives-source-filter",
                                options=NARRATIVES_SOURCE_OPTIONS,
                                value="All",
                                clearable=False,
                                searchable=False,
                                className="amazon-publishers-dropdown",
                            ),
                        ],
                    ),
                ],
            ),
            dash_table.DataTable(
                id="amazon-2026-narratives-overview-table",
                data=table_rows,
                columns=columns,
                merge_duplicate_headers=True,
                page_size=15,
                sort_action="native",
                filter_action="none",
                cell_selectable=True,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=OVERVIEW_TABLE_STYLE_CELL,
                style_header=OVERVIEW_TABLE_STYLE_HEADER,
                style_cell_conditional=_overview_cell_width_styles(),
                style_header_conditional=_narrative_header_divider_styles(norm),
                style_data_conditional=_narrative_data_bar_styles(table_rows, columns),
                css=[
                    {"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"},
                    {
                        "selector": "td[data-dash-column='narrative_label'] .dash-cell-value",
                        "rule": "pointer-events: none; cursor: pointer;",
                    },
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Data transforms
# ---------------------------------------------------------------------------


def _overview_records_from_frame(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for col in [
        "narrative_label",
        "trad_publications",
        "trad_reach",
        "trad_positive_share_of_reach",
        "trad_negative_share_of_reach",
        "some_posts",
        "some_reach",
        "some_engagement",
        "some_average_engagement",
        "some_positive_share_of_reach",
        "some_negative_share_of_reach",
    ]:
        if col not in df.columns:
            df[col] = 0 if col != "narrative_label" else ""
    for col in [c for c in df.columns if c != "narrative_label"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["narrative_label"] = df["narrative_label"].fillna("").astype(str)
    df = df[df["narrative_label"].str.strip() != ""]
    return [json_safe(row) for row in df.to_dict("records")]



def _overview_table_rows(
    records: list[dict[str, Any]],
    source_filter: str | list[str] | None,
) -> list[dict[str, Any]]:
    selected = _norm_source(source_filter)
    show_trad = "Trad" in selected
    show_some = "SoMe" in selected
    rows = []
    for idx, record in enumerate(records):
        trad_pub = num(record, "trad_publications")
        trad_reach = num(record, "trad_reach")
        some_posts = num(record, "some_posts")
        some_reach = num(record, "some_reach")
        if show_trad and not show_some and trad_pub <= 0 and trad_reach <= 0:
            continue
        if show_some and not show_trad and some_posts <= 0 and some_reach <= 0:
            continue
        label = record.get("narrative_label", "")
        rows.append(
            {
                "id": label,
                "row_id": idx,
                "narrative_label": label,
                **{col: num(record, col) if show_trad else 0 for col in NARRATIVE_TRAD_COLUMNS},
                **{col: num(record, col) if show_some else 0 for col in NARRATIVE_SOME_COLUMNS},
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Style helpers specific to the overview table
# ---------------------------------------------------------------------------


def _overview_cell_width_styles() -> list[dict[str, Any]]:
    metric_width = {"width": "150px", "maxWidth": "150px", "minWidth": "150px"}
    return [
        {
            "if": {"column_id": "narrative_label"},
            "width": "300px",
            "maxWidth": "300px",
            "minWidth": "300px",
            "textAlign": "left",
            "fontWeight": "700",
        },
        *[
            {"if": {"column_id": col}, **metric_width, "textAlign": "right"}
            for col in [*NARRATIVE_TRAD_COLUMNS, *NARRATIVE_SOME_COLUMNS]
        ],
    ]


def overview_table_columns(source_filter: str | list[str] | None) -> list[dict[str, Any]]:
    """Return DataTable column definitions, normalising 'All' to both sources."""
    return _narratives_table_columns(_norm_source(source_filter))


# ---------------------------------------------------------------------------
# Weekly reach by narratives line chart
# ---------------------------------------------------------------------------

_NARRATIVE_LINE_COLORS = NARRATIVE_LINE_COLORS

def build_narratives_combined_timeline_section(data_frame: pd.DataFrame) -> html.Div:
    trad_df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    some_df = safe_load(NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY)

    shared_color_map = _build_shared_color_map(trad_df, some_df)
    x_range = build_shared_x_range(trad_df, some_df)

    initial_fig = _narrative_weekly_figure(
        trad_df, "weekly_reach", "weekly_publications", "pubs", "Weekly Reach",
        color_map=shared_color_map,
        x_range=x_range,
    )

    return na_panel(
        html.Span(id="amazon-2026-narratives-timeline-title", children=ref_label("Weekly Reach by Narrative", "P2S2G1")),
        [
            dcc.Store(
                id="amazon-2026-narratives-timeline-store",
                data={
                    "trad": trad_df.to_dict("records") if not trad_df.empty else [],
                    "some": some_df.to_dict("records") if not some_df.empty else [],
                    "color_map": shared_color_map,
                    "x_range": x_range,
                    "load_failed": data_load_failed(trad_df, some_df),
                },
            ),
            dcc.Graph(
                id="amazon-2026-narratives-timeline-graph",
                figure=initial_fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "520px"},
            ),
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.RadioItems(
                    id="amazon-2026-narratives-timeline-source",
                    options=[
                        {"label": "Trad Reach", "value": "Trad"},
                        {"label": "Trad Multiples", "value": "Trad-Multi"},
                        {"label": "SoMe Engagement", "value": "SoMe"},
                        {"label": "SoMe Multiples", "value": "SoMe-Multi"},
                    ],
                    value="Trad",
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


def _build_shared_color_map(trad_df: pd.DataFrame, some_df: pd.DataFrame) -> dict[str, str]:
    trad_top: list[str] = []
    if not trad_df.empty and "dominant_narrative" in trad_df.columns and "weekly_reach" in trad_df.columns:
        trad_top = (
            trad_df.groupby("dominant_narrative")["weekly_reach"]
            .sum().nlargest(10).index.tolist()
        )
    some_top: list[str] = []
    if not some_df.empty and "dominant_narrative" in some_df.columns and "weekly_engagement" in some_df.columns:
        some_top = (
            some_df.groupby("dominant_narrative")["weekly_engagement"]
            .sum().nlargest(10).index.tolist()
        )
    all_narratives = list(dict.fromkeys(trad_top + some_top))
    return {n: _NARRATIVE_LINE_COLORS[i % len(_NARRATIVE_LINE_COLORS)] for i, n in enumerate(all_narratives)}



def _narrative_weekly_figure(
    data_frame: pd.DataFrame,
    metric_col: str,
    count_col: str,
    count_label: str,
    y_title: str,
    color_map: dict[str, str] | None = None,
    x_range: list[str] | None = None,
    load_failed: bool = False,
) -> go.Figure:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    failed = load_failed or data_load_failed(df)
    fig = go.Figure()
    if df.empty or "dominant_narrative" not in df.columns:
        _add_empty_figure_annotation(fig, "Data temporarily unavailable" if failed else "No data available")
        _apply_detail_weekly_layout(fig, y_title, dtick=WEEKLY_DTICK_MS)
        return fig

    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
    df[count_col] = pd.to_numeric(
        df[count_col] if count_col in df.columns else 0,
        errors="coerce",
    ).fillna(0).astype(int)
    df = df.dropna(subset=["week_start", "dominant_narrative"])

    if color_map:
        top_narratives = [n for n in color_map if n in df["dominant_narrative"].values]
        narrative_colors = {n: color_map[n] for n in top_narratives}
    else:
        top_narratives = (
            df.groupby("dominant_narrative")[metric_col]
            .sum()
            .nlargest(10)
            .index.tolist()
        )
        narrative_colors = {
            n: _NARRATIVE_LINE_COLORS[i % len(_NARRATIVE_LINE_COLORS)]
            for i, n in enumerate(top_narratives)
        }

    # Visible traces — full y values, no NaN; tooltip handled by the hover trace below
    for narrative, color in narrative_colors.items():
        sub = df[df["dominant_narrative"] == narrative].sort_values("week_start")
        fig.add_trace(
            go.Scatter(
                x=sub["week_start"],
                y=sub[metric_col],
                name=narrative,
                mode="lines+markers",
                line=dict(width=2.5, color=color, shape="spline", smoothing=0.45),
                marker=dict(size=5, color=color),
                fill="tozeroy",
                fillcolor=hex_to_rgba(color, 0.12),
                hoverinfo="skip",
            )
        )

    # Invisible hover trace: one point per week, sorted + filtered tooltip text
    _THRESHOLD = 0.02
    weeks = sorted(df["week_start"].unique())
    hover_texts: list[str] = []
    hover_y: list[float] = []
    for week in weeks:
        wdf = df[df["week_start"] == week]
        week_max = float(wdf[metric_col].max() or 1)
        rows: list[tuple[str, int, int, str]] = []
        for narrative in top_narratives:
            nrow = wdf[wdf["dominant_narrative"] == narrative]
            if nrow.empty:
                continue
            value = int(nrow[metric_col].iloc[0])
            count = int(nrow[count_col].iloc[0])
            if value >= week_max * _THRESHOLD:
                rows.append((narrative, value, count, narrative_colors[narrative]))
        rows.sort(key=lambda r: r[1], reverse=True)

        if rows:
            entries = []
            for narrative, value, count, color in rows:
                count_str = f" · {count:,} {count_label}" if count > 0 else ""
                entries.append(
                    f'<span style="color:{color}">&#9632;</span> <b>{narrative}</b>'
                    f"<br>{y_title}: {value:,.0f}{count_str}"
                )
            hover_texts.append("<br><br>".join(entries))
        else:
            hover_texts.append("No notable coverage")
        hover_y.append(week_max)

    fig.add_trace(
        go.Scatter(
            x=weeks,
            y=hover_y,
            mode="markers",
            marker=dict(size=10, opacity=0),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_texts,
            showlegend=False,
            name="",
        )
    )

    _apply_detail_weekly_layout(fig, y_title, x_range, dtick=WEEKLY_DTICK_MS)
    return fig



def _narrative_small_multiples_figure(
    data_frame: pd.DataFrame,
    metric_col: str,
    count_col: str,
    count_label: str,
    y_title: str,
    color_map: dict[str, str] | None = None,
    x_range: list[str] | None = None,
) -> tuple[go.Figure, int]:
    """Returns (figure, height_px). One subplot per narrative, shared y-scale and x-limits."""
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()

    def _empty(msg: str = "No data available") -> tuple[go.Figure, int]:
        f = go.Figure()
        f.add_annotation(
            text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(color=THEME_TEXT_MUTED, size=13),
        )
        return f, 520

    if df.empty or "dominant_narrative" not in df.columns:
        return _empty()

    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
    df[count_col] = pd.to_numeric(
        df[count_col] if count_col in df.columns else 0,
        errors="coerce",
    ).fillna(0).astype(int)
    df = df.dropna(subset=["week_start", "dominant_narrative"])

    if color_map:
        top_narratives = [n for n in color_map if n in df["dominant_narrative"].values]
    else:
        top_narratives = (
            df.groupby("dominant_narrative")[metric_col]
            .sum().nlargest(10).index.tolist()
        )
        color_map = {
            n: _NARRATIVE_LINE_COLORS[i % len(_NARRATIVE_LINE_COLORS)]
            for i, n in enumerate(top_narratives)
        }

    n = len(top_narratives)
    if n == 0:
        return _empty()

    global_max = float(df[df["dominant_narrative"].isin(top_narratives)][metric_col].max() or 1)

    titles = [(t[:44] + "…" if len(t) > 45 else t) for t in top_narratives]
    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.016,
        subplot_titles=titles,
    )

    for i, narrative in enumerate(top_narratives, start=1):
        color = color_map.get(narrative, _NARRATIVE_LINE_COLORS[0])
        sub = df[df["dominant_narrative"] == narrative].sort_values("week_start")

        fig.add_trace(
            go.Scatter(
                x=sub["week_start"],
                y=sub[metric_col],
                name=narrative,
                mode="lines",
                line=dict(width=1.5, color=color, shape="spline", smoothing=0.45),
                fill="tozeroy",
                fillcolor=hex_to_rgba(color, 0.18),
                showlegend=False,
                hovertemplate=f"{y_title}: %{{y:,.0f}}<extra></extra>",
            ),
            row=i, col=1,
        )
        fig.update_yaxes(
            range=[0, global_max * 1.08],
            showgrid=True,
            gridcolor=THEME_GRID,
            tickformat=",",
            automargin=False,
            row=i, col=1,
        )
        fig.update_xaxes(
            showgrid=True,
            gridcolor=THEME_GRID,
            showticklabels=(i == n),
            tickformat="%d %b",
            hoverformat="%d %b %Y",
            dtick=WEEKLY_DTICK_MS,
            row=i, col=1,
        )
        if x_range:
            fig.update_xaxes(range=x_range, row=i, col=1)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT, size=10),
        margin=dict(l=95, r=20, t=20, b=46),
        showlegend=False,
        hovermode="x",
        hoverlabel=theme_hoverlabel(size=12, namelength=-1),
    )
    fig.update_annotations(font=dict(color=THEME_TEXT_MUTED, size=10))

    height_px = n * 130 + 80
    return fig, height_px




# ---------------------------------------------------------------------------
# Narrative details section
# ---------------------------------------------------------------------------


def build_narratives_detail_section(data_frame: pd.DataFrame) -> html.Div:
    logger.warning("[DETAIL-DEBUG] FIGURE-REBUILD build_narratives_detail_section (on_page_load) -> content reset to placeholder")
    records = _detail_records_from_frame(data_frame)
    options = [{"label": r["narrative_label"], "value": r["narrative_label"]} for r in records]
    return html.Div(
        className="amazon-publishers-section amazon-publishers-details amazon-narrative-details",
        children=[
            html.Div(
                className="amazon-publishers-section-header",
                children=[html.H2(ref_label("Narrative Details", "P2S4"))],
            ),
            html.Div(
                className="amazon-publishers-detail-selector",
                children=[
                    html.Div("Narrative", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-narrative-detail-select",
                        options=options,
                        value=None,
                        searchable=True,
                        clearable=True,
                        persistence=True,
                        persistence_type="session",
                        placeholder="Select narrative…",
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
            dcc.Store(id="amazon-2026-narrative-detail-store", data=records),
            # Content lives in its own vm.Figure (see pages/narratives.py + detail_content_scope):
            # this keeps the shell and the populated content as separate single-source props so a
            # click can't revert the content to the placeholder. Nonce is bumped by a clientside
            # callback after _on_page_load rebuilds this shell, re-populating the current selection.
            dcc.Store(id="amazon-2026-narrative-detail-nonce"),
        ],
    )


_NARRATIVE_TEXT_COLUMNS = ["description", "takeaway_1", "takeaway_2", "takeaway_3"]


def _detail_records_from_frame(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for col in ["narrative_label", "trad_publications", "some_posts", "some_engagement",
                "campaign_items", "total_items", "paid_items"]:
        if col not in df.columns:
            df[col] = 0 if col != "narrative_label" else ""
    numeric_cols = ["trad_publications", "some_posts", "some_engagement",
                     "campaign_items", "total_items", "paid_items"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["narrative_label"] = df["narrative_label"].fillna("").astype(str)
    df = df[df["narrative_label"].str.strip() != ""]

    narratives_df = safe_load(NARRATIVES_KEY)
    for col in _NARRATIVE_TEXT_COLUMNS:
        if narratives_df.empty or col not in narratives_df.columns:
            df[col] = ""
        else:
            text_lookup = (
                narratives_df.set_index("narrative_label")[col]
                .fillna("")
                .astype(str)
            )
            df[col] = df["narrative_label"].map(text_lookup).fillna("")

    return [json_safe(row) for row in df.to_dict("records")]


def _narrative_sentiment_donut(
    positive_share: float, negative_share: float, title: str = "Sentiment share of reach"
) -> html.Div:
    neutral_share = max(0.0, 1.0 - positive_share - negative_share)
    labels, values, colors = sentiment_donut_slices(positive_share, neutral_share, negative_share)
    if not labels:
        return empty_donut_panel("No sentiment data")
    figure = donut_figure(labels, values, colors, hovertemplate="%{label}: %{percent:.1%}<extra></extra>")
    return donut_panel(title, figure)


def _narrative_angles_overview(selected_label: str) -> tuple[int, float, float]:
    angles_df = load_and_filter(ANGLES_KEY, "narrative_label", selected_label)

    total = len(angles_df)
    if total == 0 or "target_sentiment" not in angles_df.columns:
        return total, 0.0, 0.0

    sentiments = angles_df["target_sentiment"].astype(str).str.strip().str.title()
    positive_share = (sentiments == "Positive").sum() / total
    negative_share = (sentiments == "Negative").sum() / total
    return total, positive_share, negative_share


def _narrative_source_panels(overview_record: dict[str, Any] | None) -> list[html.Div]:
    if not overview_record:
        return []
    trad_pubs = int(num(overview_record, "trad_publications"))
    some_posts = int(num(overview_record, "some_posts"))
    if trad_pubs == 0 and some_posts == 0:
        return []
    panels = []
    if trad_pubs > 0:
        trad_reach = int(num(overview_record, "trad_reach"))
        trad_pos = float(num(overview_record, "trad_positive_share_of_reach"))
        trad_neg = float(num(overview_record, "trad_negative_share_of_reach"))
        panels.append(html.Div(
            className="amazon-publishers-kpi-panel",
            children=[
                html.Div(ref_label("Trad", "P2S4N1"), className="amazon-publishers-kpi-group-title"),
                html.Div(
                    className="amazon-publishers-kpi-panel-body",
                    children=[
                        html.Div(
                            className="amazon-publishers-kpi-panel-summary-kpis",
                            children=[
                                kpi_card(ref_label("Publications", "P2S4N1C1"), f"{trad_pubs:,}", compact=True),
                                kpi_card(ref_label("Reach", "P2S4N1C2"), f"{trad_reach:,}", compact=True),
                            ],
                        ),
                        _narrative_sentiment_donut(trad_pos, trad_neg),
                    ],
                ),
            ],
        ))
    if some_posts > 0:
        some_engagement = int(num(overview_record, "some_engagement"))
        some_pos = float(num(overview_record, "some_positive_share_of_reach"))
        some_neg = float(num(overview_record, "some_negative_share_of_reach"))
        panels.append(html.Div(
            className="amazon-publishers-kpi-panel",
            children=[
                html.Div(ref_label("SoMe", "P2S4N2"), className="amazon-publishers-kpi-group-title"),
                html.Div(
                    className="amazon-publishers-kpi-panel-body",
                    children=[
                        html.Div(
                            className="amazon-publishers-kpi-panel-summary-kpis",
                            children=[
                                kpi_card(ref_label("Posts", "P2S4N2C1"), f"{some_posts:,}", compact=True),
                                kpi_card(ref_label("Engagement", "P2S4N2C2"), f"{some_engagement:,}", compact=True),
                            ],
                        ),
                        _narrative_sentiment_donut(some_pos, some_neg),
                    ],
                ),
            ],
        ))
    return panels


def _narrative_detail_timeline_section(selected_label: str) -> html.Div:
    trad_df = load_and_filter(NARRATIVE_WEEKLY_REACH_KEY, "dominant_narrative", selected_label)
    some_df = load_and_filter(NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY, "dominant_narrative", selected_label)

    x_range = build_shared_x_range(trad_df, some_df)

    initial_fig = detail_weekly_figure(
        trad_df, "weekly_publications", "Trad Publications", "Trad Cumulative",
        source="Trad", x_range=x_range,
    )

    available_sources = timeline_available_sources({"has_trad": not trad_df.empty, "has_some": not some_df.empty})
    selected_sources = ["Trad"] if "Trad" in available_sources else available_sources

    return na_panel(
        html.Span(id="amazon-2026-narrative-detail-timeline-title", children=ref_label("Trad Publications", "P2S4G1")),
        [
            dcc.Store(
                id="amazon-2026-narrative-detail-timeline-store",
                data={
                    "trad": trad_df.to_dict("records") if not trad_df.empty else [],
                    "some": some_df.to_dict("records") if not some_df.empty else [],
                    "x_range": x_range,
                },
            ),
            dcc.Graph(
                id="amazon-2026-narrative-detail-timeline-graph",
                figure=initial_fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "360px"},
            ),
        ],
        controls=trad_some_controls(
            "amazon-2026-narrative-detail-timeline-source",
            available_sources,
            selected_sources,
            disable_unavailable=True,
            hide_when_single=False,
        ),
    )


def _narrative_sentiment_timeline_section(selected_label: str) -> html.Div:
    trad_df = load_and_filter(NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY, "narrative_label", selected_label)
    some_df = load_and_filter(NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY, "narrative_label", selected_label)

    trad_metric, some_metric = "publications", "posts"
    timeline_data = {
        "narrative_label": selected_label,
        "trad_metric": trad_metric,
        "some_metric": some_metric,
        "trad_timeline": timeline_records_from_frame(trad_df, id_field="narrative_label"),
        "some_timeline": timeline_records_from_frame(some_df, id_field="narrative_label"),
        "has_trad": not trad_df.empty,
        "has_some": not some_df.empty,
        "load_failed": data_load_failed(trad_df, some_df),
    }
    available_sources = timeline_available_sources(timeline_data)
    selected_sources = normalize_sources(available_sources, available_sources)

    return na_panel(
        ref_label(_timeline_chart_title(trad_metric, some_metric), "P2S4G2"),
        [
            dcc.Store(id="amazon-2026-narrative-sentiment-timeline-data", data=timeline_data),
            dcc.Graph(
                id="amazon-2026-narrative-sentiment-timeline-graph",
                figure=timeline_figure(timeline_data, selected_sources, id_field="narrative_label"),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=trad_some_controls(
            "amazon-2026-narrative-sentiment-timeline-source",
            available_sources,
            selected_sources,
            disable_unavailable=True,
            hide_when_single=False,
        ),
    )


def _narrative_media_split_timeline_section(selected_label: str) -> html.Div:
    trad_df = load_and_filter(NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY, "narrative_label", selected_label)
    some_df = load_and_filter(NARRATIVE_SOME_PLATFORM_TIMELINE_KEY, "narrative_label", selected_label)
    top_publications_df = load_and_filter(NARRATIVE_TOP_PUBLICATIONS_KEY, "narrative_label", selected_label)

    trad_flags = top_reach_flags(top_publications_df, "Trad")
    some_flags = top_reach_flags(top_publications_df, "SoMe")

    initial_fig, initial_height_px = media_split_timeline_figure(
        trad_df, some_df, stacked=False, trad_flags=trad_flags, some_flags=some_flags
    )
    initial_height_px = int(initial_height_px * NARRATIVE_MEDIA_SPLIT_HEIGHT_SCALE)

    return na_panel(
        ref_label("Publications Timeline by Media Type / Platform", "P2S4G3"),
        [
            dcc.Store(
                id="amazon-2026-narrative-media-split-store",
                data={
                    "trad": trad_df.to_dict("records") if not trad_df.empty else [],
                    "some": some_df.to_dict("records") if not some_df.empty else [],
                    "trad_flags": trad_flags,
                    "some_flags": some_flags,
                    "load_failed": data_load_failed(trad_df, some_df),
                },
            ),
            dcc.Graph(
                id="amazon-2026-narrative-media-split-graph",
                figure=initial_fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": f"{initial_height_px}px"},
                className="amazon-publishers-timeline-graph amazon-narrative-media-split-graph",
            ),
        ],
        controls=dcc.Checklist(
            id="amazon-2026-narrative-media-split-stacked",
            options=[{"label": "Stacked", "value": "stacked"}],
            value=[],
            inline=True,
            className="amazon-publishers-radio",
        ),
    )


@callback(
    Output("amazon-2026-narrative-media-split-graph", "figure"),
    Output("amazon-2026-narrative-media-split-graph", "style"),
    Input("amazon-2026-narrative-media-split-stacked", "value"),
    State("amazon-2026-narrative-media-split-store", "data"),
    prevent_initial_call=True,
)
def _update_narrative_media_split_figure(stacked_value: list[str] | None, store_data: dict | None) -> tuple[go.Figure, dict]:
    data = store_data or {}
    trad_df = pd.DataFrame(data.get("trad") or [])
    some_df = pd.DataFrame(data.get("some") or [])
    stacked = "stacked" in (stacked_value or [])
    fig, height_px = media_split_timeline_figure(
        trad_df,
        some_df,
        stacked=stacked,
        trad_flags=data.get("trad_flags") or [],
        some_flags=data.get("some_flags") or [],
        load_failed=bool(data.get("load_failed")),
    )
    height_px = int(height_px * NARRATIVE_MEDIA_SPLIT_HEIGHT_SCALE)
    return fig, {"height": f"{height_px}px"}


# ---------------------------------------------------------------------------
# Narrative angles table
# ---------------------------------------------------------------------------

ANGLE_SENTIMENT_OPTIONS = [
    {"label": "Positive", "value": "Positive"},
    {"label": "Neutral", "value": "Neutral"},
    {"label": "Negative", "value": "Negative"},
]

ANGLE_BAR_COLORS = {
    "trad_publications": "var(--na-bar-trad-publications)",
    "some_posts": "var(--na-bar-some-posts)",
    "reach": "var(--na-bar-trad-reach)",
    "popularity": "var(--na-bar-some-engagement)",
}


def _angles_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": ["", "Angle"], "id": "angle_label"},
        {"name": ["", "Sentiment"], "id": "target_sentiment"},
        {
            "name": ["", "Trad"],
            "id": "trad_publications",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": ["", "SoMe"],
            "id": "some_posts",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": ["", "Reach"],
            "id": "reach",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": ["", "Popularity (%)"],
            "id": "popularity",
            "type": "numeric",
            "format": Format(precision=1, scheme=Scheme.percentage),
        },
    ]


def _angles_table_rows(
    records: list[dict[str, Any]],
    sentiment_filter: list[str] | None,
) -> list[dict[str, Any]]:
    selected = sentiment_filter or [opt["value"] for opt in ANGLE_SENTIMENT_OPTIONS]
    rows = []
    for idx, record in enumerate(records):
        sentiment = str(record.get("target_sentiment") or "").strip().title()
        if sentiment not in selected:
            continue
        angle_id = str(record.get("angle_id") or "").strip()
        angle_label = record.get("angle_label", "")
        rows.append(
            {
                "id": angle_id or angle_label,
                "row_id": idx,
                "angle_id": angle_id,
                "angle_label": angle_label,
                "target_sentiment": sentiment,
                "trad_publications": num(record, "trad_publications"),
                "some_posts": num(record, "some_posts"),
                "reach": num(record, "reach"),
                "popularity": num(record, "popularity") / 100,
            }
        )
    return rows


def _angles_data_bar_styles(table_data: list[dict[str, Any]], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    visible_ids = {column["id"] for column in columns}
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {
            "if": {"column_id": "angle_label"},
            "color": "var(--na-link)",
            "cursor": "pointer",
            "fontWeight": "700",
            "fontSize": "13px",
            "textAlign": "left",
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
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
    for column_id in [col for col in ANGLE_BAR_COLORS if col in visible_ids]:
        styles += _data_bar_column_styles(table_data, column_id, ANGLE_BAR_COLORS[column_id])
    return styles


def _narrative_angles_section(selected_label: str) -> html.Div:
    angles_df = load_and_filter(ANGLES_KEY, "narrative_label", selected_label)

    records = [json_safe(row) for row in angles_df.to_dict("records")]
    selected_sentiments = [opt["value"] for opt in ANGLE_SENTIMENT_OPTIONS]
    table_rows = _angles_table_rows(records, selected_sentiments)
    table_cols = _angles_table_columns()
    angle_options = [{"label": "All", "value": "All"}] + [
        {"label": r.get("angle_label", ""), "value": str(r.get("angle_id") or r.get("angle_label") or "")}
        for r in records
        if r.get("angle_label")
    ]

    return html.Div(
        children=[
            _narrative_angles_table_panel(records, table_rows, table_cols, selected_sentiments),
            html.Div(
                className="amazon-publishers-control amazon-publishers-source-control",
                style={"marginTop": "8px", "maxWidth": "320px"},
                children=[
                    html.Div("Angle", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-narrative-angles-filter",
                        options=angle_options,
                        value="All",
                        clearable=False,
                        searchable=True,
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
        ],
    )


def _narrative_angles_table_panel(
    records: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
    table_cols: list[dict[str, Any]],
    selected_sentiments: list[str],
) -> html.Div:
    return na_panel(
        ref_label("Angles", "P2S4T1"),
        [
            dcc.Store(id="amazon-2026-narrative-angles-store", data=records),
            dash_table.DataTable(
                id="amazon-2026-narrative-angles-table",
                data=table_rows,
                columns=table_cols,
                merge_duplicate_headers=True,
                page_size=15,
                sort_action="native",
                filter_action="none",
                cell_selectable=True,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=TOP_TABLE_STYLE_CELL,
                style_header=TOP_TABLE_STYLE_HEADER,
                style_data_conditional=_angles_data_bar_styles(table_rows, table_cols),
                css=[
                    {"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"},
                    {
                        "selector": "td[data-dash-column='angle_label'] .dash-cell-value",
                        "rule": "pointer-events: none; cursor: pointer;",
                    },
                ],
            ),
            html.Div("No angles available for this narrative.", className="amazon-publishers-empty")
            if not records
            else None,
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.Checklist(
                    id="amazon-2026-narrative-angles-sentiment",
                    options=ANGLE_SENTIMENT_OPTIONS,
                    value=selected_sentiments,
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Narrative Top Publishers / Top Journalists tables
# ---------------------------------------------------------------------------


def _narrative_top_publishers_section(selected_label: str) -> html.Div:
    df = load_and_filter(NARRATIVE_TOP_PUBLISHERS_KEY, "narrative_label", selected_label)

    records = [json_safe(row) for row in df.to_dict("records")]
    table_rows = top_publishers_table_rows(records, "Trad")
    table_cols = top_publishers_table_columns()

    return na_panel(
        ref_label("Top Narrative Publishers", "P2S4T2"),
        [
            dcc.Store(id="amazon-2026-narrative-top-publishers-store", data=records),
            dash_table.DataTable(
                id="amazon-2026-narrative-top-publishers-table",
                data=table_rows,
                columns=table_cols,
                page_size=TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=TOP_TABLE_STYLE_CELL,
                style_header=TOP_TABLE_STYLE_HEADER,
                style_data_conditional=top_publishers_data_bar_styles(table_rows),
                css=[{"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"}],
            ),
            html.Div("No publisher data available for this narrative.", className="amazon-publishers-empty")
            if not records
            else None,
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.RadioItems(
                    id="amazon-2026-narrative-top-publishers-source",
                    options=TRAD_SOME_OPTIONS,
                    value="Trad",
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


def _narrative_top_journalists_section(selected_label: str) -> html.Div:
    df = load_and_filter(NARRATIVE_TOP_JOURNALISTS_KEY, "narrative_label", selected_label)

    records = [json_safe(row) for row in df.to_dict("records")]
    table_rows = top_journalists_table_rows(records)
    table_cols = top_journalists_table_columns()

    return na_panel(
        ref_label("Top Journalists", "P2S4T3"),
        [
            dash_table.DataTable(
                id="amazon-2026-narrative-top-journalists-table",
                data=table_rows,
                columns=table_cols,
                page_size=TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=TOP_TABLE_STYLE_CELL,
                style_header=TOP_TABLE_STYLE_HEADER,
                style_data_conditional=top_journalists_data_bar_styles(table_rows),
                css=[{"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"}],
            ),
            html.Div("No journalist data available for this narrative.", className="amazon-publishers-empty")
            if not records
            else None,
        ],
    )


def _narrative_top_tables_section(selected_label: str) -> html.Div:
    return html.Div(
        className="amazon-narrative-tables-row",
        children=[
            _narrative_top_publishers_section(selected_label),
            _narrative_top_journalists_section(selected_label),
        ],
    )


def _filter_top_items_by_angle(records: list[dict[str, Any]], angle_filter: str | None) -> list[dict[str, Any]]:
    if not angle_filter or angle_filter == "All":
        return records
    # If no records carry angle metadata at all, angle filtering is unavailable.
    if not any(r.get("Angle_ID") or r.get("Angle") for r in records):
        return records
    filter_value = str(angle_filter).strip()
    filtered = [
        r for r in records
        if str(r.get("Angle_ID") or "").strip() == filter_value
        or str(r.get("Angle") or "").strip() == filter_value
    ]
    return filtered


def _narrative_top_items_panel(selected_label: str) -> html.Div:
    df = load_and_filter(NARRATIVE_TOP_PUBLICATIONS_KEY, "narrative_label", selected_label)
    records = [json_safe(row) for row in df.to_dict("records")]
    trad_table_data, some_table_data = build_top_items_table_data(records)
    return build_top_items_panel(
        "amazon-2026-narrative",
        ref_label("Top Publications / Posts", "P2S4T4"),
        trad_table_data,
        some_table_data,
        show_publication_col=True,
        show_author_col=True,
        box="flat",
    )


def _narrative_detail_content(
    records: list[dict[str, Any]],
    selected_label: str | None,
    overview_records: list[dict[str, Any]] | None = None,
) -> html.Div:
    if not selected_label:
        return html.Div(className="amazon-publishers-empty", children="Select a narrative to see details.")
    record = next((r for r in records if r.get("narrative_label") == selected_label), None)
    if record is None:
        return html.Div(className="amazon-publishers-empty", children="No data for selected narrative.")

    trad_pubs = int(num(record, "trad_publications"))
    some_posts = int(num(record, "some_posts"))
    total_pubs = trad_pubs + some_posts

    angles_count, angles_pos_share, angles_neg_share = _narrative_angles_overview(selected_label)

    cards = [
        kpi_card(ref_label("Total Publications", "P2S4C1"), f"{total_pubs:,}"),
        kpi_card(ref_label("Angles", "P2S4C2"), f"{angles_count:,}"),
    ]

    overview_panel = html.Div(
        className="amazon-publishers-kpi-panel",
        children=[
            html.Div(ref_label("Overview", "P2S4N0"), className="amazon-publishers-kpi-group-title"),
            html.Div(
                className="amazon-publishers-kpi-panel-body",
                children=[
                    html.Div(className="amazon-publishers-kpi-panel-summary-kpis", children=cards),
                    _narrative_sentiment_donut(angles_pos_share, angles_neg_share, title="Angles by sentiment"),
                ],
            ),
        ],
    )

    overview_record = next(
        (r for r in (overview_records or []) if r.get("narrative_label") == selected_label), None
    )
    source_panels = _narrative_source_panels(overview_record)

    description = str(record.get("description") or "").strip()
    takeaways = [
        str(record.get(f"takeaway_{i}") or "").strip()
        for i in (1, 2, 3)
    ]
    takeaways = [t for t in takeaways if t]

    return html.Div(
        className="amazon-publishers-detail-content",
        children=[
            html.Div(
                className="amazon-narrative-detail-grid",
                children=[
                    html.Div(
                        className="amazon-narrative-detail-summary",
                        children=[overview_panel, *source_panels],
                    ),
                    html.Div(
                        className="amazon-narrative-profile-column",
                        children=[
                            html.Div(
                                className="amazon-narrative-profile",
                                children=[
                                    html.H3(selected_label, className="amazon-narrative-profile-title"),
                                    na_panel(
                                        ref_label("Narrative description", "P2S4D1"),
                                        [
                                            html.P(
                                                description or "No description available.",
                                                className="amazon-narrative-description-text",
                                            )
                                        ],
                                        box="flat",
                                    ),
                                    na_panel(
                                        ref_label("Key Insights", "P2S4D3"),
                                        [
                                            html.Div(
                                                [html.Div(t, className="amazon-narrative-insight-card") for t in takeaways]
                                                or [html.Div("No insights available.", className="amazon-narrative-insight-card")],
                                                className="amazon-narrative-insights-grid",
                                            )
                                        ],
                                        box="flat",
                                    ),
                                ],
                            ),
                            _narrative_top_tables_section(selected_label),
                        ],
                    ),
                ],
            ),
            _narrative_detail_timeline_section(selected_label),
            _narrative_sentiment_timeline_section(selected_label),
            _narrative_media_split_timeline_section(selected_label),
            _narrative_angles_section(selected_label),
            _narrative_top_items_panel(selected_label),
        ],
    )


# ---------------------------------------------------------------------------
# KPI panel (moved from pages/narratives.py — belongs with the other builders)
# ---------------------------------------------------------------------------


def _build_narratives_kpi_section(kpi_df: pd.DataFrame) -> html.Div:
    row = kpi_df.iloc[0] if not kpi_df.empty else {}

    total_narratives = int(row.get("total_narratives", 0))
    total_angles = int(row.get("total_angles", 0))

    total_pubs = int(row.get("total_pubs", 0))
    pubs_in_narrative = int(row.get("pubs_in_narrative", 0))
    share_pubs = pubs_in_narrative / total_pubs if total_pubs else 0.0

    total_posts = int(row.get("total_posts", 0))
    posts_in_narrative = int(row.get("posts_in_narrative", 0))
    share_posts = posts_in_narrative / total_posts if total_posts else 0.0

    total_campaign = int(row.get("total_items_campaign", 0))
    campaign_items = int(row.get("campaign_items", 0))
    share_campaign = campaign_items / total_campaign if total_campaign else 0.0

    paid_items = int(row.get("paid_items", 0))
    share_paid = paid_items / total_campaign if total_campaign else 0.0

    return html.Div(
        className="amazon-publishers-kpis-grid",
        children=[
            html.Div(
                className="amazon-publishers-kpis",
                children=[
                    kpi_card(ref_label("Narratives", "P2S1C1"), f"{total_narratives:,}"),
                    kpi_card(ref_label("Trad Publications in Narratives", "P2S1C2"), f"{share_pubs:.1%}"),
                    kpi_card(ref_label("Part of Campaigns", "P2S1C3"), f"{share_campaign:.1%}"),
                ],
            ),
            html.Div(
                className="amazon-publishers-kpis",
                children=[
                    kpi_card(ref_label("Angles", "P2S1C4"), f"{total_angles:,}"),
                    kpi_card(ref_label("SoMe Posts in Narratives", "P2S1C5"), f"{share_posts:.1%}"),
                    kpi_card(ref_label("Paid Content", "P2S1C6"), f"{share_paid:.1%}"),
                ],
            ),
        ],
    )


@capture("figure")
def narratives_kpi_panel(data_frame: pd.DataFrame) -> html.Div:
    return _build_narratives_kpi_section(data_frame)
