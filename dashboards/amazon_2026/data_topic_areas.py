"""Data loaders for the Topic Areas page."""
from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import (
    CAMPAIGN_COLUMN_CANDIDATES,
    JOURNALIST_EXCLUSION_FILTER,
    NON_CAMPAIGN_VALUES,
    PUBLISHER_DISPLAY_CANDIDATES,
    SOME_ANGLE_CANDIDATES,
    SOME_CONTENT_CANDIDATES,
    SOME_SENTIMENT_CANDIDATES,
    TRAD_ANGLE_CANDIDATES,
    TRAD_SUMMARY_CANDIDATES,
    _coalesce_string_expr,
    _optional_numeric_expr,
    _optional_string_expr,
    _sentiment_case,
    _table,
    _table_column_map,
    _weekly_grid_cte,
)
from dashboards.amazon_2026.fixtures import (
    _topic_area_breakdown_fixture,
    _topic_area_campaigns_fixture,
    _topic_area_media_fixture,
    _topic_area_overview_fixture,
    _topic_area_some_sentiment_timeline_fixture,
    _topic_area_some_weekly_engagement_fixture,
    _topic_area_top_journalists_fixture,
    _topic_area_top_publications_fixture,
    _topic_area_top_publishers_fixture,
    _topic_area_trad_sentiment_timeline_fixture,
    _topic_area_weekly_reach_fixture,
)
from data_sources.bq import safe_query


def load_topic_area_breakdown() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    trad_theme_expr = _optional_string_expr("t", trad_columns, ["Theme"])
    trad_reach_expr = _optional_numeric_expr("t", trad_columns, ["Reach"])

    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    some_theme_expr = _optional_string_expr("s", some_columns, ["Theme"])
    some_engagement_expr = _optional_numeric_expr("s", some_columns, ["Engagement"])

    sql = f"""
    SELECT
      COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
      COALESCE(NULLIF(TRIM({trad_theme_expr}), ''), 'Unknown') AS theme,
      'Trad' AS source,
      COUNT(*) AS publications,
      SUM({trad_reach_expr}) AS reach
    FROM {_table('amazon_2026_trad')} AS t
    GROUP BY 1, 2

    UNION ALL

    SELECT
      COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
      COALESCE(NULLIF(TRIM({some_theme_expr}), ''), 'Unknown') AS theme,
      'SoMe' AS source,
      COUNT(*) AS publications,
      SUM({some_engagement_expr}) AS reach
    FROM {_table('amazon_2026_some')} AS s
    GROUP BY 1, 2
    """
    return safe_query(sql, fallback=_topic_area_breakdown_fixture())


def load_topic_area_media() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    trad_media_expr = _optional_string_expr("t", trad_columns, ["Media_Type"])
    trad_reach_expr = _optional_numeric_expr("t", trad_columns, ["Reach"])

    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    some_platform_expr = _optional_string_expr("s", some_columns, ["Platform"])
    some_engagement_expr = _optional_numeric_expr("s", some_columns, ["Engagement"])

    sql = f"""
    SELECT
      COALESCE(NULLIF(TRIM({trad_media_expr}), ''), 'Unknown') AS media_label,
      COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
      'Trad' AS source,
      COUNT(*) AS publications,
      SUM({trad_reach_expr}) AS reach
    FROM {_table('amazon_2026_trad')} AS t
    GROUP BY 1, 2

    UNION ALL

    SELECT
      COALESCE(NULLIF(TRIM({some_platform_expr}), ''), 'Unknown') AS media_label,
      COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
      'SoMe' AS source,
      COUNT(*) AS publications,
      SUM({some_engagement_expr}) AS reach
    FROM {_table('amazon_2026_some')} AS s
    GROUP BY 1, 2
    """
    return safe_query(sql, fallback=_topic_area_media_fixture())


def load_topic_area_campaigns() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, CAMPAIGN_COLUMN_CANDIDATES
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, CAMPAIGN_COLUMN_CANDIDATES
    )
    some_engagement_positive_expr = _optional_numeric_expr("s", some_columns, ["engagement_positive"])
    some_engagement_negative_expr = _optional_numeric_expr("s", some_columns, ["engagement_negative"])
    some_engagement_neutral_expr = _optional_numeric_expr("s", some_columns, ["engagement_neutral"])

    sql = f"""
    WITH trad_base AS (
      SELECT
        {trad_campaign_expr} AS campaign,
        COUNT(*) AS trad_article_count,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS trad_total_reach,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'pos%', CAST(COALESCE(t.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(t.Reach, 0) AS INT64))
        ) AS trad_positive_pct,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'neg%', CAST(COALESCE(t.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(t.Reach, 0) AS INT64))
        ) AS trad_negative_pct
      FROM {_table('amazon_2026_trad')} AS t
      WHERE {trad_campaign_expr} IS NOT NULL
        AND TRIM(LOWER(CAST({trad_campaign_expr} AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
      GROUP BY campaign
    ),
    some_base AS (
      SELECT
        {some_campaign_expr} AS campaign,
        COUNT(*) AS some_post_count,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS some_total_reach,
        SUM(COALESCE(s.Engagement, 0)) AS some_total_engagement,
        AVG(COALESCE(s.Engagement, 0)) AS some_avg_engagement,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(s.Sentiment, ''))) LIKE 'pos%', CAST(COALESCE(s.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(s.Reach, 0) AS INT64))
        ) AS some_positive_pct,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(s.Sentiment, ''))) LIKE 'neg%', CAST(COALESCE(s.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(s.Reach, 0) AS INT64))
        ) AS some_negative_pct,
        SUM({some_engagement_positive_expr}) AS some_engagement_positive,
        SUM({some_engagement_negative_expr}) AS some_engagement_negative,
        SUM({some_engagement_neutral_expr}) AS some_engagement_neutral
      FROM {_table('amazon_2026_some')} AS s
      WHERE {some_campaign_expr} IS NOT NULL
        AND TRIM(LOWER(CAST({some_campaign_expr} AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
      GROUP BY campaign
    )
    SELECT
      COALESCE(t.campaign, s.campaign) AS campaign,
      COALESCE(t.trad_article_count, 0) AS trad_article_count,
      COALESCE(t.trad_total_reach, 0) AS trad_total_reach,
      COALESCE(t.trad_positive_pct, 0) AS trad_positive_pct,
      COALESCE(t.trad_negative_pct, 0) AS trad_negative_pct,
      COALESCE(s.some_post_count, 0) AS some_post_count,
      COALESCE(s.some_total_reach, 0) AS some_total_reach,
      COALESCE(s.some_total_engagement, 0) AS some_total_engagement,
      COALESCE(s.some_avg_engagement, 0) AS some_avg_engagement,
      COALESCE(s.some_positive_pct, 0) AS some_positive_pct,
      COALESCE(s.some_negative_pct, 0) AS some_negative_pct,
      COALESCE(s.some_engagement_positive, 0) AS some_engagement_positive,
      COALESCE(s.some_engagement_negative, 0) AS some_engagement_negative,
      COALESCE(s.some_engagement_neutral, 0) AS some_engagement_neutral
    FROM trad_base AS t
    FULL OUTER JOIN some_base AS s ON t.campaign = s.campaign
    WHERE (COALESCE(t.trad_total_reach, 0) + COALESCE(s.some_total_reach, 0)) >= 2000
    ORDER BY (COALESCE(t.trad_total_reach, 0) + COALESCE(s.some_total_reach, 0)) DESC, campaign
    """
    return safe_query(sql, fallback=_topic_area_campaigns_fixture())


def load_topic_area_overview() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    some_engagement_positive_expr = _optional_numeric_expr("s", some_columns, ["engagement_positive"])
    some_engagement_negative_expr = _optional_numeric_expr("s", some_columns, ["engagement_negative"])
    some_engagement_neutral_expr = _optional_numeric_expr("s", some_columns, ["engagement_neutral"])

    sql = f"""
    WITH trad_base AS (
      SELECT
        COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
        COUNT(*) AS trad_article_count,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS trad_total_reach,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'pos%', CAST(COALESCE(t.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(t.Reach, 0) AS INT64))
        ) AS trad_positive_pct,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'neg%', CAST(COALESCE(t.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(t.Reach, 0) AS INT64))
        ) AS trad_negative_pct
      FROM {_table('amazon_2026_trad')} AS t
      GROUP BY topic_area
    ),
    some_base AS (
      SELECT
        COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
        COUNT(*) AS some_post_count,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS some_total_reach,
        SUM(COALESCE(s.Engagement, 0)) AS some_total_engagement,
        AVG(COALESCE(s.Engagement, 0)) AS some_avg_engagement,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(s.Sentiment, ''))) LIKE 'pos%', CAST(COALESCE(s.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(s.Reach, 0) AS INT64))
        ) AS some_positive_pct,
        SAFE_DIVIDE(
          SUM(IF(LOWER(TRIM(COALESCE(s.Sentiment, ''))) LIKE 'neg%', CAST(COALESCE(s.Reach, 0) AS INT64), 0)),
          SUM(CAST(COALESCE(s.Reach, 0) AS INT64))
        ) AS some_negative_pct,
        SUM({some_engagement_positive_expr}) AS some_engagement_positive,
        SUM({some_engagement_negative_expr}) AS some_engagement_negative,
        SUM({some_engagement_neutral_expr}) AS some_engagement_neutral
      FROM {_table('amazon_2026_some')} AS s
      GROUP BY topic_area
    )
    SELECT
      COALESCE(t.topic_area, s.topic_area) AS topic_area,
      COALESCE(t.trad_article_count, 0) AS trad_article_count,
      COALESCE(t.trad_total_reach, 0) AS trad_total_reach,
      COALESCE(t.trad_positive_pct, 0) AS trad_positive_pct,
      COALESCE(t.trad_negative_pct, 0) AS trad_negative_pct,
      COALESCE(s.some_post_count, 0) AS some_post_count,
      COALESCE(s.some_total_reach, 0) AS some_total_reach,
      COALESCE(s.some_total_engagement, 0) AS some_total_engagement,
      COALESCE(s.some_avg_engagement, 0) AS some_avg_engagement,
      COALESCE(s.some_positive_pct, 0) AS some_positive_pct,
      COALESCE(s.some_negative_pct, 0) AS some_negative_pct,
      COALESCE(s.some_engagement_positive, 0) AS some_engagement_positive,
      COALESCE(s.some_engagement_negative, 0) AS some_engagement_negative,
      COALESCE(s.some_engagement_neutral, 0) AS some_engagement_neutral
    FROM trad_base AS t
    FULL OUTER JOIN some_base AS s ON t.topic_area = s.topic_area
    ORDER BY (COALESCE(t.trad_total_reach, 0) + COALESCE(s.some_total_reach, 0)) DESC, topic_area
    """
    return safe_query(sql, fallback=_topic_area_overview_fixture())


def load_topic_area_weekly_reach() -> pd.DataFrame:
    """Trad weekly reach + publication count, by topic area."""
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
          CAST(COALESCE(t.Reach, 0) AS INT64) AS reach
        FROM {_table('amazon_2026_trad')} AS t
        WHERE t.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("topic_area", "topic_areas")}
    SELECT
        g.week_start,
        g.topic_area,
        COALESCE(SUM(a.reach), 0) AS weekly_reach,
        COUNT(a.reach) AS weekly_publications
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start AND g.topic_area = a.topic_area
    GROUP BY g.week_start, g.topic_area
    ORDER BY g.week_start, g.topic_area
    """
    return safe_query(sql, fallback=_topic_area_weekly_reach_fixture())


def load_topic_area_some_weekly_engagement() -> pd.DataFrame:
    """SoMe weekly engagement + post count, by topic area."""
    some_columns = _table_column_map("amazon_2026_some")
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
          COALESCE(s.Engagement, 0) AS engagement
        FROM {_table('amazon_2026_some')} AS s
        WHERE s.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("topic_area", "topic_areas")}
    SELECT
        g.week_start,
        g.topic_area,
        COALESCE(SUM(a.engagement), 0) AS weekly_engagement,
        COUNT(a.engagement) AS weekly_posts
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start AND g.topic_area = a.topic_area
    GROUP BY g.week_start, g.topic_area
    ORDER BY g.week_start, g.topic_area
    """
    return safe_query(sql, fallback=_topic_area_some_weekly_engagement_fixture())


def load_topic_area_trad_sentiment_timeline() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    sql = f"""
    WITH base AS (
      SELECT
        DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS week_start,
        COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
        {_sentiment_case('t.Sentiment')} AS sentiment,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE t.Published_At IS NOT NULL
      GROUP BY week_start, topic_area, sentiment
    )
    SELECT topic_area, CAST(week_start AS STRING) AS week_start, sentiment,
           'publications' AS base_metric, publications AS metric_value
    FROM base
    UNION ALL
    SELECT topic_area, CAST(week_start AS STRING) AS week_start, sentiment,
           'reach' AS base_metric, reach AS metric_value
    FROM base
    ORDER BY topic_area, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_topic_area_trad_sentiment_timeline_fixture())


def load_topic_area_some_sentiment_timeline() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    some_sentiment_expr = _optional_string_expr("s", some_columns, SOME_SENTIMENT_CANDIDATES)
    sql = f"""
    WITH base AS (
      SELECT
        DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS week_start,
        COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
        {_sentiment_case(some_sentiment_expr)} AS sentiment,
        COUNT(*) AS posts,
        SUM(COALESCE(s.Engagement, 0)) AS engagement
      FROM {_table('amazon_2026_some')} AS s
      WHERE s.Published_At IS NOT NULL
      GROUP BY week_start, topic_area, sentiment
    )
    SELECT topic_area, CAST(week_start AS STRING) AS week_start, sentiment,
           'posts' AS base_metric, posts AS metric_value
    FROM base
    UNION ALL
    SELECT topic_area, CAST(week_start AS STRING) AS week_start, sentiment,
           'engagement' AS base_metric, engagement AS metric_value
    FROM base
    ORDER BY topic_area, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_topic_area_some_sentiment_timeline_fixture())


def load_topic_area_top_publishers() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    trad_pub_expr = _optional_string_expr("t", trad_columns, PUBLISHER_DISPLAY_CANDIDATES)
    some_pub_expr = _optional_string_expr("s", some_columns, PUBLISHER_DISPLAY_CANDIDATES)

    sql = f"""
    WITH trad_base AS (
      SELECT
        COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
        COALESCE({trad_pub_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_trad')} AS t
      GROUP BY 1, 2, 3
    ),
    some_base AS (
      SELECT
        COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
        COALESCE({some_pub_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_some')} AS s
      GROUP BY 1, 2, 3
    )
    SELECT 'Trad' AS source, topic_area, publisher, media_type_platform, reach, publications
    FROM trad_base
    UNION ALL
    SELECT 'SoMe' AS source, topic_area, publisher, media_type_platform, reach, publications
    FROM some_base
    ORDER BY topic_area, source, reach DESC
    """
    return safe_query(sql, fallback=_topic_area_top_publishers_fixture())


def load_topic_area_top_journalists() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    journalist_expr = _optional_string_expr("t", trad_columns, ["Journalist", "Byline", "Author"])

    sql = f"""
    WITH journalist_base AS (
      SELECT
        COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
        COALESCE(NULLIF(TRIM({journalist_expr}), ''), 'Unknown') AS journalist,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      GROUP BY 1, 2
    )
    SELECT topic_area, journalist, publications, reach
    FROM journalist_base
    WHERE {JOURNALIST_EXCLUSION_FILTER}
    ORDER BY topic_area, reach DESC
    """
    return safe_query(sql, fallback=_topic_area_top_journalists_fixture())


def load_topic_area_top_publications() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    trad_summary_expr = _coalesce_string_expr("t", trad_columns, TRAD_SUMMARY_CANDIDATES)
    some_sentiment_expr = _optional_string_expr("s", some_columns, SOME_SENTIMENT_CANDIDATES)
    some_content_expr = _coalesce_string_expr("s", some_columns, SOME_CONTENT_CANDIDATES)
    trad_angle_expr = _optional_string_expr("t", trad_columns, TRAD_ANGLE_CANDIDATES)
    some_angle_expr = _optional_string_expr("s", some_columns, SOME_ANGLE_CANDIDATES)

    sql = f"""
    WITH trad_pubs AS (
      SELECT
        COALESCE(NULLIF(TRIM({trad_topic_area_expr}), ''), 'Unknown') AS topic_area,
        CAST(DATE(t.Published_At) AS STRING) AS Date,
        'Trad' AS Source,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS Type,
        COALESCE(NULLIF(TRIM(t.Publisher), ''), 'Unknown') AS Publication,
        CAST(NULL AS STRING) AS Author,
        COALESCE(NULLIF(TRIM(t.Title), ''), '(untitled)') AS Title,
        COALESCE({trad_summary_expr}, '') AS Summary,
        COALESCE(NULLIF(TRIM(t.URL), ''), '') AS URL,
        {_sentiment_case('t.Sentiment')} AS Sentiment,
        CAST(COALESCE(t.Reach, 0) AS INT64) AS Reach,
        CAST(NULL AS INT64) AS Engagement,
        COALESCE({trad_angle_expr}, '') AS Angle
      FROM {_table('amazon_2026_trad')} AS t
      WHERE t.Published_At IS NOT NULL
    ),
    some_pubs AS (
      SELECT
        COALESCE(NULLIF(TRIM({some_topic_area_expr}), ''), 'Unknown') AS topic_area,
        CAST(DATE(s.Published_At) AS STRING) AS Date,
        'SoMe' AS Source,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS Type,
        CAST(NULL AS STRING) AS Publication,
        COALESCE(NULLIF(TRIM(s.Author), ''), 'Unknown') AS Author,
        '' AS Title,
        COALESCE({some_content_expr}, '') AS Summary,
        COALESCE(NULLIF(TRIM(s.URL), ''), '') AS URL,
        {_sentiment_case(some_sentiment_expr)} AS Sentiment,
        CAST(COALESCE(s.Reach, 0) AS INT64) AS Reach,
        COALESCE(s.Engagement, 0) AS Engagement,
        COALESCE({some_angle_expr}, '') AS Angle
      FROM {_table('amazon_2026_some')} AS s
      WHERE s.Published_At IS NOT NULL
    ),
    combined AS (
      SELECT * FROM trad_pubs
      UNION ALL
      SELECT * FROM some_pubs
    )
    SELECT topic_area, Date, Source, Type, Publication, Author, Title, Summary, URL, Sentiment, Reach, Engagement, Angle
    FROM (
      SELECT *,
        ROW_NUMBER() OVER (
          PARTITION BY topic_area, Source
          ORDER BY COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
        ) AS rn
      FROM combined
    )
    WHERE rn <= 50
    ORDER BY topic_area, Source, COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
    """
    return safe_query(sql, fallback=_topic_area_top_publications_fixture())
