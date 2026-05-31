"""
Custom Vizro chart functions for the Amazon media analytics dashboard.

Each function is decorated with @capture("graph") so Vizro can:
  - inject filtered DataFrames via its filter/parameter callback system
  - re-render automatically when any control changes
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from vizro.models.types import capture

# ── Design tokens ──────────────────────────────────────────────────────────────
DARK_BG    = "#181820"
SURFACE_BG = "#23232e"
GRID_COL   = "#2a2a3e"

SENT_COLORS = {
    "positive": "#4caf50",
    "neutral":  "#2196f3",
    "negative": "#f44336",
}
SENT_FILL = {
    "positive": "rgba(76,175,80,0.25)",
    "neutral":  "rgba(33,150,243,0.25)",
    "negative": "rgba(244,67,54,0.25)",
}
SENT_ORDER = ["positive", "neutral", "negative"]


def _dt_to_ms(dt) -> int:
    return int(pd.Timestamp(dt).value // 1_000_000)


def _reach_gradient_color(r: float, r_min: float, r_max: float) -> str:
    t   = (r - r_min) / (r_max - r_min) if r_max > r_min else 0.5
    low = np.array([0x1e, 0x6b, 0x8c])
    hi  = np.array([0xb5, 0xcc, 0x2e])
    c   = (low + t * (hi - low)).astype(int)
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


# ── Chart 1: Dual-axis reach / engagement timeline ─────────────────────────────
@capture("graph")
def reach_engagement_timeline(data_frame: pd.DataFrame) -> go.Figure:
    """
    Dual y-axis weekly line chart.
      Left  axis (solid lines)  = Traditional Media Reach
      Right axis (dotted lines) = Social Media Engagement
    Coloured by sentiment; filters applied by Vizro before this function runs.
    """
    agg = (
        data_frame
        .groupby(["week_start", "sentiment"], as_index=False)[["reach", "engagement"]]
        .sum()
        .sort_values("week_start")
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    for sentiment in SENT_ORDER:
        sub = agg[agg["sentiment"] == sentiment]
        if sub.empty:
            continue
        color = SENT_COLORS[sentiment]
        label = sentiment.capitalize()

        # Reach — solid line, left axis
        fig.add_trace(go.Scatter(
            x=sub["week_start"],
            y=sub["reach"],
            name=label,
            line=dict(color=color, width=2.5),
            legendgroup=sentiment,
            hovertemplate=f"<b>{label} Reach</b>: %{{y:,.0f}}<extra></extra>",
        ), secondary_y=False)

        # Engagement — dotted line, right axis
        fig.add_trace(go.Scatter(
            x=sub["week_start"],
            y=sub["engagement"],
            name=f"{label} (eng.)",
            line=dict(color=color, width=1.8, dash="dot"),
            legendgroup=sentiment,
            showlegend=False,
            hovertemplate=f"<b>{label} Engagement</b>: %{{y:,.0f}}<extra></extra>",
        ), secondary_y=True)

    axis_style = dict(gridcolor=GRID_COL, zeroline=True, zerolinecolor=GRID_COL,
                      zerolinewidth=1, color="white")

    fig.update_yaxes(title_text="<b>Traditional Media Reach</b>",
                     **axis_style, secondary_y=False)
    fig.update_yaxes(title_text="<b>Social Media Engagement</b>",
                     **axis_style, secondary_y=True)
    fig.update_xaxes(gridcolor=GRID_COL, color="white", tickformat="%b %Y",
                     showgrid=True)
    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white", family="Arial, sans-serif"),
        hovermode="x unified",
        height=480,
        legend=dict(
            bgcolor="rgba(255,255,255,0.05)",
            bordercolor=GRID_COL, borderwidth=1,
            orientation="h", y=1.02, x=0,
            title=dict(text="  Sentiment  ·  solid = Reach  ·  dotted = Engagement",
                       font=dict(size=10, color="#aaaacc")),
        ),
        margin=dict(l=70, r=90, t=50, b=30),
    )
    return fig


# ── Chart 2: Campaign Gantt timeline ──────────────────────────────────────────
@capture("graph")
def campaign_gantt(data_frame: pd.DataFrame) -> go.Figure:
    """
    Horizontal Gantt bars coloured by total reach (blue-low → yellow-high).
    Uses ms timestamps on a date-typed x-axis so bars align with the timeline above.
    """
    if data_frame.empty:
        return go.Figure(layout=dict(
            paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
            font=dict(color="white"),
            annotations=[dict(text="No campaigns selected", showarrow=False,
                              font=dict(size=14, color="#888"), xref="paper", yref="paper",
                              x=0.5, y=0.5)],
        ))

    plot_df = data_frame.sort_values("campaign_start").reset_index(drop=True)
    reaches = plot_df["reach"].values.astype(float)
    r_min, r_max = reaches.min(), reaches.max()

    fig = go.Figure()
    for _, row in plot_df.iterrows():
        start_ms = _dt_to_ms(row["campaign_start"])
        dur_ms   = _dt_to_ms(row["campaign_end"]) - start_ms
        color    = _reach_gradient_color(row["reach"], r_min, r_max)
        label    = f"reach: {int(row['reach']):,}".replace(",", "\u202f")
        fig.add_trace(go.Bar(
            x=[dur_ms],
            y=[row["campaign_label"]],
            base=[start_ms],
            orientation="h",
            marker_color=color,
            marker_line_color="rgba(0,0,0,0.4)",
            marker_line_width=1,
            text=[label],
            textposition="inside",
            insidetextanchor="start",
            textfont=dict(color="#0d1117", size=11, family="Courier New, monospace"),
            name=row["campaign_label"],
            showlegend=False,
            hovertemplate=(
                f"<b>{row['campaign_label']}</b><br>"
                f"Start: {pd.Timestamp(row['campaign_start']).strftime('%b %d, %Y')}<br>"
                f"End:   {pd.Timestamp(row['campaign_end']).strftime('%b %d, %Y')}<br>"
                f"Total Reach: {int(row['reach']):,}<extra></extra>".replace(",", "\u202f")
            ),
        ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white", family="Arial, sans-serif"),
        barmode="overlay",
        height=220,
        xaxis=dict(type="date", tickformat="%b\n%Y", gridcolor=GRID_COL,
                   color="white", showgrid=True),
        yaxis=dict(color="white", showgrid=False, autorange="reversed",
                   tickfont=dict(size=11)),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


# ── Chart 3: Total reach by narrative & sentiment (grouped bar) ────────────────
@capture("graph")
def narrative_reach_bar(data_frame: pd.DataFrame) -> go.Figure:
    """
    Horizontal grouped-bar chart: total reach per narrative per sentiment.
    Excludes the "All narratives" aggregate row.
    """
    df = data_frame[data_frame["narrative_label"] != "All narratives"]
    if df.empty:
        return go.Figure(layout=dict(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                                     font=dict(color="white")))

    agg = df.groupby(["narrative_label", "sentiment"], as_index=False)[["reach", "engagement"]].sum()

    # Shorten long labels for display
    short = {n: (n[:38] + "…" if len(n) > 38 else n) for n in agg["narrative_label"].unique()}

    fig = go.Figure()
    for sentiment in SENT_ORDER:
        sub = agg[agg["sentiment"] == sentiment]
        if sub.empty:
            continue
        fig.add_trace(go.Bar(
            x=sub["reach"],
            y=sub["narrative_label"].map(short),
            name=sentiment.capitalize(),
            marker_color=SENT_COLORS[sentiment],
            orientation="h",
            customdata=sub[["engagement"]].values,
            hovertemplate=(
                f"<b>{sentiment.capitalize()}</b><br>"
                "Reach: %{x:,.0f}<br>"
                "Engagement: %{customdata[0]:,.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white", family="Arial, sans-serif"),
        barmode="group",
        xaxis=dict(gridcolor=GRID_COL, color="white", title="Total Reach",
                   tickformat=","),
        yaxis=dict(color="white", showgrid=False, autorange="reversed"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor=GRID_COL,
                    borderwidth=1, title="Sentiment"),
        margin=dict(l=10, r=20, t=20, b=40),
    )
    return fig


# ── Chart 4: Stacked area reach over time by sentiment ─────────────────────────
@capture("graph")
def sentiment_stacked_area(data_frame: pd.DataFrame) -> go.Figure:
    """
    Stacked area chart of weekly total reach split by sentiment.
    Excludes "All narratives" to avoid double-counting.
    """
    df = data_frame[data_frame["narrative_label"] != "All narratives"]
    if df.empty:
        return go.Figure(layout=dict(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                                     font=dict(color="white")))

    agg = (
        df.groupby(["week_start", "sentiment"], as_index=False)["reach"]
        .sum()
        .sort_values("week_start")
    )

    fig = go.Figure()
    for sentiment in SENT_ORDER:
        sub = agg[agg["sentiment"] == sentiment]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["week_start"],
            y=sub["reach"],
            name=sentiment.capitalize(),
            stackgroup="one",
            line=dict(color=SENT_COLORS[sentiment], width=1.5),
            fillcolor=SENT_FILL[sentiment],
            hovertemplate=f"<b>{sentiment.capitalize()}</b>: %{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white", family="Arial, sans-serif"),
        hovermode="x unified",
        xaxis=dict(gridcolor=GRID_COL, color="white", tickformat="%b %Y"),
        yaxis=dict(gridcolor=GRID_COL, color="white", title="Total Reach",
                   tickformat=","),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor=GRID_COL,
                    borderwidth=1),
        margin=dict(l=60, r=20, t=20, b=30),
    )
    return fig


# ── Chart 5: Engagement ratio scatter (engagement / reach) ────────────────────
@capture("graph")
def engagement_ratio_scatter(data_frame: pd.DataFrame) -> go.Figure:
    """
    Scatter: reach (x) vs engagement (y) per narrative × sentiment.
    Bubble size = engagement-to-reach ratio × 1000.
    Reveals which narratives punch above their weight on social.
    """
    df = data_frame[data_frame["narrative_label"] != "All narratives"]
    if df.empty:
        return go.Figure(layout=dict(paper_bgcolor=DARK_BG, plot_bgcolor=DARK_BG,
                                     font=dict(color="white")))

    agg = df.groupby(["narrative_label", "sentiment"], as_index=False)[["reach", "engagement"]].sum()
    agg["ratio"] = (agg["engagement"] / agg["reach"].replace(0, np.nan)).fillna(0)
    agg["short_label"] = agg["narrative_label"].str.split(" and ").str[0].str[:30]

    fig = go.Figure()
    for sentiment in SENT_ORDER:
        sub = agg[agg["sentiment"] == sentiment]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["reach"],
            y=sub["engagement"],
            mode="markers+text",
            name=sentiment.capitalize(),
            marker=dict(
                color=SENT_COLORS[sentiment],
                size=sub["ratio"] * 5000 + 8,
                opacity=0.8,
                line=dict(color="white", width=0.5),
            ),
            text=sub["short_label"],
            textposition="top center",
            textfont=dict(size=9, color="white"),
            customdata=sub[["ratio", "narrative_label"]].values,
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                f"<i>{sentiment}</i><br>"
                "Reach: %{x:,.0f}<br>"
                "Engagement: %{y:,.0f}<br>"
                "Ratio: %{customdata[0]:.4f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="white", family="Arial, sans-serif"),
        xaxis=dict(gridcolor=GRID_COL, color="white", title="Total Reach", tickformat=","),
        yaxis=dict(gridcolor=GRID_COL, color="white", title="Total Engagement", tickformat=","),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor=GRID_COL,
                    borderwidth=1, title="Sentiment"),
        margin=dict(l=60, r=20, t=20, b=40),
    )
    return fig
