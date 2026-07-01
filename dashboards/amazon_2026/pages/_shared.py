"""Helpers shared across all Amazon 2026 page builders."""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import vizro.models as vm
from dash import html

from dashboards.amazon_2026.dev_ids import ref_label
from dashboards.amazon_2026.ui_components import capture

_DEFAULT_LAYOUT = object()  # sentinel: build a fresh vm.Flex per call, never share one instance


def build_standard_page(
    *,
    base_path: str,
    slug: str,
    display_name: str,
    ref_code: str,
    description: str,
    components: list,
    path: str | None = None,
    layout: Any = _DEFAULT_LAYOUT,
    controls: list | None = None,
) -> vm.Page:
    """Build the `vm.Page(...)` skeleton shared by every Amazon 2026 page.

    `id`/`title`/`path` are derived from `slug` + `display_name` + `ref_code`; only the
    page-specific `components`/`controls` (and the rare `path`/`layout` override) vary.
    """
    kwargs: dict[str, Any] = {
        "id": f"amazon-2026-{slug}",
        "title": ref_label(display_name, ref_code),
        "path": path or f"{base_path}/{slug}",
        "description": description,
        "components": components,
    }
    if layout is _DEFAULT_LAYOUT:
        kwargs["layout"] = vm.Flex(direction="column", gap="20px")
    elif layout is not None:
        kwargs["layout"] = layout
    if controls is not None:
        kwargs["controls"] = controls
    return vm.Page(**kwargs)


def detail_content_scope(content: Any) -> html.Div:
    """Wrap detail content in the ``.amazon-*-details`` scope classes the detail-grid CSS
    is keyed on.

    The detail content used to live inside the ``.amazon-publishers-section`` shell (which
    carried these classes). It now lives in its own ``vm.Figure`` so that ``_on_page_load``
    and the populate callback write the *same* prop (no nested-store conflict / collapse).
    Re-applying the scope hooks here keeps the grid/column CSS working. These classes only
    scope selectors — they add no box styling (that is ``.amazon-publishers-section``).
    """
    return html.Div(className="amazon-publishers-details amazon-narrative-details", children=content)


@capture("figure")
def basic_metric_sink(data_frame: pd.DataFrame, basic_metric: str = "publications"):
    """Invisible figure whose sole job is to receive the basic-metric Parameter value.

    Every detail page (Campaigns/Narratives/Publishers/Topic Areas) wires this in so
    `basic_metric` reaches their other callbacks via the rendered div's children.
    """
    return html.Div(basic_metric, className="amazon-publishers-control-sink")


_METRIC_OPTIONS = [
    {"label": "Publications and Posts Count", "value": "publications"},
    {"label": "Reach and Engagement Sum", "value": "reach"},
]


def metric_filter(targets: list[str]) -> vm.Filter:
    """Radio-button filter that switches all charts between count and reach/engagement."""
    return vm.Filter(
        column="base_metric",
        targets=targets,
        selector=vm.RadioItems(
            title="Base Metric:",
            options=_METRIC_OPTIONS,
            value="publications",
        ),
    )


def metric_parameter(targets: list[str], *, selector_id: str | None = None) -> vm.Parameter:
    """Radio-button parameter for custom figures that handle basic metric values themselves."""
    return vm.Parameter(
        targets=targets,
        selector=vm.RadioItems(
            id=selector_id,
            title="Base Metric:",
            options=_METRIC_OPTIONS,
            value="publications",
        ),
    )


def build_detail_timeline_response(
    source: list[str] | None,
    basic_metric: str | None,
    store_data: dict[str, Any] | None,
    *,
    ref_code: str,
    make_ref_label: Callable[[str, str], Any],
    combined_builder: Callable[..., Any],
    single_builder: Callable[..., Any],
    dtick: int | None = None,
) -> tuple[Any, Any]:
    """Build the shared Trad/SoMe detail timeline figure and title.

    Narratives, Campaigns, and Topic Areas all expose the same interaction:
    render Trad, SoMe, or combined weekly detail charts from the same stored
    payload, with only the reference code and optional dtick varying by page.
    """
    data = store_data or {}
    x_range = data.get("x_range") or None
    sources = source or []
    has_trad = "Trad" in sources
    has_some = "SoMe" in sources

    shared_kwargs: dict[str, Any] = {"x_range": x_range, "load_failed": bool(data.get("load_failed"))}
    if dtick is not None:
        shared_kwargs["dtick"] = dtick

    if has_trad and has_some:
        trad_df = pd.DataFrame(data.get("trad") or [])
        some_df = pd.DataFrame(data.get("some") or [])
        if basic_metric == "reach":
            fig = combined_builder(
                trad_df,
                some_df,
                trad_metric_col="weekly_reach",
                trad_label="Trad Reach",
                trad_cum_label="Trad Cumulative",
                some_metric_col="weekly_engagement",
                some_label="SoMe Engagement",
                some_cum_label="SoMe Cumulative",
                y_title="Reach / Engagement",
                cum_title="Cumulative Reach / Engagement",
                **shared_kwargs,
            )
            return fig, make_ref_label("Reach and Engagement", ref_code)
        fig = combined_builder(
            trad_df,
            some_df,
            trad_metric_col="weekly_publications",
            trad_label="Trad Publications",
            trad_cum_label="Trad Cumulative",
            some_metric_col="weekly_posts",
            some_label="SoMe Posts",
            some_cum_label="SoMe Cumulative",
            y_title="Publications / Posts",
            cum_title="Cumulative Publications / Posts",
            **shared_kwargs,
        )
        return fig, make_ref_label("Publications and Posts", ref_code)

    if has_some:
        df = pd.DataFrame(data.get("some") or [])
        if basic_metric == "reach":
            fig = single_builder(
                df,
                "weekly_engagement",
                "SoMe Engagement",
                "SoMe Cumulative",
                source="SoMe",
                **shared_kwargs,
            )
            return fig, make_ref_label("SoMe Engagement", ref_code)
        fig = single_builder(
            df,
            "weekly_posts",
            "SoMe Posts",
            "SoMe Cumulative",
            source="SoMe",
            **shared_kwargs,
        )
        return fig, make_ref_label("SoMe Posts", ref_code)

    df = pd.DataFrame(data.get("trad") or [])
    if basic_metric == "reach":
        fig = single_builder(
            df,
            "weekly_reach",
            "Trad Reach",
            "Trad Cumulative",
            source="Trad",
            **shared_kwargs,
        )
        return fig, make_ref_label("Trad Reach", ref_code)
    fig = single_builder(
        df,
        "weekly_publications",
        "Trad Publications",
        "Trad Cumulative",
        source="Trad",
        **shared_kwargs,
    )
    return fig, make_ref_label("Trad Publications", ref_code)


def build_overview_table_response(
    *,
    records: list[dict[str, Any]] | None,
    source_filter: str | None,
    filter_records: Callable[[list[dict[str, Any]], str, Any, Any], list[dict[str, Any]]],
    table_records: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    table_columns: Callable[[str], list[dict[str, Any]]],
    header_styles: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    data_styles: Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[dict[str, Any]]],
    tml_filter: list[str] | str | None = None,
    media_filter: list[str] | str | None = None,
    first_column_label: str | None = None,
    extra_output: Callable[[list[dict[str, Any]], str], Any] | None = None,
) -> tuple[Any, ...]:
    """Build the standard overview-table callback payload used across pages."""
    normalized_source = source_filter or "All"
    filtered = filter_records(records or [], normalized_source, tml_filter, media_filter)
    table_data = table_records(filtered)
    columns = table_columns(normalized_source)
    if first_column_label:
        columns[0] = {"name": ["", first_column_label], "id": "display_name"}

    response: list[Any] = [
        table_data,
        columns,
        header_styles(columns),
        data_styles(table_data, columns),
    ]
    if extra_output is not None:
        response.append(extra_output(filtered, normalized_source))
    return tuple(response)


def select_active_table_value(
    active_cell: dict[str, Any] | None,
    viewport_rows: list[dict[str, Any]] | None,
    table_rows: list[dict[str, Any]] | None,
    *,
    expected_column: str,
    fallback_value: Any,
    row_id_first: bool = False,
    value_keys: list[str] | None = None,
) -> Any:
    """Resolve a selector value from a clicked Dash DataTable cell."""
    if not active_cell or active_cell.get("column_id") != expected_column:
        return fallback_value
    if row_id_first and active_cell.get("row_id"):
        return active_cell["row_id"]

    row_index = active_cell.get("row")
    if row_index is None:
        return fallback_value

    rows = viewport_rows or table_rows or []
    if row_index >= len(rows):
        return fallback_value

    selected_row = rows[row_index]
    for key in value_keys or []:
        value = selected_row.get(key)
        if value:
            return value
    return fallback_value
