"""Archive page."""
from __future__ import annotations

import pandas as pd
import vizro.models as vm
from vizro.models.types import capture

from dashboards.amazon_2026.charts_archive import build_archive_scatter_section
from dashboards.amazon_2026.data_common import ARCHIVE_SCATTER_KEY
from dashboards.amazon_2026.dev_ids import ref_label


def build_archive_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-archive",
        title=ref_label("Clusters", "P5"),
        path=f"{base_path}/archive",
        description="Clustered charts for historical comparison.",
        components=[
            vm.Figure(
                id="amazon-2026-archive-scatter-section",
                figure=archive_scatter_panel(data_frame=ARCHIVE_SCATTER_KEY),
            ),
        ],
    )


@capture("figure")
def archive_scatter_panel(data_frame: pd.DataFrame):
    return build_archive_scatter_section(data_frame)
