"""
Dashboard plugin: Reach & Engagement Timeline.

Refactored from the original ``pages/timeline.py``. Part of the Amazon media
monitoring product; shares its synthetic dataset with the breakdown dashboard
via the top-level ``data`` and ``charts`` modules.
"""

from __future__ import annotations

import vizro.models as vm

from charts import campaign_gantt, reach_engagement_timeline
from dashboards._base import (
    BuildContext,
    DashboardManifest,
    DataSourceHealth,
    export_button,
    freshness_note,
)
from data import df_campaigns, df_weekly

MANIFEST = DashboardManifest(
    slug="timeline",
    title="Reach & Engagement Timeline",
    description="Dual-axis weekly reach/engagement by sentiment, with a campaign Gantt.",
    icon="timeline",
    category="Media Intelligence",
    data_requirements=["synthetic:media_weekly"],
)


def data_health() -> list[DataSourceHealth]:
    latest = df_weekly["week_start"].max()
    return [
        DataSourceHealth(
            name="synthetic:media_weekly",
            status="ok",
            detail="Synthetic dataset (always available).",
            rows=len(df_weekly),
            as_of=str(getattr(latest, "date", lambda: latest)()),
        )
    ]


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    all_campaigns = df_campaigns["campaign_label"].tolist()
    latest = df_weekly["week_start"].max()
    freshness = freshness_note(latest)

    reach_page = vm.Page(
        id="timeline",
        title="Reach & Engagement",
        path=MANIFEST.base_path,
        description=(
            "Weekly reach (solid lines) and engagement (dotted) split by sentiment. "
            f"Use the filters to focus on a narrative, sentiment or date range. {freshness}"
        ),
        components=[
            vm.Graph(
                id="reach_eng_chart",
                title="Weekly Reach (solid) & Engagement (dotted) by Sentiment",
                figure=reach_engagement_timeline(data_frame=df_weekly),
            ),
            export_button(),
        ],
        controls=[
            vm.Filter(
                column="narrative_label",
                targets=["reach_eng_chart"],
                selector=vm.Dropdown(title="Narrative", multi=False, value="All narratives"),
            ),
            vm.Filter(
                column="sentiment",
                targets=["reach_eng_chart"],
                selector=vm.Checklist(title="Sentiment", value=["positive", "neutral", "negative"]),
            ),
            vm.Filter(
                column="week_start",
                targets=["reach_eng_chart"],
                selector=vm.DatePicker(title="Date range", range=True),
            ),
            vm.Parameter(
                targets=["reach_eng_chart.y_scale"],
                selector=vm.RadioItems(options=["linear", "log"], value="linear", title="Axis scale"),
            ),
        ],
    )

    campaigns_page = vm.Page(
        id="timeline-campaigns",
        title="Campaigns",
        path=f"{MANIFEST.base_path}/campaigns",
        description=(
            "Campaign schedule as a Gantt timeline; bar colour encodes total reach "
            f"(blue = low, yellow = high). {freshness}"
        ),
        components=[
            vm.Graph(
                id="campaign_chart",
                title="Campaign Timeline  ·  bar colour = total reach (blue-low → yellow-high)",
                figure=campaign_gantt(data_frame=df_campaigns),
            ),
            export_button(),
        ],
        controls=[
            vm.Filter(
                column="campaign_label",
                targets=["campaign_chart"],
                selector=vm.Checklist(title="Show campaigns", value=all_campaigns),
            ),
        ],
    )

    return [reach_page, campaigns_page]
