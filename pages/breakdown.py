"""
Page 2 — Narrative Breakdown

Layout (side-by-side)
  Left  : grouped horizontal bar  — total reach per narrative × sentiment
  Right : stacked area chart      — reach over time split by sentiment
  Below : engagement ratio scatter — reach vs engagement bubble chart

Controls
  Sentiment  : multi-select checklist
  Date range : date-picker range
"""

import vizro.models as vm

from charts import engagement_ratio_scatter, narrative_reach_bar, sentiment_stacked_area
from data import df_weekly_narratives

breakdown_page = vm.Page(
    title="Narrative Breakdown",
    layout=vm.Grid(
        grid=[
            [0, 0, 1, 1],
            [0, 0, 1, 1],
            [0, 0, 1, 1],
            [2, 2, 2, 2],
            [2, 2, 2, 2],
            [2, 2, 2, 2],
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
    ],
    controls=[
        # ── Sentiment checklist ───────────────────────────────────────────────
        vm.Filter(
            column="sentiment",
            selector=vm.Checklist(
                title="Sentiment",
                value=["positive", "neutral", "negative"],
            ),
        ),

        # ── Date range ────────────────────────────────────────────────────────
        vm.Filter(
            column="week_start",
            selector=vm.DatePicker(
                title="Date range",
                range=True,
            ),
        ),

        # ── Y-axis scale for area chart ───────────────────────────────────────
        vm.Parameter(
            targets=["sentiment_area_chart.yaxis.type"],
            selector=vm.RadioItems(
                options=["linear", "log"],
                value="linear",
                title="Area chart scale",
            ),
        ),

        # ── Bar chart orientation parameter ───────────────────────────────────
        vm.Parameter(
            targets=["narrative_bar_chart.barmode"],
            selector=vm.RadioItems(
                options=["group", "stack", "relative"],
                value="group",
                title="Bar mode",
            ),
        ),
    ],
)
