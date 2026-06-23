from __future__ import annotations

from functools import lru_cache

import pandas as pd

from data_sources.bq import safe_query, table_ref

PROJECT_ID = "native-analytics-486522"
DATASET_ID = "amazon_2026"

OVERVIEW_KEY = "amazon_2026_overview_tml_split"
OVERVIEW_KPI_KEY = "amazon_2026_overview_kpi"
MEDIA_TYPE_PERIOD_KEY = "amazon_2026_trad_media_type_period"
SENTIMENT_SOURCE_MONTHLY_KEY = "amazon_2026_source_monthly"
SOURCE_SENTIMENT_MONTHLY_KEY = "amazon_2026_source_sentiment_monthly"
SOME_PLATFORM_KEY = "amazon_2026_some_platform"
TOP_ITEMS_KEY = "amazon_2026_top_items"
NARRATIVES_KEY = "amazon_2026_narratives"
PUBLISHERS_KEY = "amazon_2026_publishers"
PARAM_SINK_KEY = "amazon_2026_param_sink"
PUBLISHER_TRAD_TIMELINE_KEY = "amazon_2026_publisher_trad_timeline"
PUBLISHER_SOME_TIMELINE_KEY = "amazon_2026_publisher_some_timeline"
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
ANGLES_KEY = "amazon_2026_angles"
NARRATIVE_OVERVIEW_KEY = "amazon_2026_narrative_overview"
NARRATIVE_WEEKLY_REACH_KEY = "amazon_2026_narrative_weekly_reach"
NARRATIVE_SOME_WEEKLY_ENGAGEMENT_KEY = "amazon_2026_narrative_some_weekly_engagement"
NARRATIVE_TRAD_SENTIMENT_TIMELINE_KEY = "amazon_2026_narrative_trad_sentiment_timeline"
NARRATIVE_SOME_SENTIMENT_TIMELINE_KEY = "amazon_2026_narrative_some_sentiment_timeline"
NARRATIVE_TRAD_MEDIA_TYPE_TIMELINE_KEY = "amazon_2026_narrative_trad_media_type_timeline"
NARRATIVE_SOME_PLATFORM_TIMELINE_KEY = "amazon_2026_narrative_some_platform_timeline"
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
DISCOVER_ITEMS_KEY = "amazon_2026_discover_items"

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

# Values treated as "no campaign assigned" when filtering campaign columns.
NON_CAMPAIGN_VALUES = "('', 'no', 'false', 'n', 'n/a', 'none', 'null', '0')"

# Values in a `paid` column indicating sponsored/paid content.
PAID_VALUES = "('paid', 'sponsored', 'branded', 'advertorial', 'promoted')"


def _table(name: str) -> str:
    return table_ref(DATASET_ID, name, project=PROJECT_ID)


PUBLISHER_SEED_CTE = f"""publisher_seed AS (
      SELECT
        LOWER(COALESCE(NULLIF(TRIM(display_name), ''), publisher_uid)) AS display_key,
        ANY_VALUE(publisher_uid) AS publisher_uid
      FROM {_table('amazon_2026_publishers')}
      GROUP BY display_key
    )"""


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


def _sentiment_case(expr: str) -> str:
    """Return a SQL CASE expression normalising *expr* to Positive / Neutral / Negative."""
    w = f"LOWER(TRIM(COALESCE({expr}, '')))"
    return f"CASE WHEN {w} LIKE 'pos%' THEN 'Positive' WHEN {w} LIKE 'neg%' THEN 'Negative' ELSE 'Neutral' END"


def _weekly_grid_cte(dim_col: str, dim_plural: str, extra_filter: str = "") -> str:
    """Return the all_{dim_plural}, all_weeks, and grid CTEs for a weeks × dim CROSS JOIN.

    The caller is responsible for defining an ``all_weekly`` CTE upstream that
    contains both ``week_start`` and ``{dim_col}`` columns.
    """
    filter_clause = f"\n      AND {extra_filter}" if extra_filter else ""
    return (
        f"all_{dim_plural} AS (\n"
        f"        SELECT DISTINCT {dim_col}\n"
        f"        FROM all_weekly\n"
        f"        WHERE {dim_col} IS NOT NULL{filter_clause}\n"
        f"    ),\n"
        f"    all_weeks AS (\n"
        f"        SELECT DISTINCT week_start FROM all_weekly WHERE week_start IS NOT NULL\n"
        f"    ),\n"
        f"    grid AS (\n"
        f"        SELECT w.week_start, d.{dim_col}\n"
        f"        FROM all_weeks w CROSS JOIN all_{dim_plural} d\n"
        f"    )"
    )


def prime_schema_cache() -> None:
    """Pre-warm _table_column_map for all known tables before any threads are spawned.

    lru_cache is not call-once under concurrency — two threads hitting the same
    uncached key will both fire a BigQuery INFORMATION_SCHEMA query simultaneously.
    Calling this before ThreadPoolExecutor startup ensures the cache is populated
    and all subsequent calls from worker threads are instant cache hits.
    """
    for table in (
        "amazon_2026_trad",
        "amazon_2026_some",
        "amazon_2026_publishers",
        "amazon_2026_narratives",
        "amazon_2026_angles",
    ):
        _table_column_map(table)


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
