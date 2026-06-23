"""Archive page components — UMAP cluster scatter chart."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from scipy.stats import gaussian_kde

from dashboards.amazon_2026.charts_shared import (
    NARRATIVE_LINE_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_SURFACE,
    THEME_TEXT,
    THEME_TEXT_MUTED,
    _add_empty_figure_annotation,
    _hex_to_rgba,
    _json_safe,
    _theme_hoverlabel,
    na_panel,
)
from dashboards.amazon_2026.dev_ids import ref_label

# NARRATIVE_LINE_COLORS plus extra hues — archive has more clusters to color
# distinctly than the narratives/donut palettes need.
ARCHIVE_NARRATIVE_COLORS = NARRATIVE_LINE_COLORS + [
    "#cf844d", "#493aaf", "#47b931", "#c65689",
    "#3196b9", "#afab3a", "#a44dcf", "#3aaf66",
    "#b93c31", "#566dc6", "#75b931", "#af3a97",
    "#4dcfc5", "#af843a", "#5e31b9", "#56c65b",
    "#b93153", "#3a7aaf",
]
ARCHIVE_GRAYSCALE = "#9aa4b2"
ARCHIVE_NOISE_COLOR = "#5b6472"
REFERENCE_MARKER_COLOR = "#ffffff"
REFERENCE_CIRCLE_COLOR = "#c8d0da"
TIME_COLORSCALE = [
    [0.0, "#2f7dd1"],
    [0.25, "#35a66b"],
    [0.5, "#d9c23a"],
    [0.75, "#e07040"],
    [1.0, "#c84e5a"],
]


def _records_from_frame(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    df = data_frame.copy() if data_frame is not None else pd.DataFrame()
    for col in ["umap_x", "umap_y", "narrative_label", "source"]:
        if col not in df.columns:
            df[col] = "" if col in {"narrative_label", "source"} else 0.0
    df["umap_x"] = pd.to_numeric(df["umap_x"], errors="coerce")
    df["umap_y"] = pd.to_numeric(df["umap_y"], errors="coerce")
    df = df.dropna(subset=["umap_x", "umap_y"])
    df["narrative_label"] = df["narrative_label"].fillna("").astype(str)
    return [_json_safe(row) for row in df.to_dict("records")]


def _build_color_map(df: pd.DataFrame) -> dict[str, str]:
    counted = (
        df[df["narrative_label"].str.lower() != "noise"]
        .groupby("narrative_label")
        .size()
        .sort_values(ascending=False)
        .index.tolist()
    )
    return {label: ARCHIVE_NARRATIVE_COLORS[i % len(ARCHIVE_NARRATIVE_COLORS)] for i, label in enumerate(counted)}


KDE_GRID_SIZE = 60
KDE_MIN_POINTS = 8


def _kde_grid(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    x_min, x_max = df["umap_x"].min(), df["umap_x"].max()
    y_min, y_max = df["umap_y"].min(), df["umap_y"].max()
    pad_x = (x_max - x_min) * 0.08 or 1.0
    pad_y = (y_max - y_min) * 0.08 or 1.0
    grid_x = np.linspace(x_min - pad_x, x_max + pad_x, KDE_GRID_SIZE)
    grid_y = np.linspace(y_min - pad_y, y_max + pad_y, KDE_GRID_SIZE)
    return grid_x, grid_y


def _kde_density(sub: pd.DataFrame, grid_x: np.ndarray, grid_y: np.ndarray) -> np.ndarray | None:
    if len(sub) < KDE_MIN_POINTS:
        return None
    points = np.vstack([sub["umap_x"], sub["umap_y"]])
    try:
        kde = gaussian_kde(points)
    except (np.linalg.LinAlgError, ValueError):
        return None
    xx, yy = np.meshgrid(grid_x, grid_y)
    density = kde(np.vstack([xx.ravel(), yy.ravel()])).reshape(xx.shape)
    if density.max() <= 0:
        return None
    return density


def _point_customdata(sub: pd.DataFrame) -> np.ndarray | pd.Series | None:
    """Build customdata for a scatter trace, including ``_id`` (for lasso/box
    selection round-tripping) alongside the ``source`` shown on hover."""
    if "_id" in sub.columns:
        if "source" in sub.columns:
            return sub[["_id", "source"]].to_numpy()
        return sub[["_id"]].to_numpy()
    return sub["source"] if "source" in sub.columns else None


def _hover_field(sub: pd.DataFrame) -> str:
    return "%{customdata[1]}" if "_id" in sub.columns and "source" in sub.columns else "%{customdata}"


def umap_distance_bounds(records: list[dict[str, Any]]) -> float:
    """Return bounding-box diagonal of the UMAP cloud — used to scale the similarity slider to data-space radius."""
    xs = [float(r["umap_x"]) for r in records if r.get("umap_x") is not None]
    ys = [float(r["umap_y"]) for r in records if r.get("umap_y") is not None]
    if not xs or not ys:
        return 1.0
    return max(((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5, 0.01)


def _add_reference_overlay(
    fig: go.Figure,
    reference_point: tuple[float, float] | None,
    reference_radius: float | None,
) -> None:
    if not reference_point:
        return
    x0, y0 = reference_point
    if reference_radius:
        fig.add_shape(
            type="circle",
            xref="x", yref="y",
            x0=x0 - reference_radius,
            x1=x0 + reference_radius,
            y0=y0 - reference_radius,
            y1=y0 + reference_radius,
            line=dict(color=REFERENCE_CIRCLE_COLOR, width=1.5, dash="dash"),
            fillcolor="rgba(0,0,0,0)",
            layer="above",
        )
    fig.add_trace(
        go.Scattergl(
            x=[x0],
            y=[y0],
            mode="markers",
            name="Reference",
            marker=dict(
                symbol="cross",
                size=14,
                color=REFERENCE_MARKER_COLOR,
                line=dict(color=REFERENCE_MARKER_COLOR, width=2.5),
                opacity=1.0,
            ),
            hovertemplate="Reference<extra></extra>",
            showlegend=True,
        )
    )


def _archive_figure(
    records: list[dict[str, Any]],
    color_map: dict[str, str],
    color_on: bool,
    show_kde: bool,
    time_on: bool = False,
    date_bounds: dict[str, Any] | None = None,
    reference_point: tuple[float, float] | None = None,
    reference_radius: float | None = None,
) -> go.Figure:
    df = pd.DataFrame(records)
    fig = go.Figure()

    if df.empty:
        _add_empty_figure_annotation(fig, "No UMAP data available")
        _apply_archive_layout(fig)
        return fig

    if time_on and "_date_index" in df.columns:
        date_bounds = date_bounds or {}
        min_date = date_bounds.get("min_date") or ""
        max_date = date_bounds.get("max_date") or ""
        min_index = float(date_bounds.get("min_index", 0))
        max_index = float(date_bounds.get("max_index", df["_date_index"].max())) or 1.0
        mid_label = ""
        try:
            mid = pd.to_datetime(min_date) + (pd.to_datetime(max_date) - pd.to_datetime(min_date)) / 2
            mid_label = mid.strftime("%d %b %Y")
        except (ValueError, TypeError):
            pass
        fig.add_trace(
            go.Scattergl(
                x=df["umap_x"],
                y=df["umap_y"],
                mode="markers",
                name="By date",
                marker=dict(
                    size=5,
                    opacity=0.65,
                    line=dict(width=0),
                    color=df["_date_index"],
                    colorscale=TIME_COLORSCALE,
                    cmin=min_index,
                    cmax=max_index,
                    showscale=True,
                    colorbar=dict(
                        title=None,
                        thickness=12,
                        len=0.6,
                        x=1.0,
                        tickmode="array",
                        tickvals=[min_index, (min_index + max_index) / 2, max_index],
                        ticktext=[min_date, mid_label, max_date],
                        outlinewidth=0,
                        bgcolor=THEME_SURFACE,
                        tickfont=dict(color=THEME_TEXT, size=10),
                    ),
                ),
                customdata=_point_customdata(df),
                hovertemplate=f"{_hover_field(df)}<extra></extra>",
                showlegend=False,
            )
        )
        _add_reference_overlay(fig, reference_point, reference_radius)
        _apply_archive_layout(fig)
        return fig

    if color_on:
        groups: list[tuple[str, str]] = list(color_map.items())
        labeled = set(color_map.keys())
        other = df[~df["narrative_label"].isin(labeled)]
        if not other.empty:
            groups.append(("Noise", ARCHIVE_NOISE_COLOR))
    else:
        groups = [("All publications & posts", ARCHIVE_GRAYSCALE)]

    if show_kde:
        grid_x, grid_y = _kde_grid(df)
        for label, color in color_map.items():
            sub = df[df["narrative_label"] == label]
            density = _kde_density(sub, grid_x, grid_y)
            if density is None:
                continue
            z_max = float(density.max())
            z_start = z_max * 0.15
            fig.add_trace(
                go.Contour(
                    x=grid_x,
                    y=grid_y,
                    z=density,
                    name=label,
                    showscale=False,
                    showlegend=False,
                    contours=dict(
                        coloring="fill",
                        showlines=False,
                        start=z_start,
                        end=z_max,
                        size=(z_max - z_start) / 4,
                    ),
                    colorscale=[[0, _hex_to_rgba(color, 0)], [1, _hex_to_rgba(color, 0.45)]],
                    line=dict(width=0),
                    hoverinfo="skip",
                )
            )

    for label, color in groups:
        if color_on and label != "Noise":
            sub = df[df["narrative_label"] == label]
        elif color_on:
            sub = df[~df["narrative_label"].isin(color_map.keys())]
        else:
            sub = df
        if sub.empty:
            continue
        fig.add_trace(
            go.Scattergl(
                x=sub["umap_x"],
                y=sub["umap_y"],
                mode="markers",
                name=label,
                marker=dict(size=5, color=color, opacity=0.55, line=dict(width=0)),
                hovertemplate=f"<b>{label}</b><extra></extra>" if not color_on else (
                    f"<b>{label}</b><br>{_hover_field(sub)}<extra></extra>"
                ),
                customdata=_point_customdata(sub),
                showlegend=color_on,
            )
        )

    _add_reference_overlay(fig, reference_point, reference_radius)
    _apply_archive_layout(fig)
    return fig


def _apply_archive_layout(fig: go.Figure) -> None:
    fig.update_layout(
        uirevision="amazon-2026-umap",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=THEME_TEXT),
        margin=dict(l=20, r=20, t=10, b=20),
        legend=dict(
            orientation="v",
            x=0.01,
            y=0.99,
            xanchor="left",
            yanchor="top",
            bgcolor=THEME_SURFACE,
            bordercolor=THEME_BORDER,
            borderwidth=1,
            font=dict(size=11),
            title=None,
        ),
        xaxis=dict(title=None, showgrid=True, gridcolor=THEME_GRID, zeroline=False, showticklabels=False),
        yaxis=dict(title=None, showgrid=True, gridcolor=THEME_GRID, zeroline=False, showticklabels=False),
        hoverlabel=_theme_hoverlabel(size=12),
    )


def build_archive_scatter_section(data_frame: pd.DataFrame) -> html.Div:
    records = _records_from_frame(data_frame)
    df = pd.DataFrame(records)
    color_map = _build_color_map(df) if not df.empty else {}
    initial_fig = _archive_figure(records, color_map, color_on=True, show_kde=False)

    return na_panel(
        ref_label("Narrative Clusters (UMAP)", "P5S1G1"),
        [
            html.Div(
                className="amazon-publishers-chart-controls",
                children=[
                    dcc.Checklist(
                        id="amazon-2026-archive-color-toggle",
                        options=[{"label": "Color by narrative", "value": "color"}],
                        value=["color"],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                    dcc.Checklist(
                        id="amazon-2026-archive-kde-toggle",
                        options=[{"label": "KDE", "value": "kde"}],
                        value=[],
                        inline=True,
                        className="amazon-publishers-radio",
                    ),
                ],
            ),
            dcc.Store(
                id="amazon-2026-archive-scatter-data",
                data={"records": records, "color_map": color_map},
            ),
            dcc.Graph(
                id="amazon-2026-archive-scatter-graph",
                figure=initial_fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "responsive": True,
                    "toImageButtonOptions": {"format": "svg", "filename": "amazon_2026_archive_umap"},
                },
                style={"height": "640px"},
            ),
        ],
    )


@callback(
    Output("amazon-2026-archive-scatter-graph", "figure"),
    Input("amazon-2026-archive-color-toggle", "value"),
    Input("amazon-2026-archive-kde-toggle", "value"),
    State("amazon-2026-archive-scatter-data", "data"),
)
def _update_archive_scatter(color_value: list[str], kde_value: list[str], store_data: dict | None):
    data = store_data or {}
    records = data.get("records", [])
    color_map = data.get("color_map", {})
    color_on = "color" in (color_value or [])
    show_kde = "kde" in (kde_value or [])
    return _archive_figure(records, color_map, color_on, show_kde)
