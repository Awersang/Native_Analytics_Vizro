from __future__ import annotations

from typing import Callable

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
    CAMPAIGN_NARRATIVES_KEY,
    CAMPAIGN_PROFILE_KEY,
    CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY,
    CAMPAIGN_TIMELINE_KEY,
    CAMPAIGN_TOP_JOURNALISTS_KEY,
    CAMPAIGN_TOP_PUBLICATIONS_KEY,
    CAMPAIGN_TOP_PUBLISHERS_KEY,
    CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY,
    CAMPAIGN_WEEKLY_REACH_KEY,
    DATASET_ID,
    DISCOVER_ITEMS_KEY,
    MEDIA_TYPE_PERIOD_KEY,
    NARRATIVE_DETAIL_KPI_KEY,
    NARRATIVE_OVERVIEW_KEY,
    NARRATIVE_SOME_PLATFORM_TIMELINE_KEY,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY,
    NARRATIVE_TOP_JOURNALISTS_KEY,
    NARRATIVE_TOP_PUBLICATIONS_KEY,
    NARRATIVE_TOP_PUBLISHERS_KEY,
    NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY,
    NARRATIVE_WEEKLY_REACH_KEY,
    NARRATIVES_KEY,
    NARRATIVES_KPI_KEY,
    OVERVIEW_KEY,
    OVERVIEW_KPI_KEY,
    PARAM_SINK_KEY,
    PUBLISHER_SOME_TIMELINE_KEY,
    PUBLISHER_SOME_TOPIC_AREAS_KEY,
    PUBLISHER_TOP_PUBLICATIONS_KEY,
    PUBLISHER_TOPIC_AREAS_KEY,
    PUBLISHER_TRAD_TIMELINE_KEY,
    PUBLISHERS_KEY,
    SENTIMENT_SOURCE_MONTHLY_KEY,
    SOME_PLATFORM_KEY,
    SOURCE_SENTIMENT_MONTHLY_KEY,
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
    TOP_ITEMS_KEY,
    prime_schema_cache,
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
    load_overview_kpis,
    load_sentiment_source_monthly,
    load_some_platform,
    load_source_sentiment_monthly,
    load_tml_split,
    load_top_items,
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

__all__ = ["MANIFEST", "build_pages", "warm_caches", "data_health"]


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


# Single source of truth: every data_manager key this dashboard owns, mapped
# to its loader. Drives both registration (below) and cache warmup
# (warm_caches()) so a new key can't be registered without also being
# preloaded, or vice versa.
_LOADERS: dict[str, Callable[[], pd.DataFrame]] = {
    OVERVIEW_KEY: load_tml_split,
    OVERVIEW_KPI_KEY: load_overview_kpis,
    MEDIA_TYPE_PERIOD_KEY: load_media_type_period,
    SENTIMENT_SOURCE_MONTHLY_KEY: load_sentiment_source_monthly,
    SOURCE_SENTIMENT_MONTHLY_KEY: load_source_sentiment_monthly,
    SOME_PLATFORM_KEY: load_some_platform,
    TOP_ITEMS_KEY: load_top_items,
    NARRATIVES_KEY: load_narratives,
    NARRATIVES_KPI_KEY: load_narratives_kpi,
    NARRATIVE_DETAIL_KPI_KEY: load_narrative_detail_kpis,
    NARRATIVE_OVERVIEW_KEY: load_narrative_overview,
    NARRATIVE_WEEKLY_REACH_KEY: load_narrative_weekly_reach,
    NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY: load_narrative_some_weekly_engagement,
    NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY: load_narrative_trad_sentiment_timeline,
    NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY: load_narrative_some_sentiment_timeline,
    NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY: load_narrative_trad_media_type_timeline,
    NARRATIVE_SOME_PLATFORM_TIMELINE_KEY: load_narrative_some_platform_timeline,
    NARRATIVE_TOP_PUBLISHERS_KEY: load_narrative_top_publishers,
    NARRATIVE_TOP_JOURNALISTS_KEY: load_narrative_top_journalists,
    NARRATIVE_TOP_PUBLICATIONS_KEY: load_narrative_top_publications,
    PARAM_SINK_KEY: lambda: pd.DataFrame(),
    PUBLISHERS_KEY: load_publishers,
    PUBLISHER_TRAD_TIMELINE_KEY: load_publisher_trad_timeline,
    PUBLISHER_SOME_TIMELINE_KEY: load_publisher_some_timeline,
    PUBLISHER_TOPIC_AREAS_KEY: load_publisher_topic_areas,
    PUBLISHER_SOME_TOPIC_AREAS_KEY: load_publisher_some_topic_areas,
    PUBLISHER_TOP_PUBLICATIONS_KEY: load_publisher_top_publications,
    TOPIC_AREA_BREAKDOWN_KEY: load_topic_area_breakdown,
    TOPIC_AREA_CAMPAIGNS_KEY: load_topic_area_campaigns,
    TOPIC_AREA_MEDIA_KEY: load_topic_area_media,
    TOPIC_AREA_OVERVIEW_KEY: load_topic_area_overview,
    TOPIC_AREA_WEEKLY_REACH_KEY: load_topic_area_weekly_reach,
    TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY: load_topic_area_some_weekly_engagement,
    TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY: load_topic_area_trad_sentiment_timeline,
    TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY: load_topic_area_some_sentiment_timeline,
    TOPIC_AREA_TOP_PUBLISHERS_KEY: load_topic_area_top_publishers,
    TOPIC_AREA_TOP_JOURNALISTS_KEY: load_topic_area_top_journalists,
    TOPIC_AREA_TOP_PUBLICATIONS_KEY: load_topic_area_top_publications,
    ANGLES_KEY: load_angles,
    ARCHIVE_SCATTER_KEY: load_archive_scatter,
    CAMPAIGN_TIMELINE_KEY: load_campaign_timeline,
    CAMPAIGN_WEEKLY_REACH_KEY: load_campaign_weekly_reach,
    CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY: load_campaign_some_weekly_engagement,
    CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY: load_campaign_trad_sentiment_timeline,
    CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY: load_campaign_some_sentiment_timeline,
    CAMPAIGN_TOP_PUBLISHERS_KEY: load_campaign_top_publishers,
    CAMPAIGN_TOP_JOURNALISTS_KEY: load_campaign_top_journalists,
    CAMPAIGN_TOP_PUBLICATIONS_KEY: load_campaign_top_publications,
    CAMPAIGN_PROFILE_KEY: load_campaign_profile,
    CAMPAIGN_NARRATIVES_KEY: load_campaign_narratives,
    DISCOVER_ITEMS_KEY: load_discover_items,
}


def _register_data_sources() -> None:
    for key, loader in _LOADERS.items():
        data_manager[key] = loader


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    """Construct this dashboard's pages. Pure: no network I/O.

    Registering data sources is just an in-memory dict assignment (cheap), so
    it stays here — pages reference these keys by name. Actually warming the
    cache over the network is a separate, explicit step: warm_caches().
    """
    _register_data_sources()
    from dashboards.amazon_2026.pages import build_all_pages
    return build_all_pages(ctx, MANIFEST.base_path)


# Cap concurrent BigQuery connections during warmup so a cold start doesn't
# fire ~50 queries at once against a single vCPU (IMPROVEMENT_PLAN.md §5.7).
_PRELOAD_MAX_WORKERS = 8


def _preload_all() -> None:
    """Synchronously load every key in _LOADERS, bounded and in parallel."""
    import logging
    import time
    from concurrent.futures import ThreadPoolExecutor

    logger = logging.getLogger(__name__)
    preload_keys = list(_LOADERS.keys())

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=_PRELOAD_MAX_WORKERS) as executor:
        futures = {key: executor.submit(data_manager[key].load) for key in preload_keys}
        for key, future in futures.items():
            try:
                future.result()
            except Exception as exc:
                logger.warning("amazon_2026 preload failed for %s: %s", key, exc)
    logger.info(
        "amazon_2026 preload complete in %.2fs (%d keys).",
        time.monotonic() - started,
        len(preload_keys),
    )

    # Discover's per-record tokenization/clustering pass (charts_discover.py
    # _server_discover_data) is its own cache on top of data_manager and was
    # previously left to populate lazily on first page visit. Warm it here too,
    # now that DISCOVER_ITEMS_KEY is loaded, so that cost never lands on a user.
    from dashboards.amazon_2026.charts_discover import _server_discover_data
    try:
        _server_discover_data()
    except Exception as exc:
        logger.warning("amazon_2026 discover cache warmup failed: %s", exc)


def warm_caches() -> None:
    """Warm the data_manager cache for every registered key, once per process.

    Without this, the first user click on a page triggers a wave of sequential
    BQ queries inside a single callback. Loading them upfront means the cache
    is ready before any user interaction, so that first click is instant.
    Iterating _LOADERS (rather than a hand-maintained key list) means a newly
    registered key is preloaded automatically — it can't be silently un-warmed.
    """
    import threading

    prime_schema_cache()
    threading.Thread(target=_preload_all, daemon=True).start()
