"""Narratives page components — chart builders and data transforms."""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from plotly.subplots import make_subplots
from dash.dash_table.Format import Format, Scheme

from vizro.managers import data_manager
from vizro.models.types import capture

from dashboards.amazon_2026.charts_shared import (
    ACCENT_SOME,
    ACCENT_TRAD,
    NARRATIVE_SOME_COLUMNS,
    NARRATIVE_TRAD_COLUMNS,
    SENTIMENT_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_ROW_EVEN,
    THEME_ROW_ODD,
    THEME_SURFACE,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    TRAD_SOME_OPTIONS,
    _hex_to_rgba,
    _json_safe,
    _kpi_card,
    _narrative_data_bar_styles,
    _narrative_header_divider_styles,
    _narratives_table_columns,
    _normalize_sources,
    _num,
    na_panel,
    build_top_items_panel,
    _timeline_available_sources,
    _timeline_chart_title,
    _timeline_figure,
    _timeline_records_from_frame,
)
from dashboards.amazon_2026.data_common import (
    ANGLES_KEY,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY,
    NARRATIVE_TOP_JOURNALISTS_KEY,
    NARRATIVE_TOP_PUBLISHERS_KEY,
    NARRATIVE_TOP_PUBLICATIONS_KEY,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_WEEKLY_REACH_KEY,
    NARRATIVES_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label

NARRATIVES_SOURCE_OPTIONS = [
    {"label": "All", "value": "All"},
    {"label": "Trad", "value": "Trad"},
    {"label": "SoMe", "value": "SoMe"},
]


def _norm_source(sf: str | list[str] | None) -> list[str]:
    """Convert any source filter to the ["Trad", "SoMe"] form that the helpers expect."""
    return _normalize_sources(sf, ["Trad", "SoMe"])

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
                    "backgroundColor": "var(--amazon-publishers-header-bg)",
                    "border": f"1px solid {THEME_BORDER}",
                    "color": THEME_TEXT,
                    "fontWeight": "700",
                    "height": "34px",
                    "textAlign": "center",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
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
    return [_json_safe(row) for row in df.to_dict("records")]



def _overview_table_rows(
    records: list[dict[str, Any]],
    source_filter: str | list[str] | None,
) -> list[dict[str, Any]]:
    selected = _norm_source(source_filter)
    show_trad = "Trad" in selected
    show_some = "SoMe" in selected
    rows = []
    for idx, record in enumerate(records):
        trad_pub = _num(record, "trad_publications")
        trad_reach = _num(record, "trad_reach")
        some_posts = _num(record, "some_posts")
        some_reach = _num(record, "some_reach")
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
                **{col: _num(record, col) if show_trad else 0 for col in NARRATIVE_TRAD_COLUMNS},
                **{col: _num(record, col) if show_some else 0 for col in NARRATIVE_SOME_COLUMNS},
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

_NARRATIVE_LINE_COLORS = [
    "#2f7dd1", "#22a6a1", "#d98933", "#8a6fd1",
    "#35a66b", "#c84e5a", "#b8a33e", "#5aa4b1",
    "#e07040", "#7b5ea7",
]

def build_narratives_combined_timeline_section(data_frame: pd.DataFrame) -> html.Div:
    trad_df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    try:
        some_df = data_manager[NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY].load()
    except Exception:
        some_df = pd.DataFrame()

    shared_color_map = _build_shared_color_map(trad_df, some_df)
    x_range = _build_shared_x_range(trad_df, some_df)

    initial_fig = _narrative_weekly_figure(
        trad_df, "weekly_reach", "weekly_publications", "pubs", "Weekly Reach",
        color_map=shared_color_map,
        x_range=x_range,
    )

    return html.Div(
        className="na-panel",
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "flexWrap": "wrap", "gap": "8px"},
                children=[
                    html.H3(
                        id="amazon-2026-narratives-timeline-title",
                        children=ref_label("Weekly Reach by Narrative", "P2S2G1"),
                        className="na-element-title",
                        style={"margin": "0"},
                    ),
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
            dcc.Store(
                id="amazon-2026-narratives-timeline-store",
                data={
                    "trad": trad_df.to_dict("records") if not trad_df.empty else [],
                    "some": some_df.to_dict("records") if not some_df.empty else [],
                    "color_map": shared_color_map,
                    "x_range": x_range,
                },
            ),
            dcc.Graph(
                id="amazon-2026-narratives-timeline-graph",
                figure=initial_fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "520px"},
            ),
        ],
    )


def _build_shared_x_range(trad_df: pd.DataFrame, some_df: pd.DataFrame) -> list[str] | None:
    weeks: list[pd.Series] = []
    for df, col in [(trad_df, "week_start"), (some_df, "week_start")]:
        if not df.empty and col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce").dropna()
            if not parsed.empty:
                weeks.append(parsed)
    if not weeks:
        return None
    all_weeks = pd.concat(weeks)
    padding = pd.Timedelta(days=3)
    return [
        (all_weeks.min() - padding).isoformat(),
        (all_weeks.max() + padding).isoformat(),
    ]


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
) -> go.Figure:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    fig = go.Figure()
    if df.empty or "dominant_narrative" not in df.columns:
        fig.add_annotation(
            text="No data available",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )
        _apply_narrative_weekly_layout(fig, y_title)
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
                fillcolor=_hex_to_rgba(color, 0.12),
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

    _apply_narrative_weekly_layout(fig, y_title, x_range)
    return fig


# Trad/SoMe line styling shared between the single-source and combined
# Trad+SoMe weekly detail charts — kept distinct from SENTIMENT_COLORS and
# matching the dash/marker convention used by the P2S4G2 sentiment timeline
# (Trad: solid line + circle marker, SoMe: dotted line + diamond marker).
# Cumulative lines reuse the source color but use a dashed line so they
# remain distinguishable from both the Trad and SoMe weekly lines.
_DETAIL_SOURCE_STYLE = {
    "Trad": {"color": ACCENT_TRAD, "dash": "solid", "marker": "circle"},
    "SoMe": {"color": ACCENT_SOME, "dash": "dot", "marker": "diamond"},
}
_DETAIL_CUMULATIVE_DASH = "dash"


def _narrative_detail_weekly_figure(
    data_frame: pd.DataFrame,
    metric_col: str,
    y_title: str,
    cum_title: str,
    source: str = "Trad",
    x_range: list[str] | None = None,
    dtick: int | None = None,
) -> go.Figure:
    """Single-narrative weekly line with a cumulative line on a secondary y-axis."""
    style = _DETAIL_SOURCE_STYLE.get(source, _DETAIL_SOURCE_STYLE["Trad"])
    color = style["color"]

    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    fig = go.Figure()
    if df.empty or "week_start" not in df.columns:
        fig.add_annotation(
            text="No data available",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )
        _apply_narrative_weekly_layout(fig, y_title, x_range, dtick=dtick)
        return fig

    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
    df = df.dropna(subset=["week_start"]).sort_values("week_start")

    if df.empty:
        fig.add_annotation(
            text="No data available",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )
        _apply_narrative_weekly_layout(fig, y_title, x_range, dtick=dtick)
        return fig

    cumulative = df[metric_col].cumsum()

    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=df[metric_col],
            name=y_title,
            mode="lines+markers",
            line=dict(width=2.5, color=color, shape="spline", smoothing=0.45, dash=style["dash"]),
            marker=dict(size=5, color=color, symbol=style["marker"]),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(color, 0.12),
            hovertemplate=f"{y_title}: %{{y:,.0f}}<extra></extra>",
            yaxis="y",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["week_start"],
            y=cumulative,
            name=cum_title,
            mode="lines",
            line=dict(width=2, color=color, dash=_DETAIL_CUMULATIVE_DASH),
            hovertemplate=f"{cum_title}: %{{y:,.0f}}<extra></extra>",
            yaxis="y2",
        )
    )

    _apply_narrative_weekly_layout(fig, y_title, x_range, dtick=dtick)
    fig.update_layout(
        hovermode="closest",
        yaxis2=dict(
            title=cum_title,
            tickformat=",",
            rangemode="tozero",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
    return fig


def _narrative_detail_combined_weekly_figure(
    trad_df: pd.DataFrame,
    some_df: pd.DataFrame,
    trad_metric_col: str,
    trad_label: str,
    trad_cum_label: str,
    some_metric_col: str,
    some_label: str,
    some_cum_label: str,
    y_title: str,
    cum_title: str,
    x_range: list[str] | None = None,
    dtick: int | None = None,
) -> go.Figure:
    """Trad + SoMe weekly metric, each with its own cumulative line."""
    fig = go.Figure()

    def _prep(data_frame: pd.DataFrame, metric_col: str) -> pd.DataFrame:
        df = data_frame.copy() if data_frame is not None else pd.DataFrame()
        if df.empty or "week_start" not in df.columns:
            return pd.DataFrame()
        df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
        df[metric_col] = pd.to_numeric(df.get(metric_col, 0), errors="coerce").fillna(0)
        return df.dropna(subset=["week_start"]).sort_values("week_start")

    series = [
        ("Trad", _prep(trad_df, trad_metric_col), trad_metric_col, trad_label, trad_cum_label),
        ("SoMe", _prep(some_df, some_metric_col), some_metric_col, some_label, some_cum_label),
    ]

    for source, df, metric_col, weekly_label, cum_label in series:
        if df.empty:
            continue
        style = _DETAIL_SOURCE_STYLE[source]
        color = style["color"]
        cumulative = df[metric_col].cumsum()
        fig.add_trace(
            go.Scatter(
                x=df["week_start"],
                y=df[metric_col],
                name=weekly_label,
                mode="lines+markers",
                line=dict(width=2.5, color=color, shape="spline", smoothing=0.45, dash=style["dash"]),
                marker=dict(size=5, color=color, symbol=style["marker"]),
                fill="tozeroy",
                fillcolor=_hex_to_rgba(color, 0.1),
                hovertemplate=f"{weekly_label}: %{{y:,.0f}}<extra></extra>",
                yaxis="y",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["week_start"],
                y=cumulative,
                name=cum_label,
                mode="lines",
                line=dict(width=2, color=color, dash=_DETAIL_CUMULATIVE_DASH),
                hovertemplate=f"{cum_label}: %{{y:,.0f}}<extra></extra>",
                yaxis="y2",
            )
        )

    if not fig.data:
        fig.add_annotation(
            text="No data available",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT_MUTED, size=13),
        )

    _apply_narrative_weekly_layout(fig, y_title, x_range, dtick=dtick)
    fig.update_layout(
        hovermode="closest",
        yaxis2=dict(
            title=cum_title,
            tickformat=",",
            rangemode="tozero",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
    )
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
                fillcolor=_hex_to_rgba(color, 0.18),
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
        hoverlabel=dict(
            bgcolor=THEME_SURFACE,
            bordercolor=THEME_BORDER,
            font=dict(color=THEME_TEXT, size=12),
            namelength=-1,
        ),
    )
    fig.update_annotations(font=dict(color=THEME_TEXT_MUTED, size=10))

    height_px = n * 130 + 80
    return fig, height_px


def _apply_narrative_weekly_layout(
    fig: go.Figure, y_title: str, x_range: list[str] | None = None, dtick: int | None = None
) -> None:
    xaxis_cfg: dict = dict(
        title=None,
        tickformat="%d %b",
        hoverformat="%d %b %Y",
        showgrid=True,
        gridcolor=THEME_GRID,
    )
    if x_range:
        xaxis_cfg["range"] = x_range
    if dtick:
        xaxis_cfg["dtick"] = dtick

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=95, r=20, t=10, b=46),
        hovermode="x unified",
        legend=dict(
            orientation="v",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor=THEME_SURFACE,
            bordercolor=THEME_BORDER,
            borderwidth=1,
            font=dict(size=10),
            title=None,
        ),
        xaxis=xaxis_cfg,
        yaxis=dict(
            title=y_title,
            tickformat=",",
            rangemode="tozero",
            automargin=False,
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        hoverlabel=dict(
            bgcolor=THEME_SURFACE,
            bordercolor=THEME_BORDER,
            font=dict(color=THEME_TEXT, size=13),
            namelength=-1,
            align="left",
        ),
    )


# ---------------------------------------------------------------------------
# Narrative details section
# ---------------------------------------------------------------------------


def build_narratives_detail_section(data_frame: pd.DataFrame) -> html.Div:
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
            html.Div(
                id="amazon-2026-narrative-details-content",
                children=_narrative_detail_content(records, None),
            ),
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

    try:
        narratives_df = data_manager[NARRATIVES_KEY].load()
    except Exception:
        narratives_df = pd.DataFrame()
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

    return [_json_safe(row) for row in df.to_dict("records")]


def _narrative_sentiment_donut(
    positive_share: float, negative_share: float, title: str = "Sentiment share of reach"
) -> html.Div:
    neutral_share = max(0.0, 1.0 - positive_share - negative_share)
    slices = [
        ("Positive", positive_share),
        ("Neutral", neutral_share),
        ("Negative", negative_share),
    ]
    slices = [(label, share) for label, share in slices if share > 0]
    if not slices:
        return html.Div(
            className="amazon-publishers-mini-donut amazon-publishers-mini-donut-empty",
            children=[html.Div("No sentiment data", className="amazon-publishers-mini-empty")],
        )
    labels = [s[0] for s in slices]
    values = [s[1] for s in slices]
    colors = [SENTIMENT_COLORS[s[0]] for s in slices]
    slice_text = [f"{s[0]}<br>{s[1]:.1%}" if s[1] >= 0.03 else "" for s in slices]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.62,
            domain={"x": [0.2, 0.8], "y": [0.12, 0.88]},
            sort=False,
            marker={"colors": colors, "line": {"color": THEME_SURFACE, "width": 0.5}},
            text=slice_text,
            textinfo="text",
            textposition="outside",
            textfont={"color": THEME_TEXT, "size": 11},
            automargin=True,
            hovertemplate="%{label}: %{percent:.1%}<extra></extra>",
            hoverlabel={"bgcolor": THEME_SURFACE, "bordercolor": THEME_BORDER, "font": {"color": THEME_TEXT}},
            showlegend=False,
        )
    )
    fig.update_layout(
        autosize=True, width=None, height=None,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uniformtext={"minsize": 10, "mode": "hide"},
    )
    return html.Div(
        className="amazon-publishers-mini-donut",
        children=[
            html.Div(
                className="amazon-publishers-mini-donut-header",
                children=[html.Div(title, className="amazon-publishers-mini-title")],
            ),
            dcc.Graph(
                figure=fig,
                responsive=True,
                config={"displayModeBar": False},
                className="amazon-publishers-mini-donut-graph",
                style={"width": "100%", "height": "100%", "minWidth": 0},
            ),
        ],
    )


def _narrative_angles_overview(selected_label: str) -> tuple[int, float, float]:
    try:
        angles_df = data_manager[ANGLES_KEY].load()
    except Exception:
        angles_df = pd.DataFrame()

    if not angles_df.empty and "narrative_label" in angles_df.columns:
        angles_df = angles_df[angles_df["narrative_label"] == selected_label]
    else:
        angles_df = pd.DataFrame()

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
    trad_pubs = int(_num(overview_record, "trad_publications"))
    some_posts = int(_num(overview_record, "some_posts"))
    if trad_pubs == 0 and some_posts == 0:
        return []
    panels = []
    if trad_pubs > 0:
        trad_reach = int(_num(overview_record, "trad_reach"))
        trad_pos = float(_num(overview_record, "trad_positive_share_of_reach"))
        trad_neg = float(_num(overview_record, "trad_negative_share_of_reach"))
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
                                _kpi_card(ref_label("Publications", "P2S4N1C1"), f"{trad_pubs:,}", compact=True),
                                _kpi_card(ref_label("Reach", "P2S4N1C2"), f"{trad_reach:,}", compact=True),
                            ],
                        ),
                        _narrative_sentiment_donut(trad_pos, trad_neg),
                    ],
                ),
            ],
        ))
    if some_posts > 0:
        some_engagement = int(_num(overview_record, "some_engagement"))
        some_pos = float(_num(overview_record, "some_positive_share_of_reach"))
        some_neg = float(_num(overview_record, "some_negative_share_of_reach"))
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
                                _kpi_card(ref_label("Posts", "P2S4N2C1"), f"{some_posts:,}", compact=True),
                                _kpi_card(ref_label("Engagement", "P2S4N2C2"), f"{some_engagement:,}", compact=True),
                            ],
                        ),
                        _narrative_sentiment_donut(some_pos, some_neg),
                    ],
                ),
            ],
        ))
    return panels


def _narrative_detail_timeline_section(selected_label: str) -> html.Div:
    try:
        trad_df = data_manager[NARRATIVE_WEEKLY_REACH_KEY].load()
    except Exception:
        trad_df = pd.DataFrame()
    try:
        some_df = data_manager[NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY].load()
    except Exception:
        some_df = pd.DataFrame()

    if not trad_df.empty and "dominant_narrative" in trad_df.columns:
        trad_df = trad_df[trad_df["dominant_narrative"] == selected_label]
    else:
        trad_df = pd.DataFrame()
    if not some_df.empty and "dominant_narrative" in some_df.columns:
        some_df = some_df[some_df["dominant_narrative"] == selected_label]
    else:
        some_df = pd.DataFrame()

    x_range = _build_shared_x_range(trad_df, some_df)

    initial_fig = _narrative_detail_weekly_figure(
        trad_df, "weekly_publications", "Trad Publications", "Trad Cumulative",
        source="Trad", x_range=x_range,
    )

    return html.Div(
        className="na-panel",
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between", "flexWrap": "wrap", "gap": "8px"},
                children=[
                    html.H3(
                        id="amazon-2026-narrative-detail-timeline-title",
                        children=ref_label("Trad Publications", "P2S4G1"),
                        className="na-element-title",
                        style={"margin": "0"},
                    ),
                    dcc.Checklist(
                        id="amazon-2026-narrative-detail-timeline-source",
                        options=TRAD_SOME_OPTIONS,
                        value=["Trad"],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                ],
            ),
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
    )


def _narrative_sentiment_timeline_section(selected_label: str) -> html.Div:
    try:
        trad_df = data_manager[NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY].load()
    except Exception:
        trad_df = pd.DataFrame()
    try:
        some_df = data_manager[NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY].load()
    except Exception:
        some_df = pd.DataFrame()

    if not trad_df.empty and "narrative_label" in trad_df.columns:
        trad_df = trad_df[trad_df["narrative_label"] == selected_label]
    else:
        trad_df = pd.DataFrame()
    if not some_df.empty and "narrative_label" in some_df.columns:
        some_df = some_df[some_df["narrative_label"] == selected_label]
    else:
        some_df = pd.DataFrame()

    trad_metric, some_metric = "publications", "posts"
    timeline_data = {
        "narrative_label": selected_label,
        "trad_metric": trad_metric,
        "some_metric": some_metric,
        "trad_timeline": _timeline_records_from_frame(trad_df, id_field="narrative_label"),
        "some_timeline": _timeline_records_from_frame(some_df, id_field="narrative_label"),
        "has_trad": not trad_df.empty,
        "has_some": not some_df.empty,
    }
    available_sources = _timeline_available_sources(timeline_data)
    selected_sources = _normalize_sources(available_sources, available_sources)
    options = [
        {
            "label": option["label"],
            "value": option["value"],
            "disabled": option["value"] not in available_sources,
        }
        for option in TRAD_SOME_OPTIONS
    ]

    return na_panel(
        ref_label(_timeline_chart_title(trad_metric, some_metric), "P2S4G2"),
        [
            dcc.Store(id="amazon-2026-narrative-sentiment-timeline-data", data=timeline_data),
            dcc.Graph(
                id="amazon-2026-narrative-sentiment-timeline-graph",
                figure=_timeline_figure(timeline_data, selected_sources, id_field="narrative_label"),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.Checklist(
                    id="amazon-2026-narrative-sentiment-timeline-source",
                    options=options,
                    value=selected_sources,
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Narrative angles table
# ---------------------------------------------------------------------------

ANGLE_SENTIMENT_OPTIONS = [
    {"label": "Positive", "value": "Positive"},
    {"label": "Neutral", "value": "Neutral"},
    {"label": "Negative", "value": "Negative"},
]

ANGLE_BAR_COLORS = {
    "publications": "var(--amazon-publishers-bar-trad-publications)",
    "reach": "var(--amazon-publishers-bar-trad-reach)",
    "popularity": "var(--amazon-publishers-bar-some-engagement)",
}


def _angles_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": ["", "Angle"], "id": "angle_label"},
        {"name": ["", "Sentiment"], "id": "target_sentiment"},
        {
            "name": ["", "Publications"],
            "id": "publications",
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
        rows.append(
            {
                "id": record.get("angle_label", ""),
                "row_id": idx,
                "angle_label": record.get("angle_label", ""),
                "target_sentiment": sentiment,
                "publications": _num(record, "publications"),
                "reach": _num(record, "reach"),
                "popularity": _num(record, "popularity") / 100,
            }
        )
    return rows


def _angles_data_bar_styles(table_data: list[dict[str, Any]], columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    visible_ids = {column["id"] for column in columns}
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {
            "if": {"column_id": "angle_label"},
            "color": "var(--amazon-publishers-link)",
            "cursor": "pointer",
            "fontWeight": "700",
            "fontSize": "13px",
            "textAlign": "left",
            "borderRight": "none",
            "boxShadow": f"inset -1px 0 0 {THEME_BORDER}",
        },
        {
            "if": {"state": "active"},
            "backgroundColor": "var(--bs-primary-bg-subtle)",
            "border": "1px solid var(--bs-primary-bg-subtle)",
        },
        {
            "if": {"state": "selected"},
            "backgroundColor": "var(--bs-primary-bg-subtle)",
            "border": "1px solid var(--bs-primary-bg-subtle)",
        },
    ]
    for column_id in [col for col in ANGLE_BAR_COLORS if col in visible_ids]:
        max_value = max((_num(row, column_id) for row in table_data), default=0)
        if max_value <= 0:
            continue
        for row in table_data:
            pct = max(0, min(100, (_num(row, column_id) / max_value) * 100))
            row_bg = THEME_ROW_ODD if int(row["row_id"]) % 2 else THEME_ROW_EVEN
            styles.append(
                {
                    "if": {"filter_query": f"{{row_id}} = {row['row_id']}", "column_id": column_id},
                    "background": (
                        f"linear-gradient(90deg, {ANGLE_BAR_COLORS[column_id]} 0%, "
                        f"{ANGLE_BAR_COLORS[column_id]} {pct:.2f}%, {row_bg} {pct:.2f}%, {row_bg} 100%)"
                    ),
                }
            )
    return styles


def _narrative_angles_section(selected_label: str) -> html.Div:
    try:
        angles_df = data_manager[ANGLES_KEY].load()
    except Exception:
        angles_df = pd.DataFrame()

    if not angles_df.empty and "narrative_label" in angles_df.columns:
        angles_df = angles_df[angles_df["narrative_label"] == selected_label]
    else:
        angles_df = pd.DataFrame()

    records = [_json_safe(row) for row in angles_df.to_dict("records")]
    selected_sentiments = [opt["value"] for opt in ANGLE_SENTIMENT_OPTIONS]
    table_rows = _angles_table_rows(records, selected_sentiments)
    table_cols = _angles_table_columns()
    angle_options = [{"label": "All", "value": "All"}] + [
        {"label": r.get("angle_label", ""), "value": r.get("angle_label", "")}
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
                    "backgroundColor": "var(--amazon-publishers-header-bg)",
                    "border": f"1px solid {THEME_BORDER}",
                    "borderTop": "none",
                    "color": THEME_TEXT,
                    "fontWeight": "700",
                    "height": "34px",
                    "textAlign": "center",
                    "whiteSpace": "nowrap",
                    "overflow": "hidden",
                    "textOverflow": "ellipsis",
                },
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

_TOP_TABLES_LIMIT = 25
_TOP_TABLES_PAGE_SIZE = 9

_TOP_TABLE_STYLE_CELL = {
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
}

_TOP_TABLE_STYLE_HEADER = {
    "backgroundColor": "var(--amazon-publishers-header-bg)",
    "border": f"1px solid {THEME_BORDER}",
    "borderTop": "none",
    "color": THEME_TEXT,
    "fontWeight": "700",
    "height": "34px",
    "textAlign": "center",
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}


def _top_publishers_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "Publisher", "id": "publisher"},
        {"name": "Media Type / Platform", "id": "media_type_platform"},
        {
            "name": "Publications",
            "id": "publications",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": "Reach",
            "id": "reach",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
    ]


def _top_publishers_table_rows(records: list[dict[str, Any]], source: str | None) -> list[dict[str, Any]]:
    selected = source if source in ("Trad", "SoMe") else "Trad"
    filtered = [r for r in records if r.get("source") == selected]
    filtered.sort(key=lambda r: _num(r, "reach"), reverse=True)
    rows = []
    for idx, record in enumerate(filtered[:_TOP_TABLES_LIMIT]):
        rows.append(
            {
                "id": record.get("publisher", ""),
                "row_id": idx,
                "publisher": record.get("publisher", ""),
                "media_type_platform": record.get("media_type_platform", ""),
                "publications": _num(record, "publications"),
                "reach": _num(record, "reach"),
                "source": selected,
            }
        )
    return rows


def _data_bar_column_styles(
    table_data: list[dict[str, Any]],
    column_id: str,
    bar_color: Callable[[dict[str, Any]], str] | str,
) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = []
    max_value = max((_num(row, column_id) for row in table_data), default=0)
    if max_value <= 0:
        return styles
    for row in table_data:
        pct = max(0, min(100, (_num(row, column_id) / max_value) * 100))
        row_bg = THEME_ROW_ODD if int(row["row_id"]) % 2 else THEME_ROW_EVEN
        color = bar_color(row) if callable(bar_color) else bar_color
        styles.append(
            {
                "if": {"filter_query": f"{{row_id}} = {row['row_id']}", "column_id": column_id},
                "background": (
                    f"linear-gradient(90deg, {color} 0%, {color} {pct:.2f}%, "
                    f"{row_bg} {pct:.2f}%, {row_bg} 100%)"
                ),
            }
        )
    return styles


def _top_publishers_data_bar_styles(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {"if": {"column_id": "publisher"}, "textAlign": "left", "fontWeight": "500"},
        {"if": {"column_id": "media_type_platform"}, "textAlign": "left"},
    ]
    styles += _data_bar_column_styles(
        table_data,
        "reach",
        lambda row: (
            "var(--amazon-publishers-bar-trad-reach)"
            if row.get("source") == "Trad"
            else "var(--amazon-publishers-bar-some-reach)"
        ),
    )
    styles += _data_bar_column_styles(
        table_data,
        "publications",
        lambda row: (
            "var(--amazon-publishers-bar-trad-publications)"
            if row.get("source") == "Trad"
            else "var(--amazon-publishers-bar-some-posts)"
        ),
    )
    return styles


def _narrative_top_publishers_section(selected_label: str) -> html.Div:
    try:
        df = data_manager[NARRATIVE_TOP_PUBLISHERS_KEY].load()
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "narrative_label" in df.columns:
        df = df[df["narrative_label"] == selected_label]
    else:
        df = pd.DataFrame()

    records = [_json_safe(row) for row in df.to_dict("records")]
    table_rows = _top_publishers_table_rows(records, "Trad")
    table_cols = _top_publishers_table_columns()

    return na_panel(
        ref_label("Top Narrative Publishers", "P2S4T2"),
        [
            dcc.Store(id="amazon-2026-narrative-top-publishers-store", data=records),
            dash_table.DataTable(
                id="amazon-2026-narrative-top-publishers-table",
                data=table_rows,
                columns=table_cols,
                page_size=_TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=_TOP_TABLE_STYLE_CELL,
                style_header=_TOP_TABLE_STYLE_HEADER,
                style_data_conditional=_top_publishers_data_bar_styles(table_rows),
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


def _top_journalists_table_columns() -> list[dict[str, Any]]:
    return [
        {"name": "Journalist", "id": "journalist"},
        {
            "name": "Publications",
            "id": "publications",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
        {
            "name": "Reach",
            "id": "reach",
            "type": "numeric",
            "format": Format(group=True, precision=0, scheme=Scheme.fixed),
        },
    ]


_UNKNOWN_JOURNALIST_NAMES = {"unknown", "brak", "brak danych", "n/a", "na", "none", "-", ""}


def _top_journalists_table_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [
        r for r in records
        if str(r.get("journalist", "")).strip().lower() not in _UNKNOWN_JOURNALIST_NAMES
    ]
    sorted_records = sorted(filtered, key=lambda r: _num(r, "reach"), reverse=True)
    rows = []
    for idx, record in enumerate(sorted_records[:_TOP_TABLES_LIMIT]):
        rows.append(
            {
                "id": record.get("journalist", ""),
                "row_id": idx,
                "journalist": record.get("journalist", ""),
                "publications": _num(record, "publications"),
                "reach": _num(record, "reach"),
            }
        )
    return rows


def _top_journalists_data_bar_styles(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    styles: list[dict[str, Any]] = [
        {"if": {"row_index": "odd"}, "backgroundColor": THEME_ROW_ODD},
        {"if": {"column_id": "journalist"}, "textAlign": "left", "fontWeight": "500"},
    ]
    styles += _data_bar_column_styles(table_data, "reach", "var(--amazon-publishers-bar-trad-reach)")
    styles += _data_bar_column_styles(table_data, "publications", "var(--amazon-publishers-bar-trad-publications)")
    return styles


def _narrative_top_journalists_section(selected_label: str) -> html.Div:
    try:
        df = data_manager[NARRATIVE_TOP_JOURNALISTS_KEY].load()
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "narrative_label" in df.columns:
        df = df[df["narrative_label"] == selected_label]
    else:
        df = pd.DataFrame()

    records = [_json_safe(row) for row in df.to_dict("records")]
    table_rows = _top_journalists_table_rows(records)
    table_cols = _top_journalists_table_columns()

    return na_panel(
        ref_label("Top Journalists", "P2S4T3"),
        [
            dash_table.DataTable(
                id="amazon-2026-narrative-top-journalists-table",
                data=table_rows,
                columns=table_cols,
                page_size=_TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=_TOP_TABLE_STYLE_CELL,
                style_header=_TOP_TABLE_STYLE_HEADER,
                style_data_conditional=_top_journalists_data_bar_styles(table_rows),
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


def _filter_top_items_by_angle(records: list[dict[str, Any]], angle: str | None) -> list[dict[str, Any]]:
    if not angle or angle == "All":
        return records
    # Trad/SoMe rows aren't classified by angle yet (no angle data in BigQuery) —
    # don't blank the table out while that data is unavailable.
    if not any(r.get("Angle") for r in records):
        return records
    return [r for r in records if r.get("Angle") == angle]


def _narrative_top_items_panel(selected_label: str) -> html.Div:
    try:
        df = data_manager[NARRATIVE_TOP_PUBLICATIONS_KEY].load()
    except Exception:
        df = pd.DataFrame()

    if not df.empty and "narrative_label" in df.columns:
        df = df[df["narrative_label"] == selected_label]
    else:
        df = pd.DataFrame()

    records = [_json_safe(row) for row in df.to_dict("records")]
    trad_rows = [r for r in records if str(r.get("Source", "")) == "Trad"]
    some_rows = [r for r in records if str(r.get("Source", "")) == "SoMe"]

    trad_table_data = [
        {
            "Date": str(r.get("Date", "") or ""),
            "Media_Type": str(r.get("Type", "")),
            "Publication": str(r.get("Publication", "") or ""),
            "Title": str(r.get("Title", "")),
            "Summary": str(r.get("Summary", "")),
            "URL": f"[link]({r.get('URL', '')})" if str(r.get("URL", "")).startswith("http") else "",
            "Sentiment": str(r.get("Sentiment", "")),
            "Reach": _num(r, "Reach"),
            "Angle": str(r.get("Angle", "") or ""),
        }
        for r in trad_rows
    ]
    some_table_data = [
        {
            "Date": str(r.get("Date", "") or ""),
            "Platform": str(r.get("Type", "")),
            "Author": str(r.get("Author", "") or ""),
            "Post_Content": str(r.get("Summary", "")),
            "URL": f"[link]({r.get('URL', '')})" if str(r.get("URL", "")).startswith("http") else "",
            "Sentiment": str(r.get("Sentiment", "")),
            "Reach": _num(r, "Reach"),
            "Engagement": _num(r, "Engagement"),
            "Angle": str(r.get("Angle", "") or ""),
        }
        for r in some_rows
    ]

    panel_title = ref_label("Top Publications / Posts", "P2S4T4")
    return build_top_items_panel(
        "amazon-2026-narrative",
        panel_title,
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

    trad_pubs = int(_num(record, "trad_publications"))
    some_posts = int(_num(record, "some_posts"))
    total_pubs = trad_pubs + some_posts

    angles_count, angles_pos_share, angles_neg_share = _narrative_angles_overview(selected_label)

    cards = [
        _kpi_card(ref_label("Total Publications", "P2S4C1"), f"{total_pubs:,}"),
        _kpi_card(ref_label("Angles", "P2S4C2"), f"{angles_count:,}"),
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
                    _kpi_card(ref_label("Narratives", "P2S1C1"), f"{total_narratives:,}"),
                    _kpi_card(ref_label("Trad Publications in Narratives", "P2S1C2"), f"{share_pubs:.1%}"),
                    _kpi_card(ref_label("Part of Campaigns", "P2S1C3"), f"{share_campaign:.1%}"),
                ],
            ),
            html.Div(
                className="amazon-publishers-kpis",
                children=[
                    _kpi_card(ref_label("Angles", "P2S1C4"), f"{total_angles:,}"),
                    _kpi_card(ref_label("SoMe Posts in Narratives", "P2S1C5"), f"{share_posts:.1%}"),
                    _kpi_card(ref_label("Paid Content", "P2S1C6"), f"{share_paid:.1%}"),
                ],
            ),
        ],
    )


@capture("figure")
def narratives_kpi_panel(data_frame: pd.DataFrame) -> html.Div:
    return _build_narratives_kpi_section(data_frame)
