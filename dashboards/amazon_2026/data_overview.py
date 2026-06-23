from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import _metric_pivot, _optional_string_expr, _sentiment_case, _table, _table_column_map
from dashboards.amazon_2026.fixtures import (
    _media_type_period_fixture,
    _overview_fixture,
    _overview_kpi_fixture,
    _sentiment_source_monthly_fixture,
    _some_platform_fixture,
    _source_sentiment_monthly_fixture,
    _top_articles_fixture,
    _top_posts_fixture,
)
from data_sources.bq import safe_query


def _some_sentiment_expr(alias: str) -> str:
    some_columns = _table_column_map("amazon_2026_some")
    return _optional_string_expr(alias, some_columns, ["Sentiment"])


def load_tml_split() -> pd.DataFrame:
    sql = f"""
        WITH grouped AS (
            SELECT
                CASE
                    WHEN UPPER(TRIM(COALESCE(TML, ''))) = 'TML' THEN 'TML'
                    ELSE 'non-TML'
                END AS tml_group,
                COUNT(*) AS publications,
                SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS reach
            FROM {_table('amazon_2026_trad')}
            GROUP BY tml_group
        )
        {_metric_pivot('grouped', ['tml_group'])}
    """
    return safe_query(sql, fallback=_overview_fixture())


def load_media_type_period() -> pd.DataFrame:
    sql = f"""
        WITH base AS (
            SELECT
                COALESCE(NULLIF(TRIM(Media_Type), ''), 'Unknown') AS media_type,
                COUNT(*) AS publications,
                SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS reach
            FROM {_table('amazon_2026_trad')}
            GROUP BY media_type
        )
        {_metric_pivot('base', ['media_type'])}
    """
    return safe_query(sql, fallback=_media_type_period_fixture())


def load_sentiment_source_monthly() -> pd.DataFrame:
    sql = f"""
        WITH trad_base AS (
            SELECT
                EXTRACT(MONTH FROM Published_At) AS month_num,
                FORMAT_TIMESTAMP('%b', Published_At) AS month_label,
                COUNT(*) AS publications,
                SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS reach
            FROM {_table('amazon_2026_trad')}
            WHERE Published_At IS NOT NULL
            GROUP BY month_num, month_label
        ),
        social_base AS (
            SELECT
                EXTRACT(MONTH FROM Published_At) AS month_num,
                FORMAT_TIMESTAMP('%b', Published_At) AS month_label,
                COUNT(*) AS publications,
                SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS reach
            FROM {_table('amazon_2026_some')}
            WHERE Published_At IS NOT NULL
            GROUP BY month_num, month_label
        )
        SELECT month_num, month_label, 'Trad' AS source_group, 'publications' AS base_metric, publications AS metric_value
        FROM trad_base
        UNION ALL
        SELECT month_num, month_label, 'Some' AS source_group, 'publications' AS base_metric, publications AS metric_value
        FROM social_base
        UNION ALL
        SELECT month_num, month_label, 'Trad' AS source_group, 'reach' AS base_metric, reach AS metric_value
        FROM trad_base
        UNION ALL
        SELECT month_num, month_label, 'Some' AS source_group, 'reach' AS base_metric, reach AS metric_value
        FROM social_base
    """
    return safe_query(sql, fallback=_sentiment_source_monthly_fixture())


def load_source_sentiment_monthly() -> pd.DataFrame:
    some_sentiment_expr = _some_sentiment_expr("s")
    sql = f"""
        WITH trad_base AS (
            SELECT
                EXTRACT(MONTH FROM Published_At) AS month_num,
                FORMAT_TIMESTAMP('%b', Published_At) AS month_label,
                {_sentiment_case('Sentiment')} AS sentiment,
                COUNT(*) AS publications,
                SUM(COALESCE(CAST(Reach AS INT64), 0)) AS reach_val
            FROM {_table('amazon_2026_trad')}
            WHERE Published_At IS NOT NULL
            GROUP BY month_num, month_label, sentiment
        ),
        social_base AS (
            SELECT
                EXTRACT(MONTH FROM Published_At) AS month_num,
                FORMAT_TIMESTAMP('%b', Published_At) AS month_label,
                {_sentiment_case(some_sentiment_expr)} AS sentiment,
                COUNT(*) AS publications,
                SUM(COALESCE(Engagement, 0)) AS engagement_val,
                SUM(COALESCE(engagement_positive, 0)) AS positive_eng,
                SUM(COALESCE(engagement_neutral, 0)) AS neutral_eng,
                SUM(COALESCE(engagement_negative, 0)) AS negative_eng
            FROM {_table('amazon_2026_some')} AS s
            WHERE Published_At IS NOT NULL
            GROUP BY month_num, month_label, sentiment
        ),
        social_month AS (
            SELECT month_num, month_label,
                SUM(positive_eng) AS positive_val,
                SUM(neutral_eng) AS neutral_val,
                SUM(negative_eng) AS negative_val
            FROM social_base
            GROUP BY month_num, month_label
        ),
        engagement_sentiment AS (
            SELECT month_num, month_label, sentiment, metric_value
            FROM social_month,
            UNNEST([
                STRUCT('Positive' AS sentiment, positive_val AS metric_value),
                STRUCT('Neutral' AS sentiment, neutral_val AS metric_value),
                STRUCT('Negative' AS sentiment, negative_val AS metric_value)
            ])
        )
        SELECT month_num, month_label, 'Trad' AS source_group, sentiment,
               'publications' AS base_metric, publications AS metric_value
        FROM trad_base
        UNION ALL
        SELECT month_num, month_label, 'Some' AS source_group, sentiment,
               'publications' AS base_metric, publications AS metric_value
        FROM social_base
        UNION ALL
        SELECT month_num, month_label, 'Trad' AS source_group, sentiment,
               'reach' AS base_metric, reach_val AS metric_value
        FROM trad_base
        UNION ALL
        SELECT month_num, month_label, 'Some' AS source_group, sentiment,
               'reach' AS base_metric, engagement_val AS metric_value
        FROM social_base
        UNION ALL
        SELECT month_num, month_label, 'Engagement' AS source_group, sentiment,
               'publications' AS base_metric, metric_value
        FROM engagement_sentiment
        UNION ALL
        SELECT month_num, month_label, 'Engagement' AS source_group, sentiment,
               'reach' AS base_metric, metric_value
        FROM engagement_sentiment
    """
    return safe_query(sql, fallback=_source_sentiment_monthly_fixture())


def load_overview_kpis() -> pd.DataFrame:
    sql = f"""
        SELECT
            trad.total_publications,
            trad.total_reach,
            social.total_posts,
            social.total_engagement,
            pubs.trad_with_some
        FROM (
            SELECT
                COUNT(*) AS total_publications,
                SUM(CAST(COALESCE(Reach, 0) AS INT64)) AS total_reach
            FROM {_table('amazon_2026_trad')}
        ) trad
        CROSS JOIN (
            SELECT
                COUNT(*) AS total_posts,
                SUM(COALESCE(Engagement, 0)) AS total_engagement
            FROM {_table('amazon_2026_some')}
        ) social
        CROSS JOIN (
            SELECT
                COUNT(DISTINCT CASE WHEN trad_article_count > 0 AND some_post_count > 0 THEN publisher_uid END) AS trad_with_some
            FROM {_table('amazon_2026_publishers')}
        ) pubs
    """
    return safe_query(sql, fallback=_overview_kpi_fixture())


def load_some_platform() -> pd.DataFrame:
    sql = f"""
        WITH base AS (
            SELECT
                COALESCE(NULLIF(TRIM(Platform), ''), 'Unknown') AS platform,
                COUNT(*) AS posts,
                SUM(COALESCE(Engagement, 0)) AS engagement
            FROM {_table('amazon_2026_some')}
            GROUP BY platform
        )
        SELECT platform, 'publications' AS base_metric, posts AS metric_value FROM base
        UNION ALL
        SELECT platform, 'reach' AS base_metric, engagement AS metric_value FROM base
    """
    return safe_query(sql, fallback=_some_platform_fixture())


def load_top_items() -> pd.DataFrame:
    """Fetch top 250 trad articles and top 250 SoMe posts in one query.

    Returns a combined DataFrame with a 'Source' column ('Trad' or 'SoMe').
    Columns absent from one source are NULL. Eliminates the second data_manager
    call that overview_top_items_panel previously made inside the capture body.
    """
    some_sentiment_expr = _some_sentiment_expr("s")
    sql = f"""
        SELECT * FROM (
            SELECT
                'Trad' AS Source,
                CAST(DATE(Published_At) AS STRING) AS Date,
                COALESCE(NULLIF(TRIM(Media_Type), ''), 'Unknown') AS Media_Type,
                COALESCE(NULLIF(TRIM(Publisher), ''), '') AS Publication,
                COALESCE(NULLIF(TRIM(Title), ''), '(untitled)') AS Title,
                COALESCE(NULLIF(TRIM(Description), ''), NULLIF(TRIM(_3P_Description), ''), NULLIF(TRIM(Main_Text), ''), '') AS Summary,
                COALESCE(NULLIF(TRIM(URL), ''), '') AS URL,
                {_sentiment_case('Sentiment')} AS Sentiment,
                CAST(COALESCE(Reach, 0) AS INT64) AS Reach,
                CAST(COALESCE(Tier, 0) AS INT64) AS Tier,
                CAST(NULL AS STRING) AS Platform,
                CAST(NULL AS STRING) AS Author,
                CAST(NULL AS STRING) AS Post_Content,
                0 AS Engagement
            FROM {_table('amazon_2026_trad')}
            WHERE Published_At IS NOT NULL
            ORDER BY Reach DESC
            LIMIT 250
        )
        UNION ALL
        SELECT * FROM (
            SELECT
                'SoMe' AS Source,
                CAST(DATE(Published_At) AS STRING) AS Date,
                CAST(NULL AS STRING) AS Media_Type,
                CAST(NULL AS STRING) AS Publication,
                CAST(NULL AS STRING) AS Title,
                CAST(NULL AS STRING) AS Summary,
                COALESCE(NULLIF(TRIM(URL), ''), '') AS URL,
                {_sentiment_case(some_sentiment_expr)} AS Sentiment,
                CAST(COALESCE(Reach, 0) AS INT64) AS Reach,
                CAST(NULL AS INT64) AS Tier,
                COALESCE(NULLIF(TRIM(Platform), ''), 'Unknown') AS Platform,
                COALESCE(NULLIF(TRIM(Author), ''), '') AS Author,
                COALESCE(NULLIF(TRIM(Description), ''), NULLIF(TRIM(Main_Text), ''), '') AS Post_Content,
                COALESCE(Engagement, 0) AS Engagement
            FROM {_table('amazon_2026_some')} AS s
            WHERE Published_At IS NOT NULL
            ORDER BY Engagement DESC
            LIMIT 250
        )
    """
    arts = _top_articles_fixture()
    arts = arts.assign(
        Source="Trad",
        Platform=None,
        Author=None,
        Post_Content=None,
        Engagement=0,
    )
    posts = _top_posts_fixture()
    posts = posts.assign(
        Source="SoMe",
        Media_Type=None,
        Publication=None,
        Title=None,
        Summary=None,
        Tier=None,
    )
    fallback = pd.concat([arts, posts], ignore_index=True)
    return safe_query(sql, fallback=fallback)
