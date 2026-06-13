"""Helpers shared across all Amazon 2026 page builders."""
from __future__ import annotations

import vizro.models as vm

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
