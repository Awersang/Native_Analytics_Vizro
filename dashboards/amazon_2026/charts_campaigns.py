"""Campaigns page — campaign timeline chart and campaign details section."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from vizro.managers import data_manager

from dashboards.amazon_2026.charts_publishers import (
    SOURCE_OPTIONS,
    _cell_width_styles,
    _data_bar_styles,
    _detail_kpi_groups,
    _dev_inline_label,
    _find_record,
    _header_divider_styles,
    _table_columns,
    _table_records,
)
from dashboards.amazon_2026.charts_narratives import (
    _TOP_TABLES_PAGE_SIZE,
    _build_shared_x_range,
    _narrative_detail_combined_weekly_figure,
    _top_journalists_data_bar_styles,
    _top_journalists_table_columns,
    _top_journalists_table_rows,
    _top_publishers_data_bar_styles,
    _top_publishers_table_columns,
    _top_publishers_table_rows,
)
from dashboards.amazon_2026.charts_shared import (
    ACCENT_SOME,
    ACCENT_TRAD,
    TABLE_STYLE_CELL,
    TABLE_STYLE_DATA,
    TABLE_STYLE_DATA_CONDITIONAL,
    TABLE_STYLE_HEADER,
    TOP_TABLE_STYLE_CELL,
    TOP_TABLE_STYLE_HEADER,
    THEME_BORDER,
    THEME_GRID,
    THEME_SURFACE,
    THEME_TEXT,
    TOOLTIP_CSS,
    TRAD_SOME_OPTIONS,
    _json_safe,
    _normalize_sources,
    _num,
    _timeline_available_sources,
    _timeline_chart_title,
    _timeline_figure,
    _timeline_records_from_frame,
    build_overview_table_section,
    build_top_items_panel,
    load_and_filter,
    na_panel,
    trad_some_controls,
)
from dashboards.amazon_2026.data_common import (
    CAMPAIGN_NARRATIVES_KEY,
    CAMPAIGN_PROFILE_KEY,
    CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY,
    CAMPAIGN_TOP_JOURNALISTS_KEY,
    CAMPAIGN_TOP_PUBLICATIONS_KEY,
    CAMPAIGN_TOP_PUBLISHERS_KEY,
    CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_WEEKLY_REACH_KEY,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label

MIN_BAR_SPAN_DAYS = 4
ROW_HEIGHT_PX = 36
CHART_PADDING_PX = 110

# Campaign timeline bars are colored by which source drove most of the
# campaign's reach: Trad-led (blue), SoMe-led (orange), or Mixed (neither
# side has a clear majority) — a third accent distinct from ACCENT_TRAD/SOME.
ACCENT_MIXED = "#8c6fc9"
_MIXED_SHARE_BAND = (0.35, 0.65)


def _campaign_bar_color(trad_reach: float, some_reach: float) -> str:
    total = trad_reach + some_reach
    if total <= 0:
        return ACCENT_MIXED
    trad_share = trad_reach / total
    low, high = _MIXED_SHARE_BAND
    if trad_share >= high:
        return ACCENT_TRAD
    if trad_share <= low:
        return ACCENT_SOME
    return ACCENT_MIXED


def _campaign_timeline_figure(data_frame: pd.DataFrame) -> go.Figure:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text="No campaign data available",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color=THEME_TEXT, size=13),
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=12, r=12, t=12, b=12),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df["total_reach"] = pd.to_numeric(df.get("total_reach", 0), errors="coerce").fillna(0)
    df["trad_reach"] = pd.to_numeric(df.get("trad_reach", 0), errors="coerce").fillna(0)
    df["some_reach"] = pd.to_numeric(df.get("some_reach", 0), errors="coerce").fillna(0)
    df = df.sort_values("start_date")

    min_span = pd.Timedelta(days=MIN_BAR_SPAN_DAYS)
    span = (df["end_date"] - df["start_date"]).clip(lower=min_span)
    bar_colors = [
        _campaign_bar_color(row["trad_reach"], row["some_reach"]) for _, row in df.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            base=df["start_date"].dt.strftime("%Y-%m-%d").tolist(),
            x=span.dt.total_seconds() * 1000,
            y=df["campaign"],
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color=THEME_SURFACE, width=1),
                cornerradius=6,
            ),
            text=[f"{value:,.0f}" for value in df["total_reach"]],
            textposition="outside",
            textfont=dict(color=THEME_TEXT, size=12),
            customdata=df.apply(
                lambda row: [
                    row["start_date"].strftime("%d %b %Y"),
                    row["end_date"].strftime("%d %b %Y"),
                    row["total_reach"],
                    row["trad_reach"],
                    row["some_reach"],
                ],
                axis=1,
            ).tolist(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{customdata[0]} – %{customdata[1]}<br>"
                "Reach: %{customdata[2]:,.0f}"
                " (Trad %{customdata[3]:,.0f} / SoMe %{customdata[4]:,.0f})"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    legend_entries = [
        ("Trad-led", ACCENT_TRAD),
        ("SoMe-led", ACCENT_SOME),
        ("Mixed", ACCENT_MIXED),
    ]
    for name, color in legend_entries:
        fig.add_trace(
            go.Bar(
                x=[None],
                y=[None],
                name=name,
                marker=dict(color=color),
                showlegend=True,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=12, r=80, t=36, b=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=THEME_TEXT, size=12),
            bgcolor="rgba(0,0,0,0)",
        ),
        bargap=0.35,
        xaxis=dict(
            type="date",
            tickformat="%b\n%Y",
            showgrid=True,
            gridcolor=THEME_GRID,
            side="bottom",
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=df["campaign"].tolist(),
            autorange="reversed",
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        hoverlabel=dict(bgcolor=THEME_SURFACE, bordercolor=THEME_BORDER, font=dict(color=THEME_TEXT, size=13)),
    )
    return fig


def _campaign_timeline_height(data_frame: pd.DataFrame) -> int:
    rows = max(len(data_frame), 1)
    return rows * ROW_HEIGHT_PX + CHART_PADDING_PX


def _campaign_type(row: pd.Series) -> str:
    has_trad = float(row.get("trad_article_count", 0) or 0) > 0
    has_some = float(row.get("some_post_count", 0) or 0) > 0
    if has_trad and has_some:
        return "Trad+SoMe"
    if has_trad:
        return "Trad"
    if has_some:
        return "SoMe"
    return "Unknown"


def _campaign_table_records(data_frame: pd.DataFrame, id_column: str = "campaign") -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    if id_column not in df.columns:
        df[id_column] = ""
    for column in [
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
    df["display_name"] = df[id_column].fillna("").astype(str)
    df["publisher_uid"] = df["display_name"]
    df["publisher_type"] = df.apply(_campaign_type, axis=1)
    return [_json_safe(record) for record in df.to_dict("records")]


def build_campaign_campaigns_section(data_frame: pd.DataFrame) -> html.Div:
    records = _campaign_table_records(data_frame)
    table_data = _table_records(records)
    columns = _table_columns("All")
    columns[0] = {"name": ["", "Campaign"], "id": "display_name"}
    controls = html.Div(
        className="amazon-publishers-controls",
        children=[
            html.Div(
                className="amazon-publishers-control amazon-publishers-source-control",
                children=[
                    html.Div("Source", className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id="amazon-2026-campaign-campaign-source-filter",
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
        store_id="amazon-2026-campaign-campaigns-data",
        section_title=ref_label("Campaigns Overview", "P6S3"),
        controls=controls,
        dev_label=_dev_inline_label("P6S3T1", "Campaigns Table"),
        table_id="amazon-2026-campaign-campaigns-table",
        table_data=table_data,
        columns=columns,
        style_cell_conditional=_cell_width_styles(),
        style_header_conditional=_header_divider_styles(columns),
        style_data_conditional=_data_bar_styles(table_data, columns),
    )


def build_campaign_timeline_panel(data_frame: pd.DataFrame) -> Any:
    height_px = _campaign_timeline_height(data_frame)
    return na_panel(
        ref_label("Campaign Timeline", "P7S1G1"),
        dcc.Graph(
            id="amazon-2026-campaign-timeline-graph",
            figure=_campaign_timeline_figure(data_frame),
            config={"displayModeBar": False, "responsive": True},
            style={"height": f"{height_px}px"},
            className="amazon-publishers-timeline-graph",
        ),
    )


# ---------------------------------------------------------------------------
# Campaign details section
# ---------------------------------------------------------------------------


def build_campaign_details_section(
    data_frame: pd.DataFrame,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    header_label: str = "Campaign Details",
    *,
    filter_column: str = "campaign",
    selector_label: str = "Campaign",
    placeholder: str = "Select campaign…",
    empty_label: str = "Select a campaign to see details.",
) -> html.Div:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    options_values = df[filter_column].dropna().tolist() if filter_column in df.columns else []
    options = [{"label": value, "value": value} for value in options_values]
    return html.Div(
        className="amazon-publishers-section amazon-publishers-details amazon-narrative-details",
        children=[
            html.Div(
                className="amazon-publishers-section-header",
                children=[html.H2(ref_label(header_label, ref_prefix))],
            ),
            html.Div(
                className="amazon-publishers-detail-selector",
                children=[
                    html.Div(selector_label, className="amazon-publishers-control-label"),
                    dcc.Dropdown(
                        id=f"{id_prefix}-detail-select",
                        options=options,
                        value=None,
                        searchable=True,
                        clearable=True,
                        persistence=True,
                        persistence_type="session",
                        placeholder=placeholder,
                        className="amazon-publishers-dropdown",
                    ),
                ],
            ),
            html.Div(
                id=f"{id_prefix}-details-content",
                children=_campaign_detail_content(None, id_prefix, ref_prefix, empty_label=empty_label),
            ),
        ],
    )


def _campaign_associated_narratives_table(
    selected_campaign: str,
    *,
    filter_column: str = "campaign",
    narratives_key: str = CAMPAIGN_NARRATIVES_KEY,
) -> html.Div:
    df = load_and_filter(narratives_key, filter_column, selected_campaign)

    if df.empty:
        return html.Div("No associated narratives available.", className="amazon-publishers-empty")

    table_data = [
        {
            "narrative_label": str(row.get("narrative_label", "") or ""),
            "connection": str(row.get("connection", "") or ""),
            "rationale": str(row.get("rationale", "") or ""),
        }
        for row in df.to_dict("records")
    ]

    return dash_table.DataTable(
        id="amazon-2026-campaign-associated-narratives-table",
        data=table_data,
        columns=[
            {"name": "Narrative", "id": "narrative_label"},
            {"name": "Connection", "id": "connection"},
            {"name": "Rationale", "id": "rationale"},
        ],
        page_size=5,
        sort_action="native",
        filter_action="none",
        cell_selectable=False,
        style_as_list_view=True,
        style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
        style_cell={**TABLE_STYLE_CELL, "height": "auto", "whiteSpace": "normal", "overflow": "visible", "textOverflow": "clip"},
        style_header=TABLE_STYLE_HEADER,
        style_data={**TABLE_STYLE_DATA, "height": "auto"},
        style_data_conditional=TABLE_STYLE_DATA_CONDITIONAL,
        style_cell_conditional=[
            {"if": {"column_id": "narrative_label"}, "width": "220px", "minWidth": "220px"},
            {"if": {"column_id": "connection"}, "width": "100px", "minWidth": "100px", "maxWidth": "100px"},
        ],
        css=TOOLTIP_CSS,
    )


def _campaign_profile_panel(
    selected_campaign: str,
    *,
    filter_column: str = "campaign",
    profile_key: str = CAMPAIGN_PROFILE_KEY,
    narratives_key: str = CAMPAIGN_NARRATIVES_KEY,
) -> html.Div:
    try:
        df = data_manager[profile_key].load()
    except Exception:
        df = pd.DataFrame()

    record: dict[str, Any] = {}
    if not df.empty and filter_column in df.columns:
        matches = df[df[filter_column] == selected_campaign]
        if not matches.empty:
            record = _json_safe(matches.iloc[0].to_dict())

    description = str(record.get("profile") or "").strip()
    takeaways = [
        str(record.get(f"takeaway_{i}") or "").strip()
        for i in (1, 2, 3)
    ]
    takeaways = [t for t in takeaways if t]

    return html.Div(
        className="amazon-narrative-profile",
        children=[
            html.H3(selected_campaign, className="amazon-narrative-profile-title"),
            na_panel(
                ref_label("Campaign profile", "P7S2D1"),
                [
                    html.P(
                        description or "No campaign profile available.",
                        className="amazon-narrative-description-text",
                    )
                ],
                box="flat",
            ),
            na_panel(
                ref_label("Key Takeaways", "P7S2D2"),
                [
                    html.Div(
                        [html.Div(t, className="amazon-narrative-insight-card") for t in takeaways]
                        or [html.Div("No takeaways available.", className="amazon-narrative-insight-card")],
                        className="amazon-narrative-insights-grid",
                    ),
                    html.H4("Associated Narratives", className="amazon-narrative-subheading"),
                    _campaign_associated_narratives_table(
                        selected_campaign, filter_column=filter_column, narratives_key=narratives_key
                    ),
                ],
                box="flat",
            ),
        ],
    )


def _campaign_detail_content(
    selected_campaign: str | None,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    records: list[dict[str, Any]] | None = None,
    *,
    filter_column: str = "campaign",
    weekly_reach_key: str = CAMPAIGN_WEEKLY_REACH_KEY,
    some_weekly_engagement_key: str = CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY,
    trad_sentiment_key: str = CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY,
    some_sentiment_key: str = CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY,
    narratives_key: str | None = None,
    profile_key: str = CAMPAIGN_PROFILE_KEY,
    profile_narratives_key: str = CAMPAIGN_NARRATIVES_KEY,
    top_publishers_key: str = CAMPAIGN_TOP_PUBLISHERS_KEY,
    top_journalists_key: str = CAMPAIGN_TOP_JOURNALISTS_KEY,
    top_publications_key: str = CAMPAIGN_TOP_PUBLICATIONS_KEY,
    empty_label: str = "Select a campaign to see details.",
    top_publishers_title: str = "Top Campaign Publishers",
    show_top_journalists: bool = True,
    show_top_journalists_inline: bool = False,
    show_profile: bool = True,
) -> html.Div:
    if not selected_campaign:
        return html.Div(className="amazon-publishers-empty", children=empty_label)
    children = []
    selected_record = _find_record(records or [], selected_campaign)
    kpi_groups = []
    if selected_record is not None:
        trad_kpis, some_kpis = _detail_kpi_groups(selected_record)
        if trad_kpis:
            kpi_groups.append(html.Div(className="amazon-publishers-detail-kpis", children=trad_kpis))
        if some_kpis:
            kpi_groups.append(html.Div(className="amazon-publishers-detail-kpis", children=some_kpis))
    top_publishers_panel = _campaign_top_publishers_section(
        selected_campaign,
        id_prefix,
        ref_prefix,
        filter_column=filter_column,
        top_publishers_key=top_publishers_key,
        title=top_publishers_title,
    )
    top_journalists_panel = (
        _campaign_top_journalists_section(
            selected_campaign,
            id_prefix,
            ref_prefix,
            filter_column=filter_column,
            top_journalists_key=top_journalists_key,
        )
        if show_top_journalists
        else None
    )

    summary_children = [
        *kpi_groups,
        html.Div(
            className="amazon-narrative-tables-row",
            children=[top_publishers_panel, top_journalists_panel],
        )
        if show_top_journalists_inline and top_journalists_panel is not None
        else top_publishers_panel,
    ]
    if show_profile:
        children.append(
            html.Div(
                className="amazon-narrative-detail-grid",
                children=[
                    html.Div(className="amazon-narrative-detail-summary", children=summary_children),
                    html.Div(
                        className="amazon-narrative-profile-column",
                        children=[
                            _campaign_profile_panel(
                                selected_campaign,
                                filter_column=filter_column,
                                profile_key=profile_key,
                                narratives_key=profile_narratives_key,
                            )
                        ],
                    ),
                ],
            )
        )
    else:
        children.append(
            html.Div(className="amazon-narrative-detail-summary", children=summary_children)
        )
    children.extend(
        [
            _campaign_detail_timeline_section(
                selected_campaign, id_prefix, ref_prefix,
                filter_column=filter_column,
                weekly_reach_key=weekly_reach_key,
                some_weekly_engagement_key=some_weekly_engagement_key,
            ),
            _campaign_sentiment_timeline_section(
                selected_campaign, id_prefix, ref_prefix,
                filter_column=filter_column,
                trad_sentiment_key=trad_sentiment_key,
                some_sentiment_key=some_sentiment_key,
                narratives_key=narratives_key,
            ),
            top_journalists_panel
            if show_top_journalists and not show_top_journalists_inline
            else None,
            _campaign_top_items_panel(
                selected_campaign, id_prefix, ref_prefix,
                filter_column=filter_column,
                top_publications_key=top_publications_key,
            ),
        ]
    )
    return html.Div(className="amazon-publishers-detail-content", children=children)


def _campaign_detail_timeline_section(
    selected_campaign: str,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    *,
    filter_column: str = "campaign",
    weekly_reach_key: str = CAMPAIGN_WEEKLY_REACH_KEY,
    some_weekly_engagement_key: str = CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY,
) -> html.Div:
    trad_df = load_and_filter(weekly_reach_key, filter_column, selected_campaign)
    some_df = load_and_filter(some_weekly_engagement_key, filter_column, selected_campaign)

    x_range = _build_shared_x_range(trad_df, some_df)

    initial_fig = _narrative_detail_combined_weekly_figure(
        trad_df, some_df,
        trad_metric_col="weekly_publications", trad_label="Trad Publications", trad_cum_label="Trad Cumulative",
        some_metric_col="weekly_posts", some_label="SoMe Posts", some_cum_label="SoMe Cumulative",
        y_title="Publications / Posts", cum_title="Cumulative Publications / Posts",
        x_range=x_range, dtick=7 * 24 * 60 * 60 * 1000,
    )

    available_sources = _timeline_available_sources({"has_trad": not trad_df.empty, "has_some": not some_df.empty})
    selected_sources = _normalize_sources(available_sources, available_sources)

    return na_panel(
        html.Span(id=f"{id_prefix}-detail-timeline-title", children=ref_label("Publications and Posts", f"{ref_prefix}G1")),
        [
            dcc.Store(
                id=f"{id_prefix}-detail-timeline-store",
                data={
                    "trad": trad_df.to_dict("records") if not trad_df.empty else [],
                    "some": some_df.to_dict("records") if not some_df.empty else [],
                    "x_range": x_range,
                },
            ),
            dcc.Graph(
                id=f"{id_prefix}-detail-timeline-graph",
                figure=initial_fig,
                config={"displayModeBar": False, "responsive": True},
                style={"height": "360px"},
            ),
        ],
        controls=trad_some_controls(
            f"{id_prefix}-detail-timeline-source",
            available_sources,
            selected_sources,
            disable_unavailable=True,
            hide_when_single=False,
        ),
    )


logger = logging.getLogger(__name__)


def _normalize_narrative_label(label: Any) -> str:
    """Normalize a narrative label for case/whitespace-insensitive matching across datasets."""
    return str(label).strip().casefold()


def _campaign_associated_narrative_labels(
    selected_campaign: str,
    *,
    filter_column: str = "campaign",
    narratives_key: str = CAMPAIGN_NARRATIVES_KEY,
) -> list[str]:
    df = load_and_filter(narratives_key, filter_column, selected_campaign)
    if df.empty or "narrative_label" not in df.columns:
        return []
    labels = (
        df["narrative_label"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    return [label for label in labels.drop_duplicates().tolist() if label]


def _campaign_sentiment_timeline_section(
    selected_campaign: str,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    *,
    filter_column: str = "campaign",
    trad_sentiment_key: str = CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY,
    some_sentiment_key: str = CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY,
    narratives_key: str | None = None,
) -> html.Div:
    trad_df = load_and_filter(trad_sentiment_key, filter_column, selected_campaign)
    some_df = load_and_filter(some_sentiment_key, filter_column, selected_campaign)

    trad_metric, some_metric = "publications", "posts"
    timeline_data = {
        filter_column: selected_campaign,
        "trad_metric": trad_metric,
        "some_metric": some_metric,
        "trad_timeline": _timeline_records_from_frame(trad_df, id_field=filter_column),
        "some_timeline": _timeline_records_from_frame(some_df, id_field=filter_column),
        "has_trad": not trad_df.empty,
        "has_some": not some_df.empty,
    }

    narrative_labels: list[str] = []
    if narratives_key:
        narrative_labels = _campaign_associated_narrative_labels(
            selected_campaign, filter_column=filter_column, narratives_key=narratives_key
        )
    if narrative_labels:
        normalized_labels = {_normalize_narrative_label(label) for label in narrative_labels}
        try:
            narrative_trad_df = data_manager[NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY].load()
        except Exception:
            narrative_trad_df = pd.DataFrame()
        try:
            narrative_some_df = data_manager[NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY].load()
        except Exception:
            narrative_some_df = pd.DataFrame()

        if not narrative_trad_df.empty and "narrative_label" in narrative_trad_df.columns:
            trad_matches = narrative_trad_df["narrative_label"].map(_normalize_narrative_label).isin(
                normalized_labels
            )
            matched_trad_df = narrative_trad_df[trad_matches]
        else:
            matched_trad_df = pd.DataFrame()

        if not narrative_some_df.empty and "narrative_label" in narrative_some_df.columns:
            some_matches = narrative_some_df["narrative_label"].map(_normalize_narrative_label).isin(
                normalized_labels
            )
            matched_some_df = narrative_some_df[some_matches]
        else:
            matched_some_df = pd.DataFrame()

        if matched_trad_df.empty and matched_some_df.empty:
            available_trad_labels = (
                sorted(narrative_trad_df["narrative_label"].dropna().unique().tolist())
                if not narrative_trad_df.empty and "narrative_label" in narrative_trad_df.columns
                else []
            )
            available_some_labels = (
                sorted(narrative_some_df["narrative_label"].dropna().unique().tolist())
                if not narrative_some_df.empty and "narrative_label" in narrative_some_df.columns
                else []
            )
            logger.warning(
                "Campaign %r: associated narrative labels %r did not match any narrative sentiment "
                "timeline rows. Available trad labels: %r. Available some labels: %r.",
                selected_campaign,
                narrative_labels,
                available_trad_labels,
                available_some_labels,
            )

        timeline_data["narrative_labels"] = narrative_labels
        timeline_data["narrative_trad_timeline"] = _timeline_records_from_frame(
            matched_trad_df, id_field="narrative_label"
        )
        timeline_data["narrative_some_timeline"] = _timeline_records_from_frame(
            matched_some_df, id_field="narrative_label"
        )

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
    if narratives_key:
        options.append({"label": "Narratives", "value": "Narratives", "disabled": not narrative_labels})

    return na_panel(
        ref_label(_timeline_chart_title(trad_metric, some_metric), f"{ref_prefix}G2"),
        [
            dcc.Store(id=f"{id_prefix}-sentiment-timeline-data", data=timeline_data),
            dcc.Graph(
                id=f"{id_prefix}-sentiment-timeline-graph",
                figure=_timeline_figure(timeline_data, selected_sources, id_field=filter_column),
                config={"displayModeBar": False, "responsive": True},
                className="amazon-publishers-timeline-graph",
            ),
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.Checklist(
                    id=f"{id_prefix}-sentiment-timeline-source",
                    options=options,
                    value=selected_sources,
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


def _campaign_top_publishers_section(
    selected_campaign: str,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    *,
    filter_column: str = "campaign",
    top_publishers_key: str = CAMPAIGN_TOP_PUBLISHERS_KEY,
    title: str = "Top Campaign Publishers",
) -> html.Div:
    df = load_and_filter(top_publishers_key, filter_column, selected_campaign)

    records = [_json_safe(row) for row in df.to_dict("records")]
    table_rows = _top_publishers_table_rows(records, "Trad")
    table_cols = _top_publishers_table_columns()

    return na_panel(
        ref_label(title, f"{ref_prefix}T1"),
        [
            dcc.Store(id=f"{id_prefix}-top-publishers-store", data=records),
            dash_table.DataTable(
                id=f"{id_prefix}-top-publishers-table",
                data=table_rows,
                columns=table_cols,
                page_size=_TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=TOP_TABLE_STYLE_CELL,
                style_header=TOP_TABLE_STYLE_HEADER,
                style_data_conditional=_top_publishers_data_bar_styles(table_rows),
                css=[{"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"}],
            ),
            html.Div("No publisher data available for this campaign.", className="amazon-publishers-empty")
            if not records
            else None,
        ],
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.RadioItems(
                    id=f"{id_prefix}-top-publishers-source",
                    options=TRAD_SOME_OPTIONS,
                    value="Trad",
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


def _campaign_top_journalists_section(
    selected_campaign: str,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    *,
    filter_column: str = "campaign",
    top_journalists_key: str = CAMPAIGN_TOP_JOURNALISTS_KEY,
) -> html.Div:
    df = load_and_filter(top_journalists_key, filter_column, selected_campaign)

    records = [_json_safe(row) for row in df.to_dict("records")]
    table_rows = _top_journalists_table_rows(records)
    table_cols = _top_journalists_table_columns()

    return na_panel(
        ref_label("Top Journalists", f"{ref_prefix}T2"),
        [
            dash_table.DataTable(
                id=f"{id_prefix}-top-journalists-table",
                data=table_rows,
                columns=table_cols,
                page_size=_TOP_TABLES_PAGE_SIZE,
                sort_action="native",
                filter_action="none",
                cell_selectable=False,
                style_as_list_view=True,
                style_table={"overflowX": "auto", "width": "100%", "minWidth": "100%"},
                style_cell=TOP_TABLE_STYLE_CELL,
                style_header=TOP_TABLE_STYLE_HEADER,
                style_data_conditional=_top_journalists_data_bar_styles(table_rows),
                css=[{"selector": ".dash-spreadsheet-menu-item", "rule": "display: none !important;"}],
            ),
            html.Div("No journalist data available for this campaign.", className="amazon-publishers-empty")
            if not records
            else None,
        ],
    )


def _campaign_top_items_panel(
    selected_campaign: str,
    id_prefix: str = "amazon-2026-campaign",
    ref_prefix: str = "P7S2",
    *,
    filter_column: str = "campaign",
    top_publications_key: str = CAMPAIGN_TOP_PUBLICATIONS_KEY,
) -> html.Div:
    df = load_and_filter(top_publications_key, filter_column, selected_campaign)

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

    panel_title = ref_label("Top Publications / Posts", f"{ref_prefix}T3")
    return build_top_items_panel(
        id_prefix,
        panel_title,
        trad_table_data,
        some_table_data,
        show_publication_col=True,
        show_author_col=True,
        box="flat",
    )
