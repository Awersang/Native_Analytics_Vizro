from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import NON_CAMPAIGN_VALUES, _coalesce_string_expr, _optional_string_expr, _sentiment_case, _table, _table_column_map, _weekly_grid_cte
from dashboards.amazon_2026.fixtures import (
    _campaign_narratives_fixture,
    _campaign_profile_fixture,
    _campaign_some_sentiment_timeline_fixture,
    _campaign_some_weekly_engagement_fixture,
    _campaign_timeline_fixture,
    _campaign_top_journalists_fixture,
    _campaign_top_publications_fixture,
    _campaign_top_publishers_fixture,
    _campaign_trad_sentiment_timeline_fixture,
    _campaign_weekly_reach_fixture,
)
from data_sources.bq import safe_query


def load_campaign_timeline() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )

    sql = f"""
    WITH trad_campaign AS (
      SELECT
        {trad_campaign_expr} AS campaign,
        DATE(t.Published_At) AS pub_date,
        CAST(COALESCE(t.Reach, 0) AS INT64) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE t.Published_At IS NOT NULL
    ),
    some_campaign AS (
      SELECT
        {some_campaign_expr} AS campaign,
        DATE(s.Published_At) AS pub_date,
        CAST(COALESCE(s.Reach, 0) AS INT64) AS reach
      FROM {_table('amazon_2026_some')} AS s
      WHERE s.Published_At IS NOT NULL
    ),
    combined AS (
      SELECT campaign, pub_date, reach, 'trad' AS source FROM trad_campaign
      UNION ALL
      SELECT campaign, pub_date, reach, 'some' AS source FROM some_campaign
    )
    SELECT
      campaign,
      MIN(pub_date) AS start_date,
      MAX(pub_date) AS end_date,
      SUM(reach) AS total_reach,
      SUM(IF(source = 'trad', reach, 0)) AS trad_reach,
      SUM(IF(source = 'some', reach, 0)) AS some_reach,
      COUNT(*) AS items
    FROM combined
    WHERE campaign IS NOT NULL
      AND TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    GROUP BY campaign
    HAVING SUM(reach) >= 2000
    ORDER BY start_date, campaign
    """
    return safe_query(sql, fallback=_campaign_timeline_fixture())


def load_campaign_weekly_reach() -> pd.DataFrame:
    """Trad weekly reach + publication count, by campaign."""
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          {trad_campaign_expr} AS campaign,
          CAST(COALESCE(t.Reach, 0) AS INT64) AS reach
        FROM {_table('amazon_2026_trad')} AS t
        WHERE t.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("campaign", "campaigns", f"TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}")}
    SELECT
        g.week_start,
        g.campaign,
        COALESCE(SUM(a.reach), 0) AS weekly_reach,
        COUNT(a.reach) AS weekly_publications
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start AND g.campaign = a.campaign
    GROUP BY g.week_start, g.campaign
    ORDER BY g.week_start, g.campaign
    """
    return safe_query(sql, fallback=_campaign_weekly_reach_fixture())


def load_campaign_some_weekly_engagement() -> pd.DataFrame:
    """SoMe weekly engagement + post count, by campaign."""
    some_columns = _table_column_map("amazon_2026_some")
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          {some_campaign_expr} AS campaign,
          COALESCE(s.Engagement, 0) AS engagement
        FROM {_table('amazon_2026_some')} AS s
        WHERE s.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("campaign", "campaigns", f"TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}")}
    SELECT
        g.week_start,
        g.campaign,
        COALESCE(SUM(a.engagement), 0) AS weekly_engagement,
        COUNT(a.engagement) AS weekly_posts
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start AND g.campaign = a.campaign
    GROUP BY g.week_start, g.campaign
    ORDER BY g.week_start, g.campaign
    """
    return safe_query(sql, fallback=_campaign_some_weekly_engagement_fixture())


def load_campaign_trad_sentiment_timeline() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    sql = f"""
    WITH all_weekly AS (
        SELECT
          DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS week_start,
          {trad_campaign_expr} AS campaign,
          {_sentiment_case('t.Sentiment')} AS sentiment,
          CAST(COALESCE(t.Reach, 0) AS INT64) AS reach
        FROM {_table('amazon_2026_trad')} AS t
        WHERE t.Published_At IS NOT NULL
    ),
    all_campaigns AS (
        SELECT DISTINCT campaign
        FROM all_weekly
        WHERE campaign IS NOT NULL
          AND TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    ),
    all_weeks AS (
        SELECT DISTINCT week_start FROM all_weekly WHERE week_start IS NOT NULL
    ),
    all_sentiments AS (
        SELECT sentiment FROM UNNEST(['Positive', 'Neutral', 'Negative']) AS sentiment
    ),
    grid AS (
        SELECT w.week_start, c.campaign, s.sentiment
        FROM all_weeks w CROSS JOIN all_campaigns c CROSS JOIN all_sentiments s
    ),
    base AS (
        SELECT
            g.week_start, g.campaign, g.sentiment,
            COUNT(a.reach) AS publications,
            COALESCE(SUM(a.reach), 0) AS reach
        FROM grid g
        LEFT JOIN all_weekly a
          ON g.week_start = a.week_start AND g.campaign = a.campaign AND g.sentiment = a.sentiment
        GROUP BY g.week_start, g.campaign, g.sentiment
    )
    SELECT campaign, CAST(week_start AS STRING) AS week_start, sentiment,
           'publications' AS base_metric, publications AS metric_value
    FROM base
    UNION ALL
    SELECT campaign, CAST(week_start AS STRING) AS week_start, sentiment,
           'reach' AS base_metric, reach AS metric_value
    FROM base
    ORDER BY campaign, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_campaign_trad_sentiment_timeline_fixture())


def load_campaign_some_sentiment_timeline() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_sentiment_expr = _optional_string_expr("s", some_columns, ["Sentiment"])
    sql = f"""
    WITH all_weekly AS (
        SELECT
          DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS week_start,
          {some_campaign_expr} AS campaign,
          {_sentiment_case(some_sentiment_expr)} AS sentiment,
          COALESCE(s.Engagement, 0) AS engagement
        FROM {_table('amazon_2026_some')} AS s
        WHERE s.Published_At IS NOT NULL
    ),
    all_campaigns AS (
        SELECT DISTINCT campaign
        FROM all_weekly
        WHERE campaign IS NOT NULL
          AND TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    ),
    all_weeks AS (
        SELECT DISTINCT week_start FROM all_weekly WHERE week_start IS NOT NULL
    ),
    all_sentiments AS (
        SELECT sentiment FROM UNNEST(['Positive', 'Neutral', 'Negative']) AS sentiment
    ),
    grid AS (
        SELECT w.week_start, c.campaign, s.sentiment
        FROM all_weeks w CROSS JOIN all_campaigns c CROSS JOIN all_sentiments s
    ),
    base AS (
        SELECT
            g.week_start, g.campaign, g.sentiment,
            COUNT(a.engagement) AS posts,
            COALESCE(SUM(a.engagement), 0) AS engagement
        FROM grid g
        LEFT JOIN all_weekly a
          ON g.week_start = a.week_start AND g.campaign = a.campaign AND g.sentiment = a.sentiment
        GROUP BY g.week_start, g.campaign, g.sentiment
    )
    SELECT campaign, CAST(week_start AS STRING) AS week_start, sentiment,
           'posts' AS base_metric, posts AS metric_value
    FROM base
    UNION ALL
    SELECT campaign, CAST(week_start AS STRING) AS week_start, sentiment,
           'engagement' AS base_metric, engagement AS metric_value
    FROM base
    ORDER BY campaign, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_campaign_some_sentiment_timeline_fixture())


def load_campaign_top_publishers() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    trad_pub_expr = _optional_string_expr("t", trad_columns, ["publisher_display", "Publisher_Display"])
    some_pub_expr = _optional_string_expr("s", some_columns, ["publisher_display", "Publisher_Display"])

    sql = f"""
    WITH trad_base AS (
      SELECT
        {trad_campaign_expr} AS campaign,
        COALESCE({trad_pub_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_trad')} AS t
      WHERE {trad_campaign_expr} IS NOT NULL
      GROUP BY 1, 2, 3
    ),
    some_base AS (
      SELECT
        {some_campaign_expr} AS campaign,
        COALESCE({some_pub_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_some')} AS s
      WHERE {some_campaign_expr} IS NOT NULL
      GROUP BY 1, 2, 3
    )
    SELECT 'Trad' AS source, campaign, publisher, media_type_platform, reach, publications
    FROM trad_base
    WHERE TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    UNION ALL
    SELECT 'SoMe' AS source, campaign, publisher, media_type_platform, reach, publications
    FROM some_base
    WHERE TRIM(LOWER(CAST(campaign AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    ORDER BY campaign, source, reach DESC
    """
    return safe_query(sql, fallback=_campaign_top_publishers_fixture())


def load_campaign_top_journalists() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    journalist_expr = _optional_string_expr("t", trad_columns, ["Journalist", "Byline", "Author"])

    sql = f"""
    WITH journalist_base AS (
      SELECT
        {trad_campaign_expr} AS campaign,
        COALESCE(NULLIF(TRIM({journalist_expr}), ''), 'Unknown') AS journalist,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE {trad_campaign_expr} IS NOT NULL
        AND TRIM(LOWER(CAST({trad_campaign_expr} AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
      GROUP BY 1, 2
    )
    SELECT campaign, journalist, publications, reach
    FROM journalist_base
    WHERE LOWER(journalist) NOT IN ('unknown', 'brak', 'brak danych', 'n/a', 'na', 'none', '-')
    ORDER BY campaign, reach DESC
    """
    return safe_query(sql, fallback=_campaign_top_journalists_fixture())


def load_campaign_top_publications() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    trad_summary_expr = _coalesce_string_expr("t", trad_columns, ["Description", "_3P_Description", "Main_Text", "Summary"])
    some_sentiment_expr = _optional_string_expr("s", some_columns, ["Sentiment"])
    some_content_expr = _coalesce_string_expr("s", some_columns, ["Main_Text", "Description", "_3P_Description"])
    trad_angle_expr = _optional_string_expr("t", trad_columns, ["dominant_angle"])
    some_angle_expr = _optional_string_expr("s", some_columns, ["angle", "dominant_angle"])

    sql = f"""
    WITH trad_pubs AS (
      SELECT
        {trad_campaign_expr} AS campaign,
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
        AND {trad_campaign_expr} IS NOT NULL
        AND TRIM(LOWER(CAST({trad_campaign_expr} AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    ),
    some_pubs AS (
      SELECT
        {some_campaign_expr} AS campaign,
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
        AND {some_campaign_expr} IS NOT NULL
        AND TRIM(LOWER(CAST({some_campaign_expr} AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
    ),
    combined AS (
      SELECT * FROM trad_pubs
      UNION ALL
      SELECT * FROM some_pubs
    )
    SELECT campaign, Date, Source, Type, Publication, Author, Title, Summary, URL, Sentiment, Reach, Engagement, Angle
    FROM (
      SELECT *,
        ROW_NUMBER() OVER (
          PARTITION BY campaign, Source
          ORDER BY COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
        ) AS rn
      FROM combined
    )
    WHERE rn <= 50
    ORDER BY campaign, Source, COALESCE(Reach, 0) DESC, COALESCE(Engagement, 0) DESC
    """
    return safe_query(sql, fallback=_campaign_top_publications_fixture())


def load_campaign_profile() -> pd.DataFrame:
    """Campaign profile descriptions and key takeaways from the campaigns table."""
    sql = f"""
    SELECT
      campaign_name AS campaign,
      profile,
      takeaway_1,
      takeaway_2,
      takeaway_3
    FROM {_table('amazon_2026_campaigns')}
    """
    return safe_query(sql, fallback=_campaign_profile_fixture())


def load_campaign_narratives() -> pd.DataFrame:
    """Narratives associated with each campaign, from the campaign_narratives table."""
    sql = f"""
    SELECT
      c.campaign_name AS campaign,
      n.narrative_id,
      n.narrative_label,
      n.connection,
      n.rationale
    FROM {_table('amazon_2026_campaign_narratives')} AS n
    JOIN {_table('amazon_2026_campaigns')} AS c
      ON n.campaign_uid = c.campaign_uid
    ORDER BY c.campaign_name, n.narrative_id
    """
    return safe_query(sql, fallback=_campaign_narratives_fixture())
