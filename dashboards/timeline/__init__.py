"""
Dashboard plugin: Reach & Engagement Timeline.

Part of the same demo media-monitoring product as the ``breakdown``
dashboard; each keeps its own self-contained ``data.py``/``charts.py``.
"""

from __future__ import annotations

import vizro.models as vm
from vizro.managers import data_manager

from dashboards._base import (
    BuildContext,
    DashboardManifest,
    DataSourceHealth,
    export_button,
    freshness_note,
)
from dashboards.timeline.charts import campaign_gantt, reach_engagement_timeline
from dashboards.timeline.data import CAMPAIGNS_KEY, WEEKLY_KEY, load_campaigns, load_weekly

MANIFEST = DashboardManifest(
    slug="timeline",
    title="Reach & Engagement Timeline",
    description="Dual-axis weekly reach/engagement by sentiment, with a campaign Gantt.",
    icon="timeline",
    category="Media Intelligence",
    data_requirements=["synthetic:media_weekly"],
    internal=True,
)

PAGE_ICONS = {
    "timeline": "timeline",
    "timeline-campaigns": "campaign",
}


def _register_data_sources() -> None:
    # Registered at both import and build time, since Vizro clears the shared
    # data manager during dev hot reload.
    data_manager[WEEKLY_KEY] = load_weekly
    data_manager[CAMPAIGNS_KEY] = load_campaigns


_register_data_sources()


def data_health() -> list[DataSourceHealth]:
    df = load_weekly()
    latest = df["week_start"].max()
    return [
        DataSourceHealth(
            name="synthetic:media_weekly",
            status="ok",
            detail="Synthetic dataset (always available).",
            rows=len(df),
            as_of=str(getattr(latest, "date", lambda: latest)()),
        )
    ]


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    _register_data_sources()
    all_campaigns = load_campaigns()["campaign_label"].tolist()
    latest = load_weekly()["week_start"].max()
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
                figure=reach_engagement_timeline(data_frame=WEEKLY_KEY),
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
                figure=campaign_gantt(data_frame=CAMPAIGNS_KEY),
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
