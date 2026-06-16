from __future__ import annotations

import pandas as pd
import vizro.models as vm
from vizro.managers import data_manager

from dashboards._base import BuildContext, DataSourceHealth, DashboardManifest
from dashboards.amazon_2026.data_angles import load_angles
from dashboards.amazon_2026.data_archive import load_archive_scatter
from dashboards.amazon_2026.data_campaigns import (
    load_campaign_narratives,
    load_campaign_profile,
    load_campaign_some_sentiment_timeline,
    load_campaign_some_weekly_engagement,
    load_campaign_timeline,
    load_campaign_top_journalists,
    load_campaign_top_publications,
    load_campaign_top_publishers,
    load_campaign_trad_sentiment_timeline,
    load_campaign_weekly_reach,
)
from dashboards.amazon_2026.data_common import (
    ANGLES_KEY,
    ARCHIVE_SCATTER_KEY,
    CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY,
    CAMPAIGN_TIMELINE_KEY,
    CAMPAIGN_TOP_JOURNALISTS_KEY,
    CAMPAIGN_TOP_PUBLICATIONS_KEY,
    CAMPAIGN_TOP_PUBLISHERS_KEY,
    CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_WEEKLY_REACH_KEY,
    CAMPAIGN_PROFILE_KEY,
    CAMPAIGN_NARRATIVES_KEY,
    DATASET_ID,
    DISCOVER_ITEMS_KEY,
    MEDIA_TYPE_PERIOD_KEY,
    NARRATIVE_DETAIL_KPI_KEY,
    NARRATIVE_OVERVIEW_KEY,
    NARRATIVES_KEY,
    NARRATIVE_WEEKLY_REACH_KEY,
    NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY,
    NARRATIVE_SOME_PLATFORM_TIMELINE_KEY,
    NARRATIVES_KPI_KEY,
    NARRATIVE_TOP_PUBLISHERS_KEY,
    NARRATIVE_TOP_JOURNALISTS_KEY,
    NARRATIVE_TOP_PUBLICATIONS_KEY,
    OVERVIEW_KEY,
    OVERVIEW_KPI_KEY,
    PARAM_SINK_KEY,
    PUBLISHERS_KEY,
    PUBLISHER_SOME_TIMELINE_KEY,
    PUBLISHER_SOME_TOPIC_AREAS_KEY,
    PUBLISHER_TOPIC_AREAS_KEY,
    PUBLISHER_TOP_PUBLICATIONS_KEY,
    PUBLISHER_TRAD_TIMELINE_KEY,
    SENTIMENT_SOURCE_MONTHLY_KEY,
    TOPIC_AREA_BREAKDOWN_KEY,
    TOPIC_AREA_CAMPAIGNS_KEY,
    TOPIC_AREA_MEDIA_KEY,
    TOPIC_AREA_OVERVIEW_KEY,
    TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY,
    TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY,
    TOPIC_AREA_TOP_JOURNALISTS_KEY,
    TOPIC_AREA_TOP_PUBLICATIONS_KEY,
    TOPIC_AREA_TOP_PUBLISHERS_KEY,
    TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY,
    TOPIC_AREA_WEEKLY_REACH_KEY,
    SOME_PLATFORM_KEY,
    SOURCE_SENTIMENT_MONTHLY_KEY,
    TOP_ARTICLES_KEY,
    TOP_POSTS_KEY,
    _table,
)
from dashboards.amazon_2026.data_narratives import (
    load_narrative_detail_kpis,
    load_narrative_overview,
    load_narrative_some_platform_timeline,
    load_narrative_some_sentiment_timeline,
    load_narrative_some_weekly_engagement,
    load_narrative_trad_media_type_timeline,
    load_narrative_trad_sentiment_timeline,
    load_narrative_weekly_reach,
    load_narrative_top_publishers,
    load_narrative_top_journalists,
    load_narrative_top_publications,
    load_narratives,
    load_narratives_kpi,
)
from dashboards.amazon_2026.data_overview import (
    load_media_type_period,
    load_overview_daily,
    load_overview_kpis,
    load_sentiment_source_monthly,
    load_some_platform,
    load_source_sentiment_monthly,
    load_top_articles,
    load_top_posts,
)
from dashboards.amazon_2026.data_publishers import (
    load_publisher_some_topic_areas,
    load_publisher_topic_areas,
    load_publisher_top_publications,
    load_publisher_some_timeline,
    load_publisher_trad_timeline,
    load_publishers,
)
from dashboards.amazon_2026.data_discover import load_discover_items
from dashboards.amazon_2026.data_topic_areas import (
    load_topic_area_breakdown,
    load_topic_area_campaigns,
    load_topic_area_media,
    load_topic_area_overview,
    load_topic_area_some_sentiment_timeline,
    load_topic_area_some_weekly_engagement,
    load_topic_area_top_journalists,
    load_topic_area_top_publications,
    load_topic_area_top_publishers,
    load_topic_area_trad_sentiment_timeline,
    load_topic_area_weekly_reach,
)
from data_sources.bq import safe_query

MANIFEST = DashboardManifest(
    slug="amazon_2026",
    title="Amazon 2026",
    description="Four-page BigQuery dashboard for timeline, narratives, publishers, and angles.",
    icon="storefront",
    category="Amazon Intelligence",
    data_requirements=[
        "bigquery:amazon_2026.amazon_2026_trad",
        "bigquery:amazon_2026.amazon_2026_some",
        "bigquery:amazon_2026.amazon_2026_narratives",
        "bigquery:amazon_2026.amazon_2026_publishers",
        "bigquery:amazon_2026.amazon_2026_angles",
    ],
)

PAGE_ICONS = {
    "amazon-2026-overview": "dashboard",
    "amazon-2026-topic-areas": "donut_large",
    "amazon-2026-narratives": "forum",
    "amazon-2026-campaigns": "campaign",
    "amazon-2026-publishers": "person",
    "amazon-2026-discover": "explore",
    "amazon-2026-archive": "archive",
}

__all__ = ["MANIFEST", "build_pages", "data_health"]


def data_health() -> list[DataSourceHealth]:
    checks = [
        "amazon_2026_trad",
        "amazon_2026_some",
        "amazon_2026_narratives",
        "amazon_2026_publishers",
        "amazon_2026_angles",
    ]
    status: list[DataSourceHealth] = []
    for table_name in checks:
        sql = f"SELECT COUNT(*) AS rows FROM {_table(table_name)}"
        fallback = pd.DataFrame({"rows": [0]})
        try:
            df = safe_query(sql, fallback=fallback)
            rows = int(df.iloc[0]["rows"]) if not df.empty else 0
            status.append(
                DataSourceHealth(
                    name=f"bigquery:{DATASET_ID}.{table_name}",
                    status="ok" if rows > 0 else "degraded",
                    detail="Live from BigQuery." if rows > 0 else "No rows found.",
                    rows=rows,
                )
            )
        except Exception as exc:
            status.append(
                DataSourceHealth(
                    name=f"bigquery:{DATASET_ID}.{table_name}",
                    status="error",
                    detail=f"Query failed ({type(exc).__name__}).",
                    rows=None,
                )
            )
    return status


def _register_data_sources() -> None:
    data_manager[OVERVIEW_KEY] = load_overview_daily
    data_manager[OVERVIEW_KPI_KEY] = load_overview_kpis
    data_manager[MEDIA_TYPE_PERIOD_KEY] = load_media_type_period
    data_manager[SENTIMENT_SOURCE_MONTHLY_KEY] = load_sentiment_source_monthly
    data_manager[SOURCE_SENTIMENT_MONTHLY_KEY] = load_source_sentiment_monthly
    data_manager[SOME_PLATFORM_KEY] = load_some_platform
    data_manager[TOP_ARTICLES_KEY] = load_top_articles
    data_manager[TOP_POSTS_KEY] = load_top_posts
    data_manager[NARRATIVES_KEY] = load_narratives
    data_manager[NARRATIVES_KPI_KEY] = load_narratives_kpi
    data_manager[NARRATIVE_DETAIL_KPI_KEY] = load_narrative_detail_kpis
    data_manager[NARRATIVE_OVERVIEW_KEY] = load_narrative_overview
    data_manager[NARRATIVE_WEEKLY_REACH_KEY] = load_narrative_weekly_reach
    data_manager[NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY] = load_narrative_some_weekly_engagement
    data_manager[NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY] = load_narrative_trad_sentiment_timeline
    data_manager[NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY] = load_narrative_some_sentiment_timeline
    data_manager[NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY] = load_narrative_trad_media_type_timeline
    data_manager[NARRATIVE_SOME_PLATFORM_TIMELINE_KEY] = load_narrative_some_platform_timeline
    data_manager[NARRATIVE_TOP_PUBLISHERS_KEY] = load_narrative_top_publishers
    data_manager[NARRATIVE_TOP_JOURNALISTS_KEY] = load_narrative_top_journalists
    data_manager[NARRATIVE_TOP_PUBLICATIONS_KEY] = load_narrative_top_publications
    data_manager[PARAM_SINK_KEY] = lambda: pd.DataFrame()
    data_manager[PUBLISHERS_KEY] = load_publishers
    data_manager[PUBLISHER_TRAD_TIMELINE_KEY] = load_publisher_trad_timeline
    data_manager[PUBLISHER_SOME_TIMELINE_KEY] = load_publisher_some_timeline
    data_manager[PUBLISHER_TOPIC_AREAS_KEY] = load_publisher_topic_areas
    data_manager[PUBLISHER_SOME_TOPIC_AREAS_KEY] = load_publisher_some_topic_areas
    data_manager[PUBLISHER_TOP_PUBLICATIONS_KEY] = load_publisher_top_publications
    data_manager[TOPIC_AREA_BREAKDOWN_KEY] = load_topic_area_breakdown
    data_manager[TOPIC_AREA_MEDIA_KEY] = load_topic_area_media
    data_manager[TOPIC_AREA_CAMPAIGNS_KEY] = load_topic_area_campaigns
    data_manager[TOPIC_AREA_OVERVIEW_KEY] = load_topic_area_overview
    data_manager[TOPIC_AREA_WEEKLY_REACH_KEY] = load_topic_area_weekly_reach
    data_manager[TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY] = load_topic_area_some_weekly_engagement
    data_manager[TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY] = load_topic_area_trad_sentiment_timeline
    data_manager[TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY] = load_topic_area_some_sentiment_timeline
    data_manager[TOPIC_AREA_TOP_PUBLISHERS_KEY] = load_topic_area_top_publishers
    data_manager[TOPIC_AREA_TOP_JOURNALISTS_KEY] = load_topic_area_top_journalists
    data_manager[TOPIC_AREA_TOP_PUBLICATIONS_KEY] = load_topic_area_top_publications
    data_manager[ANGLES_KEY] = load_angles
    data_manager[ARCHIVE_SCATTER_KEY] = load_archive_scatter
    data_manager[CAMPAIGN_TIMELINE_KEY] = load_campaign_timeline
    data_manager[CAMPAIGN_WEEKLY_REACH_KEY] = load_campaign_weekly_reach
    data_manager[CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY] = load_campaign_some_weekly_engagement
    data_manager[CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY] = load_campaign_trad_sentiment_timeline
    data_manager[CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY] = load_campaign_some_sentiment_timeline
    data_manager[CAMPAIGN_TOP_PUBLISHERS_KEY] = load_campaign_top_publishers
    data_manager[CAMPAIGN_TOP_JOURNALISTS_KEY] = load_campaign_top_journalists
    data_manager[CAMPAIGN_TOP_PUBLICATIONS_KEY] = load_campaign_top_publications
    data_manager[CAMPAIGN_PROFILE_KEY] = load_campaign_profile
    data_manager[CAMPAIGN_NARRATIVES_KEY] = load_campaign_narratives
    data_manager[DISCOVER_ITEMS_KEY] = load_discover_items


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    _register_data_sources()
    from dashboards.amazon_2026.pages import build_all_pages
    return build_all_pages(ctx, MANIFEST.base_path)
