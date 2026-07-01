"""
Custom Vizro chart functions for the Narrative Breakdown dashboard.

Each function is decorated with @capture("graph") so Vizro can inject
filtered DataFrames via its filter/parameter callback system and re-render
automatically when any control changes.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from vizro.models.types import capture

DARK_BG  = "#181820"
GRID_COL = "#2a2a3e"

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


@capture("graph")
def narrative_reach_bar(data_frame: pd.DataFrame, barmode: str = "group") -> go.Figure:
    """Horizontal grouped-bar chart: total reach per narrative per sentiment."""
    df = data_frame
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
        barmode=barmode,
        xaxis=dict(gridcolor=GRID_COL, color="white", title="Total Reach",
                   tickformat=","),
        yaxis=dict(color="white", showgrid=False, autorange="reversed"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor=GRID_COL,
                    borderwidth=1, title="Sentiment"),
        margin=dict(l=10, r=20, t=20, b=40),
    )
    return fig


@capture("graph")
def sentiment_stacked_area(data_frame: pd.DataFrame, y_scale: str = "linear") -> go.Figure:
    """Stacked area chart of weekly total reach split by sentiment."""
    df = data_frame
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
                   type=y_scale, tickformat=","),
        legend=dict(bgcolor="rgba(255,255,255,0.05)", bordercolor=GRID_COL,
                    borderwidth=1),
        margin=dict(l=60, r=20, t=20, b=30),
    )
    return fig


@capture("graph")
def engagement_ratio_scatter(data_frame: pd.DataFrame) -> go.Figure:
    """Scatter: reach (x) vs engagement (y) per narrative × sentiment.

    Bubble size = engagement-to-reach ratio × 1000. Reveals which narratives
    punch above their weight on social.
    """
    df = data_frame
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
