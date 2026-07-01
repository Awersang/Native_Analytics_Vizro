"""Timeline geometry engine: PCHIP smoothing, flag-annotation pixel math, dynamic
height, and the Trad/SoMe source-selection helpers timeline figures are always
called alongside.

Split out of the old `charts_shared.py` god-file (see IMPROVEMENT_PLAN.md §5.4).
Depends only on `theme.py` (and `data_common.SENTIMENT_ORDER`) — `ui_components.py`
imports from here, never the other way around.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.interpolate import PchipInterpolator
from plotly.subplots import make_subplots

from dashboards.amazon_2026.data_common import SENTIMENT_ORDER
from dashboards.amazon_2026.theme import (
    SENTIMENT_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_SURFACE,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    hex_to_rgba,
    media_label_color,
    theme_hoverlabel,
)


def _add_empty_figure_annotation(fig: go.Figure, message: str, color: str = THEME_TEXT_MUTED) -> None:
    """Center a "no data" message in an otherwise-empty figure."""
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color=color, size=13),
    )


def _as_list(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _filter_trad_some(source_filter: list[str] | str | None) -> list[str]:
    return [v for v in _as_list(source_filter) if v in {"Trad", "SoMe"}]


def normalize_sources(
    source_filter: list[str] | str | None,
    available_sources: list[str],
) -> list[str]:
    selected = [s for s in _filter_trad_some(source_filter) if s in available_sources]
    if not available_sources:
        return []
    return selected or available_sources.copy()


def _normalized_narrative_sources(
    source_filter: list[str] | str | None,
    available_sources: list[str],
) -> list[str]:
    selected_sources = [s for s in _filter_trad_some(source_filter) if s in available_sources]
    if len(available_sources) <= 1:
        return available_sources.copy()
    return selected_sources or [available_sources[0]]


def timeline_available_sources(timeline_data: dict[str, Any] | None) -> list[str]:
    payload = timeline_data or {}
    available_sources: list[str] = []
    if payload.get("has_trad"):
        available_sources.append("Trad")
    if payload.get("has_some"):
        available_sources.append("SoMe")
    return available_sources


def _timeline_metric_frame(
    records: list[dict[str, Any]],
    entity_id: str,
    metric: str,
    id_field: str = "publisher_uid",
) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    df = df[
        (df[id_field].astype(str) == entity_id)
        & (df["base_metric"].astype(str) == metric)
    ].copy()
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df = df.dropna(subset=["week_start"]).sort_values(["week_start", "sentiment"])
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    return df


def _timeline_series_frame(
    records: list[dict[str, Any]],
    entity_id: str,
    metric: str,
    week_index: pd.DatetimeIndex | None = None,
    id_field: str = "publisher_uid",
) -> pd.DataFrame:
    df = _timeline_metric_frame(records, entity_id, metric, id_field)
    if df.empty:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    if week_index is None or week_index.empty:
        week_index = pd.date_range(df["week_start"].min(), df["week_start"].max(), freq="W-MON")
    rows: list[pd.DataFrame] = []
    for sentiment in SENTIMENT_ORDER:
        sub = df[df["sentiment"] == sentiment]
        rows.append(
            sub.groupby("week_start", as_index=True)["metric_value"]
            .sum()
            .reindex(week_index, fill_value=0)
            .rename_axis("week_start")
            .reset_index()
            .assign(sentiment=sentiment)
        )
    if not rows:
        return pd.DataFrame(columns=["week_start", "sentiment", "metric_value"])
    return pd.concat(rows, ignore_index=True)


def _timeline_date_bounds(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> tuple[pd.Timestamp, pd.Timestamp] | None:
    payload = timeline_data or {}
    entity_id = str(payload.get(id_field, ""))
    trad_metric = str(payload.get("trad_metric", "publications"))
    some_metric = str(payload.get("some_metric", "posts"))
    frames = [
        _timeline_metric_frame(payload.get("trad_timeline", []), entity_id, trad_metric, id_field),
        _timeline_metric_frame(payload.get("some_timeline", []), entity_id, some_metric, id_field),
    ]
    for label in payload.get("narrative_labels") or []:
        narrative_label = str(label)
        frames.append(_timeline_metric_frame(payload.get("narrative_trad_timeline", []), narrative_label, trad_metric, "narrative_label"))
        frames.append(_timeline_metric_frame(payload.get("narrative_some_timeline", []), narrative_label, some_metric, "narrative_label"))
    dates = [frame["week_start"] for frame in frames if not frame.empty and "week_start" in frame]
    if not dates:
        return None
    min_date = min(series.min() for series in dates)
    max_date = max(series.max() for series in dates)
    if pd.isna(min_date) or pd.isna(max_date):
        return None
    return min_date, max_date


def _timeline_week_index(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> pd.DatetimeIndex:
    bounds = _timeline_date_bounds(timeline_data, id_field)
    if bounds is None:
        return pd.DatetimeIndex([])
    return pd.date_range(bounds[0], bounds[1], freq="W-MON")


def _timeline_xaxis_range(timeline_data: dict[str, Any] | None, id_field: str = "publisher_uid") -> list[pd.Timestamp] | None:
    bounds = _timeline_date_bounds(timeline_data, id_field)
    if bounds is None:
        return None
    return [bounds[0], bounds[1]]


def _timeline_axis_title(source_label: str | None, trad_metric: str, some_metric: str) -> str:
    if trad_metric == "publications" and some_metric == "posts":
        return "Publications and Posts"
    if source_label == "Trad":
        return {"publications": "Trad Publications", "reach": "Trad Reach"}.get(trad_metric, trad_metric.title())
    if source_label == "SoMe":
        return {"posts": "SoMe Posts", "engagement": "SoMe Engagement"}.get(some_metric, some_metric.title())
    return "Metric"


def _timeline_uses_shared_count_scale(trad_metric: str, some_metric: str) -> bool:
    return trad_metric == "publications" and some_metric == "posts"


def _timeline_chart_title(trad_metric: str, some_metric: str) -> str:
    if trad_metric == "publications" and some_metric == "posts":
        return "Publications Timeline by Sentiment"
    if trad_metric == "reach" and some_metric == "engagement":
        return "Reach and Engagement by Sentiment"
    if trad_metric == "reach":
        return "Reach Timeline by Sentiment"
    if some_metric == "engagement":
        return "Engagement Timeline by Sentiment"
    return "Timeline by Sentiment"


def timeline_figure(
    timeline_data: dict[str, Any],
    source_filter: list[str] | str | None,
    id_field: str = "publisher_uid",
) -> go.Figure:
    available_sources = timeline_available_sources(timeline_data)
    selected_sources = normalize_sources(source_filter, available_sources)
    fig = go.Figure()
    combined_mode = len(selected_sources) > 1
    shared_count_scale = _timeline_uses_shared_count_scale(
        str(timeline_data.get("trad_metric", "publications")),
        str(timeline_data.get("some_metric", "posts")),
    )
    source_configs = {
        "Trad": {
            "records": timeline_data.get("trad_timeline", []),
            "metric": str(timeline_data.get("trad_metric", "publications")),
            "metric_labels": {"publications": "Publications", "reach": "Reach"},
            "axis": "y",
            "dash": "solid",
            "marker": "circle",
        },
        "SoMe": {
            "records": timeline_data.get("some_timeline", []),
            "metric": str(timeline_data.get("some_metric", "posts")),
            "metric_labels": {"posts": "Posts", "engagement": "Engagement"},
            "axis": "y2" if combined_mode and not shared_count_scale else "y",
            "dash": "dot",
            "marker": "diamond",
        },
    }
    entity_id = str(timeline_data.get(id_field, ""))
    shared_week_index = _timeline_week_index(timeline_data, id_field)

    for source_label in selected_sources:
        config = source_configs.get(source_label)
        if not config:
            continue
        metric = config["metric"]
        metric_label = config["metric_labels"].get(metric, metric.title())
        source_df = _timeline_series_frame(
            config["records"],
            entity_id,
            metric,
            shared_week_index,
            id_field,
        )
        if source_df.empty:
            continue
        fill_alpha = 0.08 if combined_mode else 0.14
        for sentiment in SENTIMENT_ORDER:
            sub = source_df[source_df["sentiment"] == sentiment]
            if sub.empty:
                continue
            trace_name = f"{source_label} {sentiment}" if combined_mode else sentiment
            fig.add_trace(
                go.Scatter(
                    x=sub["week_start"],
                    y=sub["metric_value"],
                    name=trace_name,
                    legendgroup=source_label,
                    mode="lines+markers",
                    line=dict(
                        width=2.5,
                        color=SENTIMENT_COLORS.get(sentiment),
                        shape="spline",
                        smoothing=0.45,
                        dash=config["dash"],
                    ),
                    marker=dict(size=6, color=SENTIMENT_COLORS.get(sentiment), symbol=config["marker"]),
                    fill="tozeroy",
                    fillcolor=hex_to_rgba(SENTIMENT_COLORS.get(sentiment), fill_alpha),
                    yaxis=config["axis"],
                    hovertemplate=(
                        f"<b>{trace_name}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        f"{metric_label}: %{{y:,.0f}}<extra></extra>"
                    ),
                )
            )
    if not fig.data:
        message = "Data temporarily unavailable" if timeline_data.get("load_failed") else "No weekly data"
        _add_empty_figure_annotation(fig, message)
    primary_label = _timeline_axis_title(
        selected_sources[0] if selected_sources else None,
        str(timeline_data.get("trad_metric", "publications")),
        str(timeline_data.get("some_metric", "posts")),
    )
    fig.update_layout(
        title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=26, r=26, t=18, b=46),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right", title=None),
        xaxis=dict(
            title=None,
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            range=_timeline_xaxis_range(timeline_data, id_field),
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        yaxis=dict(title=primary_label, tickformat=",", rangemode="tozero", showgrid=True, gridcolor=THEME_GRID),
        hoverlabel=theme_hoverlabel(),
    )
    if combined_mode and not shared_count_scale:
        fig.update_layout(
            yaxis2=dict(
                title=_timeline_axis_title(
                    "SoMe",
                    str(timeline_data.get("trad_metric", "publications")),
                    str(timeline_data.get("some_metric", "posts")),
                ),
                tickformat=",",
                rangemode="tozero",
                overlaying="y",
                side="right",
                showgrid=False,
                zeroline=False,
            )
        )
    return fig


def _nice_axis_step(max_value: float, target_ticks: int = 4) -> float:
    """Return a "nice" tick step (1/2/2.5/5 x10^n) covering `max_value` in ~`target_ticks` steps."""
    if max_value <= 0:
        return 1.0
    raw_step = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw_step))
    for multiple in (1, 2, 2.5, 5, 10):
        step = multiple * magnitude
        if step >= raw_step:
            return step
    return 10 * magnitude


def _media_split_weekly_pivot(data_frame: pd.DataFrame, group_col: str, value_col: str) -> pd.DataFrame:
    if data_frame is None or data_frame.empty:
        return pd.DataFrame()
    df = data_frame.copy()
    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    df = df.dropna(subset=["week_start"])
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(index="week_start", columns=group_col, values=value_col, aggfunc="sum", fill_value=0)
    return pivot.sort_index()


def top_reach_flags(top_publications_df: pd.DataFrame, source: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Return the top `top_n` publications/posts for `source` ("Trad"/"SoMe") by reach.

    Each flag dict has `label` (Publication for Trad, Author for SoMe), `value`
    (the reach), `date` (ISO date string), and `kind="reach"` — used to render
    flag annotations on `media_split_timeline_figure`.
    """
    if top_publications_df is None or top_publications_df.empty or "Source" not in top_publications_df.columns:
        return []
    subset = top_publications_df[top_publications_df["Source"] == source].copy()
    if subset.empty:
        return []
    subset["Reach"] = pd.to_numeric(subset["Reach"], errors="coerce").fillna(0)
    subset = subset.sort_values("Reach", ascending=False).head(top_n)
    label_col = "Publication" if source == "Trad" else "Author"
    flags = []
    for _, row in subset.iterrows():
        date = pd.to_datetime(row.get("Date"), errors="coerce")
        if pd.isna(date):
            continue
        label = str(row.get(label_col) or "Unknown").strip() or "Unknown"
        flags.append({"label": label, "value": float(row["Reach"]), "date": date.strftime("%Y-%m-%d"), "kind": "reach"})
    return flags


def _top_volume_week_flag(pivot: pd.DataFrame, stacked: bool, unit_label: str) -> dict[str, Any] | None:
    """Return a flag dict marking the week with the highest total `unit_label`
    (the same `totals` series used to anchor the reach flags), or `None` if
    there's no positive data."""
    if pivot.empty:
        return None
    totals = pivot.sum(axis=1) if stacked else pivot.max(axis=1)
    if totals.empty:
        return None
    week_start = totals.idxmax()
    value = float(totals.loc[week_start])
    if value <= 0:
        return None
    return {
        "label": f"Top week by {unit_label}",
        "value": value,
        "date": week_start.strftime("%Y-%m-%d"),
        "kind": "volume",
    }


def _add_reach_flag_annotations(
    fig: go.Figure,
    flags: list[dict[str, Any]] | None,
    pivot: pd.DataFrame,
    side: str,
    px_per_unit: float,
    stacked: bool = False,
) -> float:
    """Add flag annotations for top datapoints — 🚩 reach flags (publisher/author
    + reach) and ⭐ "top week by volume" flags (in `MEDIA_SPLIT_VOLUME_COLOR`).

    Returns the largest pixel distance (from the zero line) spanned by any flag's
    box, so callers can extend the axis range to keep every box inside the plot.
    """
    if not flags or pivot.empty:
        return 0.0
    week_index = pivot.index
    totals = pivot.sum(axis=1) if stacked else pivot.max(axis=1)
    sign = 1 if side == "trad" else -1
    week_slot: dict[pd.Timestamp, int] = {}
    placements: list[tuple[int, pd.Timestamp, float, dict[str, Any]]] = []
    for flag in flags:
        date = pd.to_datetime(flag.get("date"), errors="coerce")
        if pd.isna(date):
            continue
        week_start = (date - pd.Timedelta(days=date.weekday())).normalize()
        if week_start not in week_index:
            idx = week_index.get_indexer([week_start], method="nearest")[0]
            week_start = week_index[idx]
        base = float(totals.get(week_start, 0))
        slot = week_slot.get(week_start, 0)
        week_slot[week_start] = slot + 1
        placements.append((slot, week_start, base, flag))

    # Draw the farther-offset (higher-slot) flags first so their longer arrows
    # sit behind the closer flags' labels/arrows instead of covering them.
    placements.sort(key=lambda p: p[0], reverse=True)
    max_required_px = 0.0
    for slot, week_start, base, flag in placements:
        offset = 10 + slot * MEDIA_SPLIT_FLAG_SLOT_PX
        if flag.get("kind") == "volume":
            text = f"⭐ {flag['label']}: {flag['value']:,.0f}"
            accent = MEDIA_SPLIT_VOLUME_COLOR
            box_height = MEDIA_SPLIT_FLAG_BOX_HEIGHT_VOLUME
        else:
            text = f"\U0001F6A9 {flag['label']}<br>Reach: {flag['value']:,.0f}"
            accent = THEME_BORDER
            box_height = MEDIA_SPLIT_FLAG_BOX_HEIGHT_REACH
        fig.add_annotation(
            x=week_start,
            y=sign * base,
            text=text,
            showarrow=True,
            arrowhead=2,
            arrowsize=0.8,
            arrowcolor="#444",
            ax=0,
            ay=-offset if side == "trad" else offset,
            align="left",
            font=dict(size=10, color=THEME_TEXT),
            bgcolor=THEME_SURFACE,
            bordercolor=accent,
            borderwidth=1,
            borderpad=4,
            yanchor="bottom" if side == "trad" else "top",
        )
        required_px = abs(base) * px_per_unit + offset + box_height
        max_required_px = max(max_required_px, required_px)
    return max_required_px


def _smooth_nonnegative_curve(
    index: pd.DatetimeIndex, values: pd.Series, points_per_segment: int = 8
) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Upsample a weekly series with shape-preserving (PCHIP) interpolation so
    the rendered line looks smooth without the overshoot a cardinal/spline
    curve produces — e.g. dipping below zero between a zero week and a sharply
    rising one. PCHIP never exceeds the local min/max of neighbouring points,
    so a series that never goes negative stays non-negative once interpolated.
    """
    if len(values) < 3:
        return index, values.to_numpy()
    x_numeric = index.values.astype("datetime64[ns]").astype("int64")
    interpolator = PchipInterpolator(x_numeric, values.to_numpy())
    x_dense = np.linspace(x_numeric[0], x_numeric[-1], (len(x_numeric) - 1) * points_per_segment + 1)
    return pd.to_datetime(x_dense, unit="ns"), interpolator(x_dense)


MEDIA_SPLIT_AXIS_PIXELS_PER_TICK = 68
MEDIA_SPLIT_MARGIN_TOP_BASE = 20
MEDIA_SPLIT_MARGIN_BOTTOM_BASE = 40
MEDIA_SPLIT_MARGIN_LEFT = 70
MEDIA_SPLIT_MARGIN_RIGHT = 150
MEDIA_SPLIT_FLAG_SLOT_PX = 50
MEDIA_SPLIT_FLAG_BOX_HEIGHT_REACH = 38
MEDIA_SPLIT_FLAG_BOX_HEIGHT_VOLUME = 24
MEDIA_SPLIT_MIN_HEIGHT_PX = 480
MEDIA_SPLIT_VOLUME_COLOR = "#D3B745"


def media_split_timeline_figure(
    trad_df: pd.DataFrame,
    some_df: pd.DataFrame,
    stacked: bool = False,
    trad_flags: list[dict[str, Any]] | None = None,
    some_flags: list[dict[str, Any]] | None = None,
    load_failed: bool = False,
) -> tuple[go.Figure, int]:
    """Mirrored weekly timeline: Trad media types stacked/lined above zero, SoMe
    platforms below zero (plotted as negative but labelled/hover'd as positive).

    Returns ``(figure, height_px)`` — the height is sized to the data actually
    rendered (no leftover empty space at top/bottom) while keeping the same
    pixels-per-unit step on both halves of the y-axis, so equal Trad/SoMe
    values remain directly comparable even though their axis limits differ.
    """
    fig = go.Figure()

    trad_pivot = _media_split_weekly_pivot(trad_df, "media_type", "publications")
    some_pivot = _media_split_weekly_pivot(some_df, "platform", "posts")

    trad_extent = 0.0
    some_extent = 0.0

    if trad_pivot.empty and some_pivot.empty:
        failed = load_failed or bool(trad_df.attrs.get("load_failed")) or bool(some_df.attrs.get("load_failed"))
        _add_empty_figure_annotation(fig, "Data temporarily unavailable" if failed else "No weekly data")
    else:
        all_weeks = pd.DatetimeIndex(sorted(set(trad_pivot.index) | set(some_pivot.index)))
        if not trad_pivot.empty:
            trad_pivot = trad_pivot.reindex(all_weeks, fill_value=0)
        if not some_pivot.empty:
            some_pivot = some_pivot.reindex(all_weeks, fill_value=0)

        # Axis extent reflects what's actually drawn: the stacked total when
        # `stacked`, or the tallest individual line otherwise.
        if stacked:
            trad_extent = float(trad_pivot.sum(axis=1).max()) if not trad_pivot.empty else 0.0
            some_extent = float(some_pivot.sum(axis=1).max()) if not some_pivot.empty else 0.0
        else:
            trad_extent = float(trad_pivot.max().max()) if not trad_pivot.empty else 0.0
            some_extent = float(some_pivot.max().max()) if not some_pivot.empty else 0.0

        fill_mode = "tonexty" if stacked else "tozeroy"
        fill_alpha = 0.28 if stacked else 0.12
        stack_kwargs = {"stackgroup": "trad"} if stacked else {}

        for media_type in trad_pivot.columns:
            color = media_label_color(media_type, "Trad")
            smooth_x, smooth_y = _smooth_nonnegative_curve(trad_pivot.index, trad_pivot[media_type])
            fig.add_trace(
                go.Scatter(
                    x=smooth_x,
                    y=smooth_y,
                    name=f"Trad – {media_type}",
                    legendgroup="Trad",
                    mode="lines",
                    line=dict(width=2, color=color, shape="linear"),
                    fill=fill_mode,
                    fillcolor=hex_to_rgba(color, fill_alpha),
                    hovertemplate=(
                        f"<b>Trad – {media_type}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        "Publications: %{y:,.0f}<extra></extra>"
                    ),
                    **stack_kwargs,
                )
            )

        stack_kwargs = {"stackgroup": "some"} if stacked else {}
        for platform in some_pivot.columns:
            color = media_label_color(platform, "SoMe")
            smooth_x, smooth_y = _smooth_nonnegative_curve(some_pivot.index, -some_pivot[platform])
            fig.add_trace(
                go.Scatter(
                    x=smooth_x,
                    y=smooth_y,
                    name=f"SoMe – {platform}",
                    legendgroup="SoMe",
                    mode="lines",
                    line=dict(width=2, color=color, dash="dot", shape="linear"),
                    fill=fill_mode,
                    fillcolor=hex_to_rgba(color, fill_alpha),
                    customdata=-smooth_y,
                    hovertemplate=(
                        f"<b>SoMe – {platform}</b><br>"
                        "Week: %{x|%d %b %Y}<br>"
                        "Posts: %{customdata:,.0f}<extra></extra>"
                    ),
                    **stack_kwargs,
                )
            )

    # Both halves use the same step (pixels-per-unit), so equal Trad/SoMe
    # values sit the same distance from zero — but each half only extends as
    # far as its own data needs, instead of forcing a shared axis limit.
    step = _nice_axis_step(max(trad_extent, some_extent))
    trad_tick_count = max(1, math.ceil(trad_extent / step)) if trad_extent > 0 else 1
    some_tick_count = max(1, math.ceil(some_extent / step)) if some_extent > 0 else 1
    tickvals = (
        [-i * step for i in range(some_tick_count, 0, -1)]
        + [0]
        + [i * step for i in range(1, trad_tick_count + 1)]
    )
    ticktext = [f"{abs(v):,.0f}" for v in tickvals]

    px_per_unit = MEDIA_SPLIT_AXIS_PIXELS_PER_TICK / step

    trad_volume_flag = _top_volume_week_flag(trad_pivot, stacked, "pub.")
    some_volume_flag = _top_volume_week_flag(some_pivot, stacked, "posts")
    all_trad_flags = [*(trad_flags or []), *([trad_volume_flag] if trad_volume_flag else [])]
    all_some_flags = [*(some_flags or []), *([some_volume_flag] if some_volume_flag else [])]

    trad_required_px = _add_reach_flag_annotations(fig, all_trad_flags, trad_pivot, "trad", px_per_unit, stacked=stacked)
    some_required_px = _add_reach_flag_annotations(fig, all_some_flags, some_pivot, "some", px_per_unit, stacked=stacked)

    if trad_flags or some_flags:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=8, color=THEME_TEXT_MUTED, symbol="triangle-up"),
                name="Top 5 pub. by reach",
                showlegend=True,
                hoverinfo="skip",
            )
        )
    if trad_volume_flag or some_volume_flag:
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=8, color=MEDIA_SPLIT_VOLUME_COLOR, symbol="star"),
                name="Top week by pub.",
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Flag stacks extend the axis range beyond the data extent so their boxes
    # land inside the plot area instead of bleeding into the margins — that's
    # what keeps margins (and thus `height_px`) tight while still leaving room
    # for every flag.
    trad_tick_px = trad_tick_count * step * 1.05 * px_per_unit
    some_tick_px = some_tick_count * step * 1.05 * px_per_unit
    top_extra_px = max(0.0, trad_required_px - trad_tick_px)
    bottom_extra_px = max(0.0, some_required_px - some_tick_px)
    trad_edge = trad_tick_count * step * 1.05 + top_extra_px / px_per_unit
    some_edge = some_tick_count * step * 1.05 + bottom_extra_px / px_per_unit

    margin_t = MEDIA_SPLIT_MARGIN_TOP_BASE
    margin_b = MEDIA_SPLIT_MARGIN_BOTTOM_BASE
    axis_height = (trad_tick_count + some_tick_count) * MEDIA_SPLIT_AXIS_PIXELS_PER_TICK + top_extra_px + bottom_extra_px
    height_px = max(MEDIA_SPLIT_MIN_HEIGHT_PX, int(axis_height + margin_t + margin_b))

    # Section labels replace the old single (misleading) axis title — one
    # centred in the Trad half (above zero) and one in the SoMe half (below).
    fig.add_annotation(
        text="Trad publications",
        xref="paper",
        x=0,
        xshift=-58,
        yref="y",
        y=trad_edge / 2,
        showarrow=False,
        textangle=-90,
        font=dict(size=11, color=THEME_TEXT_MUTED),
        xanchor="center",
        yanchor="middle",
    )
    fig.add_annotation(
        text="SoMe posts",
        xref="paper",
        x=0,
        xshift=-58,
        yref="y",
        y=-some_edge / 2,
        showarrow=False,
        textangle=-90,
        font=dict(size=11, color=THEME_TEXT_MUTED),
        xanchor="center",
        yanchor="middle",
    )

    # Explicit zero line drawn above the data traces — with many overlapping
    # filled lines converging on zero, the axis's own zeroline gets lost
    # underneath them, so draw a same-thickness gray line on top instead.
    fig.add_shape(
        type="line",
        xref="paper",
        x0=0,
        x1=1,
        yref="y",
        y0=0,
        y1=0,
        line=dict(color=THEME_TEXT_MUTED, width=2),
        layer="above",
    )

    fig.update_layout(
        title=None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=MEDIA_SPLIT_MARGIN_LEFT, r=MEDIA_SPLIT_MARGIN_RIGHT, t=margin_t, b=margin_b),
        hovermode="x unified",
        legend=dict(orientation="v", y=1, x=1.02, xanchor="left", yanchor="top", title=None, font=dict(size=11)),
        xaxis=dict(
            title=None,
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            showgrid=True,
            gridcolor=THEME_GRID,
        ),
        yaxis=dict(
            title=None,
            tickvals=tickvals,
            ticktext=ticktext,
            range=[-some_edge, trad_edge],
            showgrid=True,
            gridcolor=THEME_GRID,
            zeroline=False,
        ),
        hoverlabel=theme_hoverlabel(),
    )
    return fig, height_px


TIMELINE_BASE_HEIGHT_PX = 380
_NARRATIVE_ROW_HEIGHT_PX = 130


def _timeline_with_narratives_figure(
    timeline_data: dict[str, Any],
    source_filter: list[str] | str | None,
    id_field: str = "publisher_uid",
) -> tuple[go.Figure, int]:
    """Returns (figure, height_px). Sentiment timeline on top plus one sub-chart per
    associated narrative below, all sharing the main chart's x-limits.

    Expects ``timeline_data`` to additionally carry ``narrative_labels`` and
    ``narrative_trad_timeline`` / ``narrative_some_timeline`` records keyed by
    ``narrative_label`` (same shape as the main timeline records).
    """
    labels = [str(label) for label in (timeline_data.get("narrative_labels") or [])]
    main_fig = timeline_figure(timeline_data, source_filter, id_field)
    if not labels:
        return main_fig, TIMELINE_BASE_HEIGHT_PX

    available_sources = timeline_available_sources(timeline_data)
    selected_sources = normalize_sources(source_filter, available_sources)
    trad_metric = str(timeline_data.get("trad_metric", "publications"))
    some_metric = str(timeline_data.get("some_metric", "posts"))
    use_secondary = len(selected_sources) > 1 and not _timeline_uses_shared_count_scale(trad_metric, some_metric)

    n = len(labels)
    gap_before_first_subplot_px = 40
    gap_between_subplots_px = 15
    title_offset_px = 8
    row_heights_px = [TIMELINE_BASE_HEIGHT_PX] + [_NARRATIVE_ROW_HEIGHT_PX] * n
    gaps_px = [gap_before_first_subplot_px] + [gap_between_subplots_px] * (n - 1)
    total_plot_px = sum(row_heights_px) + sum(gaps_px)
    total_px = total_plot_px + 60
    titles = [""] + [(t[:60] + "…" if len(t) > 61 else t) for t in labels]
    fig = make_subplots(
        rows=n + 1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=min(0.03, gap_between_subplots_px / total_plot_px),
        row_heights=[h / total_plot_px for h in row_heights_px],
        subplot_titles=titles,
        specs=[[{"secondary_y": True}]] * (n + 1),
    )

    row_domains: list[tuple[float, float]] = []
    cursor = 1.0
    for row_index, height_px in enumerate(row_heights_px):
        height_frac = height_px / total_plot_px
        top = cursor
        bottom = top - height_frac
        row_domains.append((bottom, top))
        if row_index < len(gaps_px):
            cursor = bottom - gaps_px[row_index] / total_plot_px
        else:
            cursor = bottom
    for row_index, domain in enumerate(row_domains):
        clamped = [max(0.0, min(1.0, value)) for value in domain]
        fig.update_yaxes(domain=clamped, row=row_index + 1, col=1, secondary_y=False)

    title_offset_frac = title_offset_px / total_plot_px
    for annotation, domain in zip(fig.layout.annotations, row_domains[1:]):
        annotation.update(y=domain[1] - title_offset_frac)

    for trace in main_fig.data:
        fig.add_trace(trace, row=1, col=1, secondary_y=getattr(trace, "yaxis", "y") == "y2")

    source_configs = {
        "Trad": {
            "records": timeline_data.get("narrative_trad_timeline", []),
            "metric": trad_metric,
            "metric_labels": {"publications": "Publications", "reach": "Reach"},
            "secondary": False,
            "dash": "solid",
            "marker": "circle",
        },
        "SoMe": {
            "records": timeline_data.get("narrative_some_timeline", []),
            "metric": some_metric,
            "metric_labels": {"posts": "Posts", "engagement": "Engagement"},
            "secondary": use_secondary,
            "dash": "dot",
            "marker": "diamond",
        },
    }
    shared_week_index = _timeline_week_index(timeline_data, id_field)
    combined_mode = len(selected_sources) > 1
    primary_max = 0.0
    secondary_max = 0.0

    for row_offset, label in enumerate(labels):
        row = row_offset + 2
        for source_label in selected_sources:
            config = source_configs.get(source_label)
            if not config:
                continue
            metric = config["metric"]
            metric_label = config["metric_labels"].get(metric, metric.title())
            source_df = _timeline_series_frame(
                config["records"], label, metric, shared_week_index, "narrative_label"
            )
            if source_df.empty:
                continue
            for sentiment in SENTIMENT_ORDER:
                sub = source_df[source_df["sentiment"] == sentiment]
                if sub.empty:
                    continue
                trace_name = f"{source_label} {sentiment}" if combined_mode else sentiment
                series_max = float(sub["metric_value"].max() or 0)
                if config["secondary"]:
                    secondary_max = max(secondary_max, series_max)
                else:
                    primary_max = max(primary_max, series_max)
                fig.add_trace(
                    go.Scatter(
                        x=sub["week_start"],
                        y=sub["metric_value"],
                        name=trace_name,
                        mode="lines+markers",
                        line=dict(
                            width=1.5,
                            color=SENTIMENT_COLORS.get(sentiment),
                            shape="spline",
                            smoothing=0.45,
                            dash=config["dash"],
                        ),
                        marker=dict(size=4, color=SENTIMENT_COLORS.get(sentiment), symbol=config["marker"]),
                        fill="tozeroy",
                        fillcolor=hex_to_rgba(SENTIMENT_COLORS.get(sentiment), 0.08),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{trace_name}</b><br>"
                            "Week: %{x|%d %b %Y}<br>"
                            f"{metric_label}: %{{y:,.0f}}<extra></extra>"
                        ),
                    ),
                    row=row,
                    col=1,
                    secondary_y=config["secondary"],
                )

    main_layout = main_fig.layout
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=60, r=60 if use_secondary else 26, t=18, b=46),
        hovermode="x unified",
        legend=main_layout.legend,
        hoverlabel=main_layout.hoverlabel,
    )
    x_range = _timeline_xaxis_range(timeline_data, id_field)
    for row in range(1, n + 2):
        fig.update_xaxes(
            tickformat="%d %b",
            dtick=7 * 24 * 60 * 60 * 1000,
            range=x_range,
            showgrid=True,
            gridcolor=THEME_GRID,
            row=row,
            col=1,
        )
    fig.update_yaxes(
        title=main_layout.yaxis.title,
        tickformat=",",
        rangemode="tozero",
        showgrid=True,
        gridcolor=THEME_GRID,
        row=1,
        col=1,
        secondary_y=False,
    )
    if use_secondary and getattr(main_layout, "yaxis2", None) is not None:
        fig.update_yaxes(
            title=main_layout.yaxis2.title,
            tickformat=",",
            rangemode="tozero",
            showgrid=False,
            zeroline=False,
            row=1,
            col=1,
            secondary_y=True,
        )
    narrative_primary_title = _timeline_axis_title(
        selected_sources[0] if selected_sources else None, trad_metric, some_metric
    )
    narrative_secondary_title = _timeline_axis_title("SoMe", trad_metric, some_metric)
    for row in range(2, n + 2):
        fig.update_yaxes(
            title=dict(text=narrative_primary_title, font=dict(size=10)),
            range=[0, (primary_max or 1) * 1.08],
            tickformat=",",
            showgrid=True,
            gridcolor=THEME_GRID,
            row=row,
            col=1,
            secondary_y=False,
        )
        if use_secondary:
            fig.update_yaxes(
                title=dict(text=narrative_secondary_title, font=dict(size=10)),
                range=[0, (secondary_max or 1) * 1.08],
                tickformat=",",
                showgrid=False,
                zeroline=False,
                row=row,
                col=1,
                secondary_y=True,
            )
    fig.update_annotations(font=dict(color=THEME_TEXT_MUTED, size=10))
    return fig, total_px
