from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from vizro.managers import data_manager
from vizro.models.types import capture

from dashboards.amazon_2026.charts_shared import (
    ACCENT_SOME,
    ACCENT_TRAD,
    MEDIA_TYPE_COLORS,
    PLATFORM_COLORS,
    SENTIMENT_COLORS,
    THEME_BORDER,
    THEME_SURFACE,
    THEME_TEXT,
    _kpi_card,
    _num,
    build_top_items_panel,
    na_panel,
    register_top_items_callback,
)
from dashboards.amazon_2026.data_common import MEDIA_TYPE_ORDER, MONTH_ORDER, TOP_POSTS_KEY
from dashboards.amazon_2026.dev_ids import ref_label

_GRAPH_CONFIG = {"displayModeBar": False, "responsive": True}


def _theme_hoverlabel(size: int = 13) -> dict:
    return {
        "bgcolor": THEME_SURFACE,
        "bordercolor": THEME_BORDER,
        "font": {"color": THEME_TEXT, "size": size},
    }


def _overview_metric_title(data_frame: pd.DataFrame) -> str:
    metric = "publications"
    if "base_metric" in data_frame.columns and not data_frame.empty:
        selected = str(data_frame["base_metric"].iloc[0]).lower()
        if selected in {"publications", "reach"}:
            metric = selected
    return "Publications" if metric == "publications" else "Reach"


def _trad_tml_donut_figure(data_frame: pd.DataFrame, metric_title: str):
    fig = px.pie(
        data_frame=data_frame,
        names="tml_group",
        values="metric_value",
        hole=0.46,
    )

    fig.update_traces(
        textinfo="label+percent",
        textposition="inside",
        textfont=dict(color="white", size=14),
        marker=dict(line=dict(color=THEME_SURFACE, width=0.5)),
        sort=False,
        hovertemplate=(
            f"<b>%{{label}}</b><br>{metric_title}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>"
        ),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=12, r=12, t=12, b=12),
        showlegend=False,
        hoverlabel=_theme_hoverlabel(),
    )
    return fig


@capture("figure")
def trad_tml_donut_panel(data_frame: pd.DataFrame):
    metric_title = _overview_metric_title(data_frame)
    fig = _trad_tml_donut_figure(data_frame, metric_title)
    return na_panel(
        ref_label(f"{metric_title} by TML", "P1S2G1"),
        dcc.Graph(figure=fig, config=_GRAPH_CONFIG),
        box="panel",
    )


def _trad_media_type_period_donut_figure(data_frame: pd.DataFrame, metric_title: str):
    fig = px.pie(
        data_frame=data_frame,
        names="media_type",
        values="metric_value",
        hole=0.46,
        color="media_type",
        color_discrete_map=MEDIA_TYPE_COLORS,
        category_orders={"media_type": MEDIA_TYPE_ORDER},
    )
    fig.update_traces(
        textinfo="percent",
        textposition="inside",
        textfont=dict(color="white", size=13),
        marker=dict(line=dict(color=THEME_SURFACE, width=0.5)),
        sort=False,
        hovertemplate=(
            f"<b>%{{label}}</b><br>{metric_title}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>"
        ),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=12, r=12, t=12, b=12),
        uniformtext_minsize=11,
        uniformtext_mode="hide",
        legend=dict(orientation="v", x=1.02, y=0.5, title=None),
        hoverlabel=_theme_hoverlabel(),
    )
    return fig


@capture("figure")
def trad_media_type_period_donut_panel(data_frame: pd.DataFrame):
    metric_title = _overview_metric_title(data_frame)
    fig = _trad_media_type_period_donut_figure(data_frame, metric_title)
    return na_panel(
        ref_label(f"{metric_title} by Media Type (whole period)", "P1S2G2"),
        dcc.Graph(figure=fig, config=_GRAPH_CONFIG),
        box="panel",
    )


def _some_platform_donut_figure(data_frame: pd.DataFrame, metric_label: str):
    fig = px.pie(
        data_frame=data_frame,
        names="platform",
        values="metric_value",
        hole=0.46,
        color="platform",
        color_discrete_map=PLATFORM_COLORS,
    )
    fig.update_traces(
        textinfo="percent",
        textposition="inside",
        textfont=dict(color="white", size=13),
        marker=dict(line=dict(color=THEME_SURFACE, width=0.5)),
        sort=False,
        hovertemplate=(
            f"<b>%{{label}}</b><br>{metric_label}: %{{value:,.0f}}<br>Share: %{{percent}}<extra></extra>"
        ),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=12, r=12, t=12, b=12),
        uniformtext_minsize=11,
        uniformtext_mode="hide",
        legend=dict(orientation="v", x=1.02, y=0.5, title=None),
        hoverlabel=_theme_hoverlabel(),
    )
    return fig


@capture("figure")
def some_platform_donut_panel(data_frame: pd.DataFrame):
    metric = "publications"
    if "base_metric" in data_frame.columns and not data_frame.empty:
        selected = str(data_frame["base_metric"].iloc[0]).lower()
        if selected in {"publications", "reach"}:
            metric = selected

    if metric == "publications":
        title = "Posts by Platform"
        metric_label = "Posts"
    else:
        title = "Engagement by Platform"
        metric_label = "Engagement"

    fig = _some_platform_donut_figure(data_frame, metric_label)
    return na_panel(
        ref_label(title, "P1S2G3"),
        dcc.Graph(figure=fig, config=_GRAPH_CONFIG),
        box="panel",
    )


def _pubs_posts_reach_by_source_figure(data_frame: pd.DataFrame, metric: str, y_label: str):
    source_colors = {"Some": ACCENT_SOME, "Trad": ACCENT_TRAD}
    source_display = {"Trad": "Trad", "Some": "SoMe"}

    df = data_frame.copy()
    if "base_metric" in df.columns:
        df = df[df["base_metric"] == metric]
    if "month_num" in df.columns:
        df = df.sort_values(["month_num", "source_group"])

    agg = df.groupby(["month_num", "month_label", "source_group"], as_index=False)["metric_value"].sum()
    present_months = [m for m in MONTH_ORDER if (agg["month_label"] == m).any()] or MONTH_ORDER
    total_df = agg.groupby("source_group", as_index=False)["metric_value"].sum().assign(month_num=13, month_label="Total")
    plot_df = pd.concat([agg, total_df], ignore_index=True)
    x_order = present_months + ["Total"]
    plot_df = plot_df[plot_df["month_label"].isin(x_order)]
    max_value = float(plot_df["metric_value"].max()) if not plot_df.empty else 0.0
    y_axis_max = max_value * 1.18 if max_value > 0 else 1.0

    # Match the sentiment chart's hierarchical x-axis: source labels on the ticks,
    # months as annotations underneath each pair of bars.
    slot_width = 2.6
    total_extra_gap = 1.2
    bar_width = 0.9

    x_pos: dict[tuple[str, str], float] = {}
    tick_vals: list[float] = []
    tick_text: list[str] = []
    month_annotations: list[dict] = []

    for i, month in enumerate(x_order):
        extra = total_extra_gap if month == "Total" else 0.0
        base = i * slot_width + extra
        x_trad = base
        x_some = base + 1.0
        x_pos[(month, "Trad")] = x_trad
        x_pos[(month, "Some")] = x_some
        tick_vals.extend([x_trad, x_some])
        tick_text.extend([source_display["Trad"], source_display["Some"]])
        month_annotations.append(
            dict(
                x=(x_trad + x_some) / 2,
                y=-0.13,
                xref="x",
                yref="paper",
                text=f"<b>{month}</b>",
                showarrow=False,
                font=dict(color=THEME_TEXT, size=11),
                xanchor="center",
                yanchor="top",
                borderpad=4,
            )
        )

    fig = go.Figure()
    for source_group in ["Trad", "Some"]:
        sub = plot_df[plot_df["source_group"] == source_group]
        x_vals: list[float] = []
        y_vals: list[float] = []
        hover_labels: list[str] = []
        text_labels: list[str] = []

        for _, row in sub.iterrows():
            key = (row["month_label"], row["source_group"])
            if key in x_pos:
                value = float(row["metric_value"])
                x_vals.append(x_pos[key])
                y_vals.append(value)
                hover_labels.append(f"{row['month_label']} · {source_display[row['source_group']]}")
                text_labels.append(f"{value:,.0f}")

        if not x_vals:
            continue

        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=y_vals,
                name=source_group,
                marker_color=source_colors[source_group],
                width=bar_width,
                text=text_labels,
                textposition="outside",
                textfont=dict(size=10, color=THEME_TEXT),
                insidetextanchor="middle",
                customdata=[[lbl] for lbl in hover_labels],
                hovertemplate=(
                    f"<b>{source_display[source_group]}</b><br>"
                    "%{customdata[0]}<br>"
                    f"{y_label}: %{{y:,.0f}}<extra></extra>"
                ),
                cliponaxis=False,
            )
        )

    x_max = max(x_pos.values()) + 1.2 if x_pos else 1.0
    fig.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=26, r=26, t=12, b=72),
        xaxis=dict(
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(size=11, color=THEME_TEXT),
            range=[-0.8, x_max],
            title=None,
        ),
        yaxis=dict(title=y_label, tickformat=",", tickfont=dict(size=11), title_font=dict(size=11), range=[0, y_axis_max]),
        legend=dict(orientation="v", x=1.02, y=0.5, title=None),
        annotations=month_annotations,
        hoverlabel=_theme_hoverlabel(),
    )
    return fig


@capture("figure")
def pubs_posts_reach_by_source_panel(data_frame: pd.DataFrame):
    metric = "publications"
    if "base_metric" in data_frame.columns and not data_frame.empty:
        bm = str(data_frame["base_metric"].iloc[0]).lower()
        if bm in {"publications", "reach"}:
            metric = bm

    y_label = "Count" if metric == "publications" else "Reach"
    title = "Publications and Posts Count" if metric == "publications" else "Reach Sum"

    fig = _pubs_posts_reach_by_source_figure(data_frame, metric, y_label)
    return na_panel(
        ref_label(title, "P1S3G1"),
        dcc.Graph(figure=fig, config=_GRAPH_CONFIG),
        box="panel",
    )


P1S4G1_GROUPS = ["Trad", "SoMe", "Engagement"]


def _trad_source_sentiment_monthly_split_figure(data_frame: pd.DataFrame, visible_groups: list[str] | None = None):
    df = data_frame.copy()
    source_remap = {"Some": "SoMe"}
    active_groups = [g for g in P1S4G1_GROUPS if g in (visible_groups if visible_groups is not None else P1S4G1_GROUPS)]
    # Reversed order: Negative bottom → Neutral middle → Positive top
    sentiment_order_plot = ["Negative", "Neutral", "Positive"]

    df["source_group"] = df["source_group"].replace(source_remap)

    if "month_num" in df.columns:
        df = df.sort_values(["month_num", "source_group", "sentiment"])

    agg = df.groupby(["month_num", "month_label", "source_group", "sentiment"], as_index=False)["metric_value"].sum()
    present_months = [m for m in MONTH_ORDER if (agg["month_label"] == m).any()]
    if not present_months:
        present_months = MONTH_ORDER

    total_df = (
        agg.groupby(["source_group", "sentiment"], as_index=False)["metric_value"]
        .sum()
        .assign(month_num=13, month_label="Total")
    )
    plot_df = pd.concat([agg, total_df], ignore_index=True)

    # Share % within each (month_label, source_group) pair
    plot_df["share_pct"] = plot_df.groupby(["month_label", "source_group"])["metric_value"].transform(
        lambda s: (s / s.sum() * 100) if s.sum() else 0
    )

    # Numeric x positions: monthly slots use slot_width=2.6, Total gets extra gap
    all_months = present_months + ["Total"]
    slot_width = 3.6
    total_extra_gap = 1.2  # additional gap before Total column
    bar_width = 0.9

    x_pos: dict[tuple, float] = {}
    tick_vals: list[float] = []
    tick_text: list[str] = []
    month_annotations: list[dict] = []

    for i, month in enumerate(all_months):
        extra = total_extra_gap if month == "Total" else 0.0
        base = i * slot_width + extra
        for j, group in enumerate(active_groups):
            x_pos[(month, group)] = base + j * 1.0
            tick_vals.append(base + j * 1.0)
            tick_text.append(group)
        mid = base + (len(active_groups) - 1) / 2.0 if active_groups else base
        month_annotations.append(
            dict(
                x=mid,
                y=-0.13,
                xref="x",
                yref="paper",
                text=f"<b>{month}</b>",
                showarrow=False,
                font=dict(color=THEME_TEXT, size=11),
                xanchor="center",
                yanchor="top",
                borderpad=4,
            )
        )

    fig = go.Figure()
    for sentiment in sentiment_order_plot:
        sub = plot_df[plot_df["sentiment"] == sentiment]
        x_vals: list[float] = []
        y_vals: list[float] = []
        hover_labels: list[str] = []
        text_labels: list[str] = []

        for _, row in sub.iterrows():
            key = (row["month_label"], row["source_group"])
            if key in x_pos:
                pct = float(row["share_pct"])
                x_vals.append(x_pos[key])
                y_vals.append(pct)
                hover_labels.append(f"{row['month_label']} · {row['source_group']}")
                text_labels.append(f"{pct:.0f}%" if pct >= 8 else "")

        if not x_vals:
            continue

        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=y_vals,
                name=sentiment,
                marker_color=SENTIMENT_COLORS[sentiment],
                width=bar_width,
                text=text_labels,
                textposition="inside",
                textfont=dict(color="white", size=10),
                insidetextanchor="middle",
                customdata=[[lbl] for lbl in hover_labels],
                hovertemplate=(
                    f"<b>{sentiment}</b><br>"
                    "%{customdata[0]}<br>"
                    "Share: %{y:.1f}%<extra></extra>"
                ),
            )
        )

    x_max = max(x_pos.values()) + 1.2 if x_pos else 1.0
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=26, r=26, t=12, b=72),
        xaxis=dict(
            tickmode="array",
            tickvals=tick_vals,
            ticktext=tick_text,
            tickfont=dict(size=11, color=THEME_TEXT),
            range=[-0.8, x_max],
            title=None,
        ),
        yaxis=dict(title="Share", title_font=dict(size=11), ticksuffix="%", range=[0, 100]),
        legend=dict(orientation="v", x=1.02, y=0.5, title=None),
        annotations=month_annotations,
        hoverlabel=_theme_hoverlabel(),
    )
    return fig


@capture("figure")
def trad_source_sentiment_monthly_split_panel(data_frame: pd.DataFrame):
    base_metric = "publications"
    if "base_metric" in data_frame.columns and not data_frame.empty:
        bm = str(data_frame["base_metric"].iloc[0]).lower()
        if bm in {"publications", "reach"}:
            base_metric = bm
    chart_title = (
        "Publications and Posts by Sentiment"
        if base_metric == "publications"
        else "Reach and Engagement by Sentiment"
    )

    fig = _trad_source_sentiment_monthly_split_figure(data_frame, visible_groups=P1S4G1_GROUPS)
    return na_panel(
        ref_label(chart_title, "P1S4G1"),
        [
            dcc.Store(id="amazon-2026-p1s4g1-data", data=data_frame.to_dict("records")),
            dcc.Graph(id="amazon-2026-p1s4g1-graph", figure=fig, config=_GRAPH_CONFIG),
        ],
        box="panel",
        controls=html.Div(
            className="amazon-publishers-chart-controls",
            children=[
                dcc.Checklist(
                    id="amazon-2026-p1s4g1-group-toggle",
                    options=[{"label": g, "value": g} for g in P1S4G1_GROUPS],
                    value=list(P1S4G1_GROUPS),
                    inline=True,
                    className="amazon-publishers-radio",
                ),
            ],
        ),
    )


@callback(
    Output("amazon-2026-p1s4g1-graph", "figure"),
    Input("amazon-2026-p1s4g1-group-toggle", "value"),
    State("amazon-2026-p1s4g1-data", "data"),
)
def _update_p1s4g1_graph(visible_groups, records):
    df = pd.DataFrame(records or [])
    return _trad_source_sentiment_monthly_split_figure(df, visible_groups=visible_groups or [])


@capture("figure")
def overview_top_items_panel(data_frame: pd.DataFrame):
    articles_df = data_frame.copy()
    for col in ["Date", "Media_Type", "Publication", "Title", "Summary", "URL", "Sentiment", "Reach"]:
        if col not in articles_df.columns:
            articles_df[col] = ""
    trad_table_data = [
        {
            "Date": str(row.get("Date", "") or ""),
            "Media_Type": str(row.get("Media_Type", "")),
            "Publication": str(row.get("Publication", "")),
            "Title": str(row.get("Title", "")),
            "Summary": str(row.get("Summary", "")),
            "URL": f"[link]({row['URL']})" if str(row.get("URL", "")).startswith("http") else "",
            "Sentiment": str(row.get("Sentiment", "")),
            "Reach": _num(row, "Reach"),
        }
        for _, row in articles_df.iterrows()
    ]

    posts_df = data_manager[TOP_POSTS_KEY].load()
    for col in ["Date", "Platform", "Author", "Post_Content", "URL", "Sentiment", "Reach", "Engagement"]:
        if col not in posts_df.columns:
            posts_df[col] = ""
    some_table_data = [
        {
            "Date": str(row.get("Date", "") or ""),
            "Platform": str(row.get("Platform", "")),
            "Author": str(row.get("Author", "")),
            "Post_Content": str(row.get("Post_Content", "")),
            "URL": f"[link]({row['URL']})" if str(row.get("URL", "")).startswith("http") else "",
            "Sentiment": str(row.get("Sentiment", "")),
            "Reach": _num(row, "Reach"),
            "Engagement": _num(row, "Engagement"),
        }
        for _, row in posts_df.iterrows()
    ]

    panel_title = ref_label("Top Publications / Posts", "P1S5T1")
    return build_top_items_panel(
        "amazon-2026-overview",
        panel_title,
        trad_table_data,
        some_table_data,
        show_publication_col=True,
        show_author_col=True,
    )


register_top_items_callback("amazon-2026-overview", show_publication_col=True, show_author_col=True)


@capture("figure")
def overview_kpi_panel(data_frame: pd.DataFrame):
    row = data_frame.iloc[0].to_dict() if not data_frame.empty else {}

    reach_mln = _num(row, "total_reach") / 1_000_000
    pubs_k = _num(row, "total_publications") / 1_000
    posts_k = _num(row, "total_posts") / 1_000
    engagement_k = _num(row, "total_engagement") / 1_000
    trad_with_some = int(_num(row, "trad_with_some"))

    trad_panel = na_panel(
        ref_label("Traditional Media", "P1S1N1"),
        html.Div(
            className="amazon-publishers-kpis",
            children=[
                _kpi_card(ref_label("Total Reach", "P1S1N1C1"), f"{reach_mln:,.1f} mln"),
                _kpi_card(ref_label("Publications", "P1S1N1C2"), f"{pubs_k:,.1f} k"),
                _kpi_card(ref_label("Linked Trad+SoMe", "P1S1N1C3"), f"{trad_with_some:,}"),
            ],
        ),
        box="outline",
    )
    some_panel = na_panel(
        ref_label("Social Media", "P1S1N2"),
        html.Div(
            className="amazon-publishers-kpis amazon-publishers-kpis--2col",
            children=[
                _kpi_card(ref_label("Posts", "P1S1N2C1"), f"{posts_k:,.1f} k"),
                _kpi_card(ref_label("Engagement", "P1S1N2C2"), f"{engagement_k:,.1f} k"),
            ],
        ),
        box="outline",
    )
    return html.Div(className="amazon-overview-kpi-grid", children=[trad_panel, some_panel])
