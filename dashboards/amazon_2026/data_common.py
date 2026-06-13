from __future__ import annotations

from functools import lru_cache

import pandas as pd

from data_sources.bq import safe_query, table_ref

PROJECT_ID = "native-analytics-486522"
DATASET_ID = "amazon_2026"

OVERVIEW_KEY = "amazon_2026_overview_tml_split"
OVERVIEW_KPI_KEY = "amazon_2026_overview_kpi"
MEDIA_TYPE_MONTHLY_KEY = "amazon_2026_trad_media_type_monthly"
MEDIA_TYPE_PERIOD_KEY = "amazon_2026_trad_media_type_period"
SENTIMENT_MONTHLY_KEY = "amazon_2026_trad_sentiment_monthly"
SENTIMENT_PERIOD_KEY = "amazon_2026_trad_sentiment_period"
SENTIMENT_SOURCE_MONTHLY_KEY = "amazon_2026_source_monthly"
SOURCE_SENTIMENT_MONTHLY_KEY = "amazon_2026_source_sentiment_monthly"
SOME_PLATFORM_KEY = "amazon_2026_some_platform"
TOP_ARTICLES_KEY = "amazon_2026_top_articles"
TOP_POSTS_KEY = "amazon_2026_top_posts"
NARRATIVES_KEY = "amazon_2026_narratives"
NARRATIVE_SENTIMENT_KEY = "amazon_2026_narrative_sentiment"
PUBLISHERS_KEY = "amazon_2026_publishers"
PUBLISHER_TRAD_TIMELINE_KEY = "amazon_2026_publisher_trad_timeline"
PUBLISHER_SOME_TIMELINE_KEY = "amazon_2026_publisher_some_timeline"
PUBLISHER_NARRATIVES_KEY = "amazon_2026_publisher_narratives"
PUBLISHER_TOPIC_AREAS_KEY = "amazon_2026_publisher_topic_areas"
PUBLISHER_SOME_TOPIC_AREAS_KEY = "amazon_2026_publisher_some_topic_areas"
PUBLISHER_TOP_PUBLICATIONS_KEY = "amazon_2026_publisher_top_publications"
TOPIC_AREA_BREAKDOWN_KEY = "amazon_2026_topic_area_breakdown"
TOPIC_AREA_MEDIA_KEY = "amazon_2026_topic_area_media"
TOPIC_AREA_CAMPAIGNS_KEY = "amazon_2026_topic_area_campaigns"
TOPIC_AREA_OVERVIEW_KEY = "amazon_2026_topic_area_overview"
TOPIC_AREA_WEEKLY_REACH_KEY = "amazon_2026_topic_area_weekly_reach"
TOPIC_AREA_SOME_WEEKLY_ENGAGEMENT_KEY = "amazon_2026_topic_area_some_weekly_engagement"
TOPIC_AREA_TRAD_SENTIMENT_TIMELINE_KEY = "amazon_2026_topic_area_trad_sentiment_timeline"
TOPIC_AREA_SOME_SENTIMENT_TIMELINE_KEY = "amazon_2026_topic_area_some_sentiment_timeline"
TOPIC_AREA_TOP_PUBLISHERS_KEY = "amazon_2026_topic_area_top_publishers"
TOPIC_AREA_TOP_JOURNALISTS_KEY = "amazon_2026_topic_area_top_journalists"
TOPIC_AREA_TOP_PUBLICATIONS_KEY = "amazon_2026_topic_area_top_publications"
TOPIC_AREA_PROFILE_KEY = "amazon_2026_topic_area_profile"
TOPIC_AREA_NARRATIVES_KEY = "amazon_2026_topic_area_narratives"
ANGLES_KEY = "amazon_2026_angles"
NARRATIVE_OVERVIEW_KEY = "amazon_2026_narrative_overview"
NARRATIVE_WEEKLY_REACH_KEY = "amazon_2026_narrative_weekly_reach"
NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY = "amazon_2026_narrative_some_weekly_engagement"
NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY = "amazon_2026_narrative_trad_sentiment_timeline"
NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY = "amazon_2026_narrative_some_sentiment_timeline"
NARRATIVES_KPI_KEY = "amazon_2026_narratives_kpi"
NARRATIVE_DETAIL_KPI_KEY = "amazon_2026_narrative_detail_kpi"
NARRATIVE_TOP_PUBLISHERS_KEY = "amazon_2026_narrative_top_publishers"
NARRATIVE_TOP_JOURNALISTS_KEY = "amazon_2026_narrative_top_journalists"
NARRATIVE_TOP_PUBLICATIONS_KEY = "amazon_2026_narrative_top_publications"
ARCHIVE_SCATTER_KEY = "amazon_2026_archive_scatter"
CAMPAIGN_TIMELINE_KEY = "amazon_2026_campaign_timeline"
CAMPAIGN_WEEKLY_REACH_KEY = "amazon_2026_campaign_weekly_reach"
CAMPAIGN_SOME_WEEKLY_ENGAGEMENT_KEY = "amazon_2026_campaign_some_weekly_engagement"
CAMPAIGN_TRAD_SENTIMENT_TIMELINE_KEY = "amazon_2026_campaign_trad_sentiment_timeline"
CAMPAIGN_SOME_SENTIMENT_TIMELINE_KEY = "amazon_2026_campaign_some_sentiment_timeline"
CAMPAIGN_TOP_PUBLISHERS_KEY = "amazon_2026_campaign_top_publishers"
CAMPAIGN_TOP_JOURNALISTS_KEY = "amazon_2026_campaign_top_journalists"
CAMPAIGN_TOP_PUBLICATIONS_KEY = "amazon_2026_campaign_top_publications"
CAMPAIGN_PROFILE_KEY = "amazon_2026_campaign_profile"
CAMPAIGN_NARRATIVES_KEY = "amazon_2026_campaign_narratives"

MEDIA_TYPE_ORDER = [
    "Online",
    "Radio",
    "Newswire",
    "Print",
    "TV",
    "Podcast",
    "Blog",
    "Newsletter",
    "Video",
    "Unknown",
]

SENTIMENT_ORDER = ["Positive", "Neutral", "Negative"]

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _table(name: str) -> str:
    return table_ref(DATASET_ID, name, project=PROJECT_ID)


@lru_cache
def _table_column_map(table_name: str) -> dict[str, str]:
    sql = f"""
        SELECT column_name
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table_name}'
    """
    df = safe_query(sql, fallback=pd.DataFrame(columns=["column_name"]))
    if df.empty or "column_name" not in df.columns:
        return {}
    return {str(col).lower(): str(col) for col in df["column_name"].dropna()}


def _metric_pivot(
    cte: str,
    dims: list[str],
    count_col: str = "publications",
    reach_col: str = "reach",
) -> str:
    """Return a UNION ALL block that pivots count and reach columns into (base_metric, metric_value) rows."""
    dim_sql = ", ".join(dims)
    return (
        f"SELECT {dim_sql}, 'publications' AS base_metric, {count_col} AS metric_value FROM {cte}\n"
        f"        UNION ALL\n"
        f"        SELECT {dim_sql}, 'reach' AS base_metric, {reach_col} AS metric_value FROM {cte}"
    )


def _optional_json_string_expr(alias: str, columns: dict[str, str], candidates: list[str]) -> str:
    for candidate in candidates:
        column_name = columns.get(candidate.lower())
        if column_name:
            return f"NULLIF(TRIM(TO_JSON_STRING({alias}.`{column_name}`)), 'null')"
    return "CAST(NULL AS STRING)"


def _optional_string_expr(alias: str, columns: dict[str, str], candidates: list[str]) -> str:
    for candidate in candidates:
        column_name = columns.get(candidate.lower())
        if column_name:
            return f"NULLIF(TRIM(CAST({alias}.`{column_name}` AS STRING)), '')"
    return "CAST(NULL AS STRING)"


def _optional_numeric_expr(alias: str, columns: dict[str, str], candidates: list[str]) -> str:
    for candidate in candidates:
        column_name = columns.get(candidate.lower())
        if column_name:
            return f"COALESCE({alias}.`{column_name}`, 0)"
    return "0"


def _coalesce_string_expr(alias: str, columns: dict[str, str], candidates: list[str]) -> str:
    """Like ``_optional_string_expr``, but COALESCEs across every existing candidate column.

    Useful when different rows populate different columns (e.g. ``Description``
    is blank for some SoMe posts while ``Main_Text`` is filled in) — picking a
    single column statically would leave those rows blank.
    """
    exprs = [
        f"NULLIF(TRIM(CAST({alias}.`{columns[candidate.lower()]}` AS STRING)), '')"
        for candidate in candidates
        if candidate.lower() in columns
    ]
    if not exprs:
        return "CAST(NULL AS STRING)"
    return f"COALESCE({', '.join(exprs)})"
