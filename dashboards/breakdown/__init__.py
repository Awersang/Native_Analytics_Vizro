"""
Dashboard plugin: Narrative Breakdown.

Refactored from the original ``pages/breakdown.py``.
"""

from __future__ import annotations

import vizro.models as vm

from charts import engagement_ratio_scatter, narrative_reach_bar, sentiment_stacked_area
from dashboards._base import (
    BuildContext,
    DashboardManifest,
    DataSourceHealth,
    export_button,
    freshness_note,
)
from data import df_weekly_narratives

MANIFEST = DashboardManifest(
    slug="breakdown",
    title="Narrative Breakdown",
    description="Reach by narrative & sentiment, stacked-area trend, and engagement-ratio scatter.",
    icon="insights",
    category="Media Intelligence",
    data_requirements=["synthetic:media_weekly"],
)


def data_health() -> list[DataSourceHealth]:
    latest = df_weekly_narratives["week_start"].max()
    return [
        DataSourceHealth(
            name="synthetic:media_weekly",
            status="ok",
            detail="Synthetic dataset (always available).",
            rows=len(df_weekly_narratives),
            as_of=str(getattr(latest, "date", lambda: latest)()),
        )
    ]


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    latest = df_weekly_narratives["week_start"].max()
    page = vm.Page(
        id="breakdown",
        title=MANIFEST.title,
        path=MANIFEST.base_path,
        description=(
            "Reach by narrative and sentiment, a stacked-area trend, and a reach-vs-engagement "
            f"scatter (bubble size = engagement-to-reach ratio). {freshness_note(latest)}"
        ),
        layout=vm.Grid(
            grid=[
                [0, 0, 1, 1],
                [0, 0, 1, 1],
                [0, 0, 1, 1],
                [2, 2, 2, 2],
                [2, 2, 2, 2],
                [2, 2, 2, 2],
                [3, -1, -1, -1],
            ],
            row_min_height="70px",
        ),
        components=[
            vm.Graph(
                id="narrative_bar_chart",
                title="Total Reach by Narrative & Sentiment",
                figure=narrative_reach_bar(data_frame=df_weekly_narratives),
            ),
            vm.Graph(
                id="sentiment_area_chart",
                title="Reach Over Time — Stacked by Sentiment",
                figure=sentiment_stacked_area(data_frame=df_weekly_narratives),
            ),
            vm.Graph(
                id="ratio_scatter_chart",
                title="Reach vs Engagement  ·  bubble size = engagement-to-reach ratio",
                figure=engagement_ratio_scatter(data_frame=df_weekly_narratives),
            ),
            export_button(),
        ],
        controls=[
            vm.Filter(
                column="sentiment",
                selector=vm.Checklist(title="Sentiment", value=["positive", "neutral", "negative"]),
            ),
            vm.Filter(
                column="week_start",
                selector=vm.DatePicker(title="Date range", range=True),
            ),
            vm.Parameter(
                targets=["sentiment_area_chart.y_scale"],
                selector=vm.RadioItems(options=["linear", "log"], value="linear", title="Area chart scale"),
            ),
            vm.Parameter(
                targets=["narrative_bar_chart.barmode"],
                selector=vm.RadioItems(options=["group", "stack", "relative"], value="group", title="Bar mode"),
            ),
        ],
    )
    return [page]
