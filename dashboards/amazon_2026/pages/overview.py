"""Overview page for the Amazon 2026 dashboard."""
from __future__ import annotations

import vizro.models as vm

from dashboards.amazon_2026.charts import (
    overview_kpi_panel,
    overview_top_items_panel,
    pubs_posts_reach_by_source_panel,
    some_platform_donut_panel,
    trad_media_type_period_donut_panel,
    trad_source_sentiment_monthly_split_panel,
    trad_tml_donut_panel,
)
from dashboards.amazon_2026.data_common import (
    MEDIA_TYPE_PERIOD_KEY,
    OVERVIEW_KEY,
    OVERVIEW_KPI_KEY,
    SENTIMENT_SOURCE_MONTHLY_KEY,
    SOME_PLATFORM_KEY,
    SOURCE_SENTIMENT_MONTHLY_KEY,
    TOP_ARTICLES_KEY,
)
from dashboards.amazon_2026.dev_ids import ref_label, ref_only
from dashboards.amazon_2026.pages._shared import metric_filter


def build_overview_page(base_path: str) -> vm.Page:
    return vm.Page(
        id="amazon-2026-overview",
        title=ref_label("Overview", "P1"),
        path=base_path,
        description="Publications split in traditional media between TML and non-TML.",
        components=[
            vm.Container(
                title=ref_only("P1S1"),
                layout=vm.Grid(grid=[[0]]),
                components=[
                    vm.Figure(
                        id="amazon-2026-overview-kpis",
                        figure=overview_kpi_panel(data_frame=OVERVIEW_KPI_KEY),
                    ),
                ],
            ),
            vm.Container(
                title=ref_only("P1S2"),
                layout=vm.Grid(
                    grid=[[0, 1, 2]],
                    col_gap="16px",
                    row_min_height="380px",
                ),
                components=[
                    vm.Figure(
                        id="amazon-2026-overview-tml",
                        figure=trad_tml_donut_panel(data_frame=OVERVIEW_KEY),
                    ),
                    vm.Figure(
                        id="amazon-2026-media-type-period",
                        figure=trad_media_type_period_donut_panel(data_frame=MEDIA_TYPE_PERIOD_KEY),
                    ),
                    vm.Figure(
                        id="amazon-2026-some-platform",
                        figure=some_platform_donut_panel(data_frame=SOME_PLATFORM_KEY),
                    ),
                ],
            ),
            vm.Container(
                title=ref_only("P1S3"),
                layout=vm.Grid(grid=[[0]], row_min_height="376px"),
                components=[
                    vm.Figure(
                        id="amazon-2026-pubs-posts-reach",
                        figure=pubs_posts_reach_by_source_panel(data_frame=SENTIMENT_SOURCE_MONTHLY_KEY),
                    ),
                ],
            ),
            vm.Container(
                title=ref_only("P1S4"),
                layout=vm.Grid(grid=[[0]], row_min_height="460px"),
                components=[
                    vm.Figure(
                        id="amazon-2026-source-sentiment-monthly",
                        figure=trad_source_sentiment_monthly_split_panel(data_frame=SOURCE_SENTIMENT_MONTHLY_KEY),
                    ),
                ],
            ),
            vm.Container(
                title=ref_only("P1S5"),
                layout=vm.Grid(grid=[[0]], row_min_height="500px"),
                components=[
                    vm.Figure(
                        id="amazon-2026-top-items",
                        figure=overview_top_items_panel(data_frame=TOP_ARTICLES_KEY),
                    ),
                ],
            ),
        ],
        layout=vm.Flex(direction="column", gap="20px"),
        controls=[
            metric_filter(
                [
                    "amazon-2026-overview-tml",
                    "amazon-2026-media-type-period",
                    "amazon-2026-some-platform",
                    "amazon-2026-pubs-posts-reach",
                    "amazon-2026-source-sentiment-monthly",
                ]
            )
        ],
    )
