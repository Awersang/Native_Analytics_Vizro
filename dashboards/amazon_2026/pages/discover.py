"""Discover page."""
from __future__ import annotations

import vizro.models as vm

from dashboards.amazon_2026.dev_ids import ref_label


def build_discover_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-discover",
        title=ref_label("Discover", "P8"),
        path=f"{base_path}/discover",
        description="Explore and search across the dataset.",
        components=[
            vm.Card(text=""),
        ],
    )
