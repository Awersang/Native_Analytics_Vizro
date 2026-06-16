"""Pages sub-package for the Amazon 2026 dashboard.

Each module owns exactly one page builder function.  Adding a new page
means adding a new module here and registering it in ``build_all_pages``.
"""
from __future__ import annotations

import vizro.models as vm

from dashboards._base import BuildContext
from dashboards.amazon_2026.dev_ids import set_dev_mode
from dashboards.amazon_2026.pages.archive import build_archive_page
from dashboards.amazon_2026.pages.campaigns import build_campaigns_page
from dashboards.amazon_2026.pages.discover import build_discover_page
from dashboards.amazon_2026.pages.narratives import build_narratives_page
from dashboards.amazon_2026.pages.overview import build_overview_page
from dashboards.amazon_2026.pages.publishers import build_publishers_page
from dashboards.amazon_2026.pages.topic_areas import build_topic_areas_page

__all__ = [
    "build_all_pages",
    "build_overview_page",
    "build_archive_page",
    "build_narratives_page",
    "build_publishers_page",
    "build_topic_areas_page",
    "build_campaigns_page",
    "build_discover_page",
]


def build_all_pages(
    _ctx: BuildContext,
    base_path: str,
) -> list[vm.Page]:
    set_dev_mode(True)
    return [
        build_overview_page(base_path),
        build_topic_areas_page(base_path),
        build_narratives_page(base_path),
        build_campaigns_page(base_path),
        build_publishers_page(base_path),
        build_discover_page(base_path),
        build_archive_page(base_path),
    ]
