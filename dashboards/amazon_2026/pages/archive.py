"""Archive page."""
from __future__ import annotations

import pandas as pd
import vizro.models as vm

from dashboards.amazon_2026.charts_archive import build_archive_scatter_section
from dashboards.amazon_2026.data_common import ARCHIVE_SCATTER_KEY
from dashboards.amazon_2026.pages._shared import build_standard_page
from dashboards.amazon_2026.ui_components import capture


def build_archive_page(base_path: str) -> vm.Page:
    return build_standard_page(
        base_path=base_path,
        slug="archive",
        display_name="Clusters",
        ref_code="P5",
        description="Clustered charts for historical comparison.",
        layout=None,
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
