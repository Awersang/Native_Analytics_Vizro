from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import (
    PUBLISHER_DISPLAY_CANDIDATES,
    PUBLISHER_SEED_CTE,
    SOME_CONTENT_CANDIDATES,
    SOME_SENTIMENT_CANDIDATES,
    TRAD_SUMMARY_CANDIDATES,
    _coalesce_string_expr,
    _optional_json_string_expr,
    _optional_numeric_expr,
    _optional_string_expr,
    _sentiment_case,
    _table,
    _table_column_map,
)
from dashboards.amazon_2026.fixtures import (
    _publisher_some_topic_areas_fixture,
    _publisher_some_timeline_fixture,
    _publisher_topic_areas_fixture,
    _publisher_top_publications_fixture,
    _publisher_trad_timeline_fixture,
    _publishers_fixture,
)
from data_sources.bq import safe_query


def load_publishers() -> pd.DataFrame:
    publishers_columns = _table_column_map("amazon_2026_publishers")

    publisher_platforms_expr = _optional_json_string_expr(
        "p",
        publishers_columns,
        [
            "platforms_url",
            "author_profile_urls",
            "author_profile_url",
            "publisher_profile_urls",
            "publisher_profile_url",
            "profile_urls",
            "profile_url",
        ],
    )
    publisher_website_expr = _optional_json_string_expr(
        "p",
        publishers_columns,
        [
            "website_url",
            "author_external_url",
            "publisher_external_url",
            "external_url",
            "publisher_url",
        ],
    )
    profile_expr = _optional_string_expr("p", publishers_columns, ["profile", "publisher_profile", "profile_text"])
    analysis_expr = _optional_string_expr("p", publishers_columns, ["analysis", "publisher_analysis"])
    some_bio_expr = _optional_string_expr("p", publishers_columns, ["some_bio", "bio"])
    trad_is_tml_expr = _optional_string_expr("p", publishers_columns, ["is_tml", "trad_is_tml"])
    trad_media_type_expr = _optional_string_expr("p", publishers_columns, ["trad_media_type"])
    trad_dominant_media_type_expr = _optional_string_expr(
        "p",
        publishers_columns,
        ["trad_dominant_media_type"],
    )
    some_dominant_platform_expr = _optional_string_expr(
        "p",
        publishers_columns,
        ["some_dominant_platform"],
    )
    trad_top_narratives_expr = _optional_json_string_expr(
        "p",
        publishers_columns,
        ["trad_top_narratives"],
    )
    some_top_narratives_expr = _optional_json_string_expr(
        "p",
        publishers_columns,
        ["Some_top_narratives", "some_top_narratives"],
    )

    some_columns = _table_column_map("amazon_2026_some")
    some_engagement_positive_expr = _optional_numeric_expr("s", some_columns, ["engagement_positive"])
    some_engagement_negative_expr = _optional_numeric_expr("s", some_columns, ["engagement_negative"])
    some_engagement_neutral_expr = _optional_numeric_expr("s", some_columns, ["engagement_neutral"])

    sql = f"""
    WITH {PUBLISHER_SEED_CTE},
    some_engagement_sentiment AS (
      SELECT
        COALESCE(
          NULLIF(TRIM(CAST(s.publisher_uid AS STRING)), ''),
          seed.publisher_uid,
          TO_HEX(MD5(LOWER(COALESCE(NULLIF(TRIM(CAST(s.publisher_display AS STRING)), ''), NULLIF(TRIM(s.Author), ''), 'Unknown'))))
        ) AS publisher_uid,
        {some_engagement_positive_expr} AS engagement_positive,
        {some_engagement_negative_expr} AS engagement_negative,
        {some_engagement_neutral_expr} AS engagement_neutral
      FROM {_table('amazon_2026_some')} AS s
      LEFT JOIN publisher_seed AS seed
        ON LOWER(COALESCE(NULLIF(TRIM(CAST(s.publisher_display AS STRING)), ''), NULLIF(TRIM(s.Author), ''), 'Unknown')) = seed.display_key
    ),
    some_engagement_agg AS (
      SELECT
        publisher_uid,
        SUM(engagement_positive) AS some_engagement_positive,
        SUM(engagement_negative) AS some_engagement_negative,
        SUM(engagement_neutral) AS some_engagement_neutral
      FROM some_engagement_sentiment
      GROUP BY publisher_uid
    )
    SELECT
      COALESCE(NULLIF(TRIM(p.publisher_uid), ''), TO_HEX(MD5(LOWER(COALESCE(NULLIF(TRIM(p.display_name), ''), 'Unknown'))))) AS publisher_uid,
      COALESCE(NULLIF(TRIM(p.display_name), ''), NULLIF(TRIM(p.publisher_uid), ''), 'Unknown') AS display_name,
      COALESCE(p.total_items, COALESCE(p.trad_article_count, 0) + COALESCE(p.some_post_count, 0)) AS total_items,
      COALESCE(p.trad_article_count, 0) AS trad_article_count,
      COALESCE(p.trad_total_reach, 0) AS trad_total_reach,
      COALESCE(p.trad_positive_pct, 0) AS trad_positive_pct,
      COALESCE(p.trad_negative_pct, 0) AS trad_negative_pct,
      COALESCE(p.some_post_count, 0) AS some_post_count,
      COALESCE(p.some_total_reach, 0) AS some_total_reach,
      COALESCE(p.some_total_engagement, 0) AS some_total_engagement,
      COALESCE(p.some_avg_engagement, 0) AS some_avg_engagement,
      COALESCE(p.some_positive_pct, 0) AS some_positive_pct,
      COALESCE(p.some_negative_pct, 0) AS some_negative_pct,
      CASE
        WHEN LOWER(TRIM(COALESCE({trad_is_tml_expr}, ''))) IN ('true', 'treu', 'tml', 'yes', '1') THEN 'TML'
        WHEN LOWER(TRIM(COALESCE({trad_is_tml_expr}, ''))) IN ('false', 'non-tml', 'non tml', 'no', '0') THEN 'non-TML'
        ELSE ''
      END AS tml_values,
      COALESCE(NULLIF(TRIM({trad_media_type_expr}), ''), '') AS media_types,
      COALESCE(NULLIF({trad_dominant_media_type_expr}, ''), NULLIF(TRIM({trad_media_type_expr}), ''), 'Unknown') AS trad_dominant_media_type,
      COALESCE(NULLIF({some_dominant_platform_expr}, ''), 'Unknown') AS some_dominant_platform,
      CASE
        WHEN COALESCE(p.trad_article_count, 0) > 0 AND COALESCE(p.some_post_count, 0) > 0 THEN 'Trad+SoMe'
        WHEN COALESCE(p.trad_article_count, 0) > 0 THEN 'Trad'
        WHEN COALESCE(p.some_post_count, 0) > 0 THEN 'SoMe'
        ELSE 'Unknown'
      END AS publisher_type,
      COALESCE(NULLIF({publisher_platforms_expr}, 'null'), '') AS platforms_url,
      COALESCE(NULLIF({publisher_website_expr}, 'null'), '') AS website_url,
      COALESCE(NULLIF({profile_expr}, ''), NULLIF({analysis_expr}, ''), NULLIF({some_bio_expr}, ''), '') AS profile_description,
      COALESCE(p.combined_top_narratives, '') AS combined_top_narratives,
      COALESCE(NULLIF({trad_top_narratives_expr}, 'null'), '') AS trad_top_narratives,
      COALESCE(NULLIF({some_top_narratives_expr}, 'null'), '') AS some_top_narratives,
      COALESCE(e.some_engagement_positive, 0) AS some_engagement_positive,
      COALESCE(e.some_engagement_negative, 0) AS some_engagement_negative,
      COALESCE(e.some_engagement_neutral, 0) AS some_engagement_neutral
    FROM {_table('amazon_2026_publishers')} AS p
    LEFT JOIN some_engagement_agg AS e ON e.publisher_uid = p.publisher_uid
    ORDER BY total_items DESC, display_name
    """
    return safe_query(sql, fallback=_publishers_fixture())


def load_publisher_trad_timeline() -> pd.DataFrame:
    sql = f"""
    WITH {PUBLISHER_SEED_CTE},
    base AS (
      SELECT
        DATE_TRUNC(DATE(Published_At), WEEK(MONDAY)) AS week_start,
        COALESCE(NULLIF(TRIM(Publisher), ''), 'Unknown') AS display_name,
        {_sentiment_case('Sentiment')} AS sentiment,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')}
      WHERE Published_At IS NOT NULL
      GROUP BY week_start, display_name, sentiment
    ),
    keyed AS (
      SELECT
        COALESCE(p.publisher_uid, TO_HEX(MD5(LOWER(base.display_name)))) AS publisher_uid,
        base.display_name,
        CAST(base.week_start AS STRING) AS week_start,
        base.sentiment,
        base.publications,
        base.reach
      FROM base
      LEFT JOIN publisher_seed AS p
        ON LOWER(base.display_name) = p.display_key
    )
    SELECT publisher_uid, display_name, week_start, sentiment,
           'publications' AS base_metric, publications AS metric_value
    FROM keyed
    UNION ALL
    SELECT publisher_uid, display_name, week_start, sentiment,
           'reach' AS base_metric, reach AS metric_value
    FROM keyed
    ORDER BY display_name, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_publisher_trad_timeline_fixture())


def load_publisher_some_timeline() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    some_sentiment_expr = _optional_string_expr("s", some_columns, SOME_SENTIMENT_CANDIDATES)
    sql = f"""
    WITH {PUBLISHER_SEED_CTE},
    base AS (
      SELECT
        DATE_TRUNC(DATE(Published_At), WEEK(MONDAY)) AS week_start,
        NULLIF(TRIM(CAST(publisher_uid AS STRING)), '') AS source_publisher_uid,
        COALESCE(NULLIF(TRIM(CAST(publisher_display AS STRING)), ''), NULLIF(TRIM(Author), ''), 'Unknown') AS display_name,
        {_sentiment_case(some_sentiment_expr)} AS sentiment,
        COUNT(*) AS posts,
        SUM(COALESCE(Engagement, 0)) AS engagement
      FROM {_table('amazon_2026_some')} AS s
      WHERE Published_At IS NOT NULL
      GROUP BY week_start, source_publisher_uid, display_name, sentiment
    ),
    keyed AS (
      SELECT
        COALESCE(base.source_publisher_uid, p.publisher_uid, TO_HEX(MD5(LOWER(base.display_name)))) AS publisher_uid,
        base.display_name,
        CAST(base.week_start AS STRING) AS week_start,
        base.sentiment,
        base.posts,
        base.engagement
      FROM base
      LEFT JOIN publisher_seed AS p
        ON LOWER(base.display_name) = p.display_key
    )
    SELECT publisher_uid, display_name, week_start, sentiment,
           'posts' AS base_metric, posts AS metric_value
    FROM keyed
    UNION ALL
    SELECT publisher_uid, display_name, week_start, sentiment,
           'engagement' AS base_metric, engagement AS metric_value
    FROM keyed
    ORDER BY display_name, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_publisher_some_timeline_fixture())


def load_publisher_topic_areas() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic Area", "topic_area"])

    sql = f"""
    WITH {PUBLISHER_SEED_CTE}
    SELECT
      COALESCE(
        NULLIF(TRIM(CAST(t.publisher_uid AS STRING)), ''),
        p.publisher_uid,
        TO_HEX(MD5(LOWER(COALESCE(NULLIF(TRIM(CAST(t.publisher_display AS STRING)), ''), NULLIF(TRIM(t.Publisher), ''), 'Unknown'))))
      ) AS publisher_uid,
      COALESCE(NULLIF(TRIM({topic_area_expr}), ''), 'Unknown') AS topic_area,
      COUNT(*) AS publication_count
    FROM {_table('amazon_2026_trad')} AS t
    LEFT JOIN publisher_seed AS p
      ON LOWER(COALESCE(NULLIF(TRIM(CAST(t.publisher_display AS STRING)), ''), NULLIF(TRIM(t.Publisher), ''), 'Unknown')) = p.display_key
    GROUP BY 1, 2
    ORDER BY publication_count DESC, topic_area
    """
    return safe_query(sql, fallback=_publisher_topic_areas_fixture())


def load_publisher_some_topic_areas() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    topic_area_expr = _optional_string_expr("s", some_columns, ["Topic Area", "topic_area"])

    sql = f"""
    WITH {PUBLISHER_SEED_CTE}
    SELECT
      COALESCE(
        NULLIF(TRIM(CAST(s.publisher_uid AS STRING)), ''),
        p.publisher_uid,
        TO_HEX(MD5(LOWER(COALESCE(NULLIF(TRIM(CAST(s.publisher_display AS STRING)), ''), NULLIF(TRIM(s.Author), ''), 'Unknown'))))
      ) AS publisher_uid,
      COALESCE(NULLIF(TRIM({topic_area_expr}), ''), 'Unknown') AS topic_area,
      COUNT(*) AS post_count
    FROM {_table('amazon_2026_some')} AS s
    LEFT JOIN publisher_seed AS p
      ON LOWER(COALESCE(NULLIF(TRIM(CAST(s.publisher_display AS STRING)), ''), NULLIF(TRIM(s.Author), ''), 'Unknown')) = p.display_key
    GROUP BY 1, 2
    ORDER BY post_count DESC, topic_area
    """
    return safe_query(sql, fallback=_publisher_some_topic_areas_fixture())


def load_publisher_top_publications() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_pub_uid_expr = _optional_string_expr("t", trad_columns, ["publisher_uid"])
    trad_pub_display_expr = _optional_string_expr("t", trad_columns, PUBLISHER_DISPLAY_CANDIDATES)
    trad_summary_expr = _coalesce_string_expr("t", trad_columns, TRAD_SUMMARY_CANDIDATES)
    some_pub_uid_expr = _optional_string_expr("s", some_columns, ["publisher_uid"])
    some_pub_display_expr = _optional_string_expr("s", some_columns, PUBLISHER_DISPLAY_CANDIDATES)
    some_sentiment_expr = _optional_string_expr("s", some_columns, SOME_SENTIMENT_CANDIDATES)
    some_content_expr = _coalesce_string_expr("s", some_columns, SOME_CONTENT_CANDIDATES)

    sql = f"""
    WITH {PUBLISHER_SEED_CTE},
    trad_pubs AS (
      SELECT
        COALESCE(
          {trad_pub_uid_expr},
          p.publisher_uid,
          TO_HEX(MD5(LOWER(COALESCE({trad_pub_display_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown'))))
        ) AS publisher_uid,
        CAST(DATE(t.Published_At) AS STRING) AS Date,
        'Trad' AS Source,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS Type,
        COALESCE(NULLIF(TRIM(t.Title), ''), '(untitled)') AS Title,
        COALESCE({trad_summary_expr}, '') AS Summary,
        COALESCE(NULLIF(TRIM(t.URL), ''), '') AS URL,
        {_sentiment_case('t.Sentiment')} AS Sentiment,
        CAST(COALESCE(t.Reach, 0) AS INT64) AS Reach,
        CAST(NULL AS INT64) AS Engagement
      FROM {_table('amazon_2026_trad')} AS t
      LEFT JOIN publisher_seed AS p
        ON LOWER(COALESCE({trad_pub_display_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown')) = p.display_key
      WHERE t.Published_At IS NOT NULL
    ),
    some_pubs AS (
      SELECT
        COALESCE(
          {some_pub_uid_expr},
          p.publisher_uid,
          TO_HEX(MD5(LOWER(COALESCE({some_pub_display_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown'))))
        ) AS publisher_uid,
        CAST(DATE(s.Published_At) AS STRING) AS Date,
        'SoMe' AS Source,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS Type,
        '' AS Title,
        COALESCE({some_content_expr}, '') AS Summary,
        COALESCE(NULLIF(TRIM(s.URL), ''), '') AS URL,
        {_sentiment_case(some_sentiment_expr)} AS Sentiment,
        CAST(COALESCE(s.Reach, 0) AS INT64) AS Reach,
        COALESCE(s.Engagement, 0) AS Engagement
      FROM {_table('amazon_2026_some')} AS s
      LEFT JOIN publisher_seed AS p
        ON LOWER(COALESCE({some_pub_display_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown')) = p.display_key
      WHERE s.Published_At IS NOT NULL
    ),
    combined AS (
      SELECT publisher_uid, Date, Source, Type, Title, Summary, URL, Sentiment, Reach, Engagement
      FROM trad_pubs
      UNION ALL
      SELECT publisher_uid, Date, Source, Type, Title, Summary, URL, Sentiment, Reach, Engagement
      FROM some_pubs
    )
    SELECT publisher_uid, Date, Source, Type, Title, Summary, URL, Sentiment, Reach, Engagement
    FROM (
      SELECT *,
        ROW_NUMBER() OVER (
          PARTITION BY publisher_uid, Source
          ORDER BY COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
        ) AS rn
      FROM combined
    )
    WHERE rn <= 50
    ORDER BY publisher_uid, Source, COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
    """
    return safe_query(sql, fallback=_publisher_top_publications_fixture())
