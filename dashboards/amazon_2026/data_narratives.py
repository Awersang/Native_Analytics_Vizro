from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import NON_CAMPAIGN_VALUES, PAID_VALUES, _coalesce_string_expr, _optional_string_expr, _sentiment_case, _table, _table_column_map, _weekly_grid_cte
from dashboards.amazon_2026.fixtures import (
    _narrative_detail_kpi_fixture,
    _narrative_overview_fixture,
    _narrative_some_platform_timeline_fixture,
    _narrative_some_sentiment_timeline_fixture,
    _narrative_some_weekly_engagement_fixture,
    _narrative_top_journalists_fixture,
    _narrative_top_publications_fixture,
    _narrative_top_publishers_fixture,
    _narrative_trad_media_type_timeline_fixture,
    _narrative_trad_sentiment_timeline_fixture,
    _narrative_weekly_reach_fixture,
    _narratives_fixture,
    _narratives_kpi_fixture,
)
from data_sources.bq import safe_query


def _narrative_col_expr(alias: str, columns: dict[str, str]) -> str:
    """Return a SQL expression for the narrative label column, preferring dominant_narrative."""
    name = columns.get("dominant_narrative", "")
    if name:
        return f"{alias}.`{name}`"
    return _optional_string_expr(alias, columns, ["dominant_narrative", "narrative_label"])


def load_narratives() -> pd.DataFrame:
    sql = f"""
    SELECT
      narrative_id,
      narrative_label,
      `rows` AS row_count,
      total_mentions,
      avg_popularity,
      share_of_positive_items_trad_some AS positive_pct,
      share_of_neutral_items_trad_some AS neutral_pct,
      share_of_negative_items_trad_some AS negative_pct,
      campaign_pct,
      paid_pct,
      first_seen,
      last_seen,
      description,
      takeaway_1,
      takeaway_2,
      takeaway_3
    FROM {_table('amazon_2026_narratives')}
    ORDER BY total_mentions DESC
    """
    return safe_query(sql, fallback=_narratives_fixture())


def load_narrative_overview() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")
    trad_label_expr = _optional_string_expr("t", trad_columns, ["narrative_label"])
    some_label_expr = _optional_string_expr("s", some_columns, ["narrative_label"])
    some_sentiment_expr = _optional_string_expr("s", some_columns, ["Sentiment"])

    sql = f"""
    WITH trad_base AS (
      SELECT
        NULLIF(TRIM({trad_label_expr}), '') AS narrative_label,
        COUNT(*) AS trad_publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS trad_reach,
        SUM(CASE WHEN LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'pos%'
                 THEN CAST(COALESCE(t.Reach, 0) AS INT64) ELSE 0 END) AS trad_positive_reach,
        SUM(CASE WHEN LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'neg%'
                 THEN CAST(COALESCE(t.Reach, 0) AS INT64) ELSE 0 END) AS trad_negative_reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE NULLIF(TRIM({trad_label_expr}), '') IS NOT NULL
      GROUP BY 1
    ),
    some_base AS (
      SELECT
        NULLIF(TRIM({some_label_expr}), '') AS narrative_label,
        COUNT(*) AS some_posts,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS some_reach,
        SUM(COALESCE(s.Engagement, 0)) AS some_engagement,
        SUM(CASE WHEN LOWER(TRIM(COALESCE({some_sentiment_expr}, ''))) LIKE 'pos%'
                 THEN CAST(COALESCE(s.Reach, 0) AS INT64) ELSE 0 END) AS some_positive_reach,
        SUM(CASE WHEN LOWER(TRIM(COALESCE({some_sentiment_expr}, ''))) LIKE 'neg%'
                 THEN CAST(COALESCE(s.Reach, 0) AS INT64) ELSE 0 END) AS some_negative_reach
      FROM {_table('amazon_2026_some')} AS s
      WHERE NULLIF(TRIM({some_label_expr}), '') IS NOT NULL
      GROUP BY 1
    )
    SELECT
      COALESCE(t.narrative_label, s.narrative_label) AS narrative_label,
      COALESCE(t.trad_publications, 0) AS trad_publications,
      COALESCE(t.trad_reach, 0) AS trad_reach,
      CASE WHEN COALESCE(t.trad_reach, 0) > 0
           THEN COALESCE(t.trad_positive_reach, 0) / CAST(t.trad_reach AS FLOAT64) ELSE 0
      END AS trad_positive_share_of_reach,
      CASE WHEN COALESCE(t.trad_reach, 0) > 0
           THEN COALESCE(t.trad_negative_reach, 0) / CAST(t.trad_reach AS FLOAT64) ELSE 0
      END AS trad_negative_share_of_reach,
      COALESCE(s.some_posts, 0) AS some_posts,
      COALESCE(s.some_reach, 0) AS some_reach,
      COALESCE(s.some_engagement, 0) AS some_engagement,
      CASE WHEN COALESCE(s.some_posts, 0) > 0
           THEN COALESCE(s.some_engagement, 0) / CAST(s.some_posts AS FLOAT64) ELSE 0
      END AS some_average_engagement,
      CASE WHEN COALESCE(s.some_reach, 0) > 0
           THEN COALESCE(s.some_positive_reach, 0) / CAST(s.some_reach AS FLOAT64) ELSE 0
      END AS some_positive_share_of_reach,
      CASE WHEN COALESCE(s.some_reach, 0) > 0
           THEN COALESCE(s.some_negative_reach, 0) / CAST(s.some_reach AS FLOAT64) ELSE 0
      END AS some_negative_share_of_reach
    FROM trad_base AS t
    FULL OUTER JOIN some_base AS s ON t.narrative_label = s.narrative_label
    WHERE LOWER(TRIM(COALESCE(t.narrative_label, s.narrative_label))) NOT IN ('noise', 'unknown')
    ORDER BY (COALESCE(t.trad_reach, 0) + COALESCE(s.some_reach, 0)) DESC,
             COALESCE(t.narrative_label, s.narrative_label)
    """
    return safe_query(sql, fallback=_narrative_overview_fixture())


def load_narrative_weekly_reach() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    narrative_col = _narrative_col_expr("t", trad_columns)
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS dominant_narrative,
          CAST(COALESCE(t.Reach, 0) AS INT64) AS reach
        FROM {_table('amazon_2026_trad')} AS t
        WHERE t.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("dominant_narrative", "narratives", "LOWER(dominant_narrative) NOT IN ('noise', 'unknown')")}
    SELECT
        g.week_start,
        g.dominant_narrative,
        COALESCE(SUM(a.reach), 0) AS weekly_reach,
        COUNT(a.reach) AS weekly_publications
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start
      AND g.dominant_narrative = a.dominant_narrative
    GROUP BY g.week_start, g.dominant_narrative
    ORDER BY g.week_start, g.dominant_narrative
    """
    return safe_query(sql, fallback=_narrative_weekly_reach_fixture())


def load_narrative_some_weekly_engagement() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    narrative_col = _narrative_col_expr("s", some_columns)
    sql = f"""
    WITH all_weekly AS (
        SELECT
          CAST(DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
          NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS dominant_narrative,
          COALESCE(s.Engagement, 0) AS engagement
        FROM {_table('amazon_2026_some')} AS s
        WHERE s.Published_At IS NOT NULL
    ),
    {_weekly_grid_cte("dominant_narrative", "narratives", "LOWER(dominant_narrative) NOT IN ('noise', 'unknown')")}
    SELECT
        g.week_start,
        g.dominant_narrative,
        COALESCE(SUM(a.engagement), 0) AS weekly_engagement,
        COUNT(a.engagement) AS weekly_posts
    FROM grid g
    LEFT JOIN all_weekly a
      ON g.week_start = a.week_start
      AND g.dominant_narrative = a.dominant_narrative
    GROUP BY g.week_start, g.dominant_narrative
    ORDER BY g.week_start, g.dominant_narrative
    """
    return safe_query(sql, fallback=_narrative_some_weekly_engagement_fixture())


def load_narrative_trad_sentiment_timeline() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    narrative_col = _narrative_col_expr("t", trad_columns)
    sql = f"""
    WITH base AS (
      SELECT
        DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS week_start,
        NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS narrative_label,
        {_sentiment_case('t.Sentiment')} AS sentiment,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE t.Published_At IS NOT NULL
      GROUP BY week_start, narrative_label, sentiment
    )
    SELECT narrative_label, CAST(week_start AS STRING) AS week_start, sentiment,
           'publications' AS base_metric, publications AS metric_value
    FROM base
    WHERE narrative_label IS NOT NULL AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
    UNION ALL
    SELECT narrative_label, CAST(week_start AS STRING) AS week_start, sentiment,
           'reach' AS base_metric, reach AS metric_value
    FROM base
    WHERE narrative_label IS NOT NULL AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
    ORDER BY narrative_label, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_narrative_trad_sentiment_timeline_fixture())


def load_narrative_some_sentiment_timeline() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    narrative_col = _narrative_col_expr("s", some_columns)
    some_sentiment_expr = _optional_string_expr("s", some_columns, ["Sentiment"])
    sql = f"""
    WITH base AS (
      SELECT
        DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS week_start,
        NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS narrative_label,
        {_sentiment_case(some_sentiment_expr)} AS sentiment,
        COUNT(*) AS posts,
        SUM(COALESCE(s.Engagement, 0)) AS engagement
      FROM {_table('amazon_2026_some')} AS s
      WHERE s.Published_At IS NOT NULL
      GROUP BY week_start, narrative_label, sentiment
    )
    SELECT narrative_label, CAST(week_start AS STRING) AS week_start, sentiment,
           'posts' AS base_metric, posts AS metric_value
    FROM base
    WHERE narrative_label IS NOT NULL AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
    UNION ALL
    SELECT narrative_label, CAST(week_start AS STRING) AS week_start, sentiment,
           'engagement' AS base_metric, engagement AS metric_value
    FROM base
    WHERE narrative_label IS NOT NULL AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
    ORDER BY narrative_label, week_start, sentiment, base_metric
    """
    return safe_query(sql, fallback=_narrative_some_sentiment_timeline_fixture())


def load_narrative_trad_media_type_timeline() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    narrative_col = _narrative_col_expr("t", trad_columns)
    sql = f"""
    SELECT
      NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS narrative_label,
      CAST(DATE_TRUNC(DATE(t.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
      COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS media_type,
      COUNT(*) AS publications
    FROM {_table('amazon_2026_trad')} AS t
    WHERE t.Published_At IS NOT NULL
      AND NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') IS NOT NULL
      AND LOWER(NULLIF(TRIM(CAST({narrative_col} AS STRING)), '')) NOT IN ('noise', 'unknown')
    GROUP BY narrative_label, week_start, media_type
    ORDER BY narrative_label, week_start, media_type
    """
    return safe_query(sql, fallback=_narrative_trad_media_type_timeline_fixture())


def load_narrative_some_platform_timeline() -> pd.DataFrame:
    some_columns = _table_column_map("amazon_2026_some")
    narrative_col = _narrative_col_expr("s", some_columns)
    sql = f"""
    SELECT
      NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') AS narrative_label,
      CAST(DATE_TRUNC(DATE(s.Published_At), WEEK(MONDAY)) AS STRING) AS week_start,
      COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS platform,
      COUNT(*) AS posts
    FROM {_table('amazon_2026_some')} AS s
    WHERE s.Published_At IS NOT NULL
      AND NULLIF(TRIM(CAST({narrative_col} AS STRING)), '') IS NOT NULL
      AND LOWER(NULLIF(TRIM(CAST({narrative_col} AS STRING)), '')) NOT IN ('noise', 'unknown')
    GROUP BY narrative_label, week_start, platform
    ORDER BY narrative_label, week_start, platform
    """
    return safe_query(sql, fallback=_narrative_some_platform_timeline_fixture())


def load_narratives_kpi() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_narr_expr = _optional_string_expr("t", trad_columns, ["narrative_label", "dominant_narrative"])
    some_narr_expr = _optional_string_expr("s", some_columns, ["narrative_label", "dominant_narrative"])
    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    trad_paid_expr = _optional_string_expr(
        "t", trad_columns, ["paid", "Paid", "paid_earned", "Paid_Earned", "content_type", "Content_Type"]
    )
    some_paid_expr = _optional_string_expr(
        "s", some_columns, ["paid", "Paid", "paid_earned", "Paid_Earned", "content_type", "Content_Type"]
    )

    # One base scan per source — all metrics derived from these two CTEs.
    sql = f"""
    WITH
    narr_totals AS (
      SELECT COUNT(*) AS total_narratives
      FROM {_table('amazon_2026_narratives')}
      WHERE LOWER(TRIM(COALESCE(narrative_label, ''))) NOT IN ('noise', 'unknown', '')
    ),
    angle_totals AS (
      SELECT COUNT(*) AS total_angles
      FROM {_table('amazon_2026_angles')}
    ),
    trad_raw AS (
      SELECT
        NULLIF(TRIM(CAST({trad_narr_expr} AS STRING)), '') AS narr_label,
        {trad_campaign_expr} AS camp,
        {trad_paid_expr} AS paid
      FROM {_table('amazon_2026_trad')} AS t
    ),
    trad_agg AS (
      SELECT
        COUNT(*) AS total_pubs,
        COUNTIF(narr_label IS NOT NULL AND LOWER(narr_label) NOT IN ('noise', 'unknown')) AS pubs_in_narrative,
        COUNTIF(camp IS NOT NULL AND TRIM(LOWER(CAST(camp AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}) AS campaign_pubs,
        COUNTIF(LOWER(TRIM(CAST(paid AS STRING))) IN {PAID_VALUES}) AS paid_pubs
      FROM trad_raw
    ),
    some_raw AS (
      SELECT
        NULLIF(TRIM(CAST({some_narr_expr} AS STRING)), '') AS narr_label,
        {some_campaign_expr} AS camp,
        {some_paid_expr} AS paid
      FROM {_table('amazon_2026_some')} AS s
    ),
    some_agg AS (
      SELECT
        COUNT(*) AS total_posts,
        COUNTIF(narr_label IS NOT NULL AND LOWER(narr_label) NOT IN ('noise', 'unknown')) AS posts_in_narrative,
        COUNTIF(camp IS NOT NULL AND TRIM(LOWER(CAST(camp AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}) AS campaign_posts,
        COUNTIF(LOWER(TRIM(CAST(paid AS STRING))) IN {PAID_VALUES}) AS paid_posts
      FROM some_raw
    ),
    trad_by_narr AS (
      SELECT narr_label AS narrative_label, COUNT(*) AS trad_pubs
      FROM trad_raw
      WHERE narr_label IS NOT NULL AND LOWER(narr_label) NOT IN ('noise', 'unknown')
      GROUP BY narr_label
    ),
    some_by_narr AS (
      SELECT narr_label AS narrative_label, COUNT(*) AS some_posts
      FROM some_raw
      WHERE narr_label IS NOT NULL AND LOWER(narr_label) NOT IN ('noise', 'unknown')
      GROUP BY narr_label
    ),
    narrative_combined AS (
      SELECT
        COALESCE(s.narrative_label, t.narrative_label) AS narrative_label,
        COALESCE(s.some_posts, 0) AS some_posts,
        COALESCE(t.trad_pubs, 0) AS trad_pubs,
        COALESCE(s.some_posts, 0) + COALESCE(t.trad_pubs, 0) AS total_items
      FROM some_by_narr s
      FULL OUTER JOIN trad_by_narr t ON LOWER(s.narrative_label) = LOWER(t.narrative_label)
    ),
    top_some_heavy AS (
      SELECT narrative_label FROM narrative_combined ORDER BY some_posts DESC LIMIT 1
    ),
    top_some_dominant AS (
      SELECT narrative_label
      FROM narrative_combined
      WHERE total_items > 0
      ORDER BY SAFE_DIVIDE(some_posts, total_items) DESC
      LIMIT 1
    )
    SELECT
      n.total_narratives,
      a.total_angles,
      tn.pubs_in_narrative,
      tn.total_pubs,
      sn.posts_in_narrative,
      sn.total_posts,
      tn.campaign_pubs + sn.campaign_posts AS campaign_items,
      tn.total_pubs + sn.total_posts AS total_items_campaign,
      tn.paid_pubs + sn.paid_posts AS paid_items,
      th.narrative_label AS top_some_heavy_narrative,
      td.narrative_label AS top_some_dominant_narrative
    FROM narr_totals n
    CROSS JOIN angle_totals a
    CROSS JOIN trad_agg tn
    CROSS JOIN some_agg sn
    CROSS JOIN top_some_heavy th
    CROSS JOIN top_some_dominant td
    """
    return safe_query(sql, fallback=_narratives_kpi_fixture())


def load_narrative_detail_kpis() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_narr_expr = _optional_string_expr("t", trad_columns, ["narrative_label", "dominant_narrative"])
    some_narr_expr = _optional_string_expr("s", some_columns, ["narrative_label", "dominant_narrative"])
    trad_campaign_expr = _optional_string_expr(
        "t", trad_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    some_campaign_expr = _optional_string_expr(
        "s", some_columns, ["campaign_announcement", "Campaign_Announcement", "campaign"]
    )
    trad_paid_expr = _optional_string_expr(
        "t", trad_columns, ["paid", "Paid", "paid_earned", "Paid_Earned", "content_type", "Content_Type"]
    )
    some_paid_expr = _optional_string_expr(
        "s", some_columns, ["paid", "Paid", "paid_earned", "Paid_Earned", "content_type", "Content_Type"]
    )

    sql = f"""
    WITH
    trad_raw AS (
      SELECT
        NULLIF(TRIM(CAST({trad_narr_expr} AS STRING)), '') AS narrative_label,
        {trad_campaign_expr} AS camp,
        {trad_paid_expr} AS paid
      FROM {_table('amazon_2026_trad')} AS t
    ),
    some_raw AS (
      SELECT
        NULLIF(TRIM(CAST({some_narr_expr} AS STRING)), '') AS narrative_label,
        COALESCE(s.Engagement, 0) AS engagement,
        {some_campaign_expr} AS camp,
        {some_paid_expr} AS paid
      FROM {_table('amazon_2026_some')} AS s
    ),
    trad_by_narr AS (
      SELECT
        narrative_label,
        COUNT(*) AS trad_publications,
        COUNTIF(
          camp IS NOT NULL
          AND TRIM(LOWER(CAST(camp AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
        ) AS trad_campaign_items,
        COUNTIF(
          LOWER(TRIM(CAST(paid AS STRING))) IN {PAID_VALUES}
        ) AS trad_paid_items
      FROM trad_raw
      WHERE narrative_label IS NOT NULL
        AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
      GROUP BY 1
    ),
    some_by_narr AS (
      SELECT
        narrative_label,
        COUNT(*) AS some_posts,
        SUM(engagement) AS some_engagement,
        COUNTIF(
          camp IS NOT NULL
          AND TRIM(LOWER(CAST(camp AS STRING))) NOT IN {NON_CAMPAIGN_VALUES}
        ) AS some_campaign_items,
        COUNTIF(
          LOWER(TRIM(CAST(paid AS STRING))) IN {PAID_VALUES}
        ) AS some_paid_items
      FROM some_raw
      WHERE narrative_label IS NOT NULL
        AND LOWER(narrative_label) NOT IN ('noise', 'unknown')
      GROUP BY 1
    )
    SELECT
      COALESCE(t.narrative_label, s.narrative_label) AS narrative_label,
      COALESCE(t.trad_publications, 0) AS trad_publications,
      COALESCE(s.some_posts, 0) AS some_posts,
      COALESCE(s.some_engagement, 0) AS some_engagement,
      COALESCE(t.trad_campaign_items, 0) + COALESCE(s.some_campaign_items, 0) AS campaign_items,
      COALESCE(t.trad_publications, 0) + COALESCE(s.some_posts, 0) AS total_items,
      COALESCE(t.trad_paid_items, 0) + COALESCE(s.some_paid_items, 0) AS paid_items
    FROM trad_by_narr t
    FULL OUTER JOIN some_by_narr s ON LOWER(t.narrative_label) = LOWER(s.narrative_label)
    ORDER BY COALESCE(t.trad_publications, 0) + COALESCE(s.some_posts, 0) DESC
    """
    return safe_query(sql, fallback=_narrative_detail_kpi_fixture())


def load_narrative_top_publishers() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_label_expr = _optional_string_expr("t", trad_columns, ["narrative_label"])
    some_label_expr = _optional_string_expr("s", some_columns, ["narrative_label"])
    trad_pub_expr = _optional_string_expr("t", trad_columns, ["publisher_display", "Publisher_Display"])
    some_pub_expr = _optional_string_expr("s", some_columns, ["publisher_display", "Publisher_Display"])

    sql = f"""
    WITH trad_base AS (
      SELECT
        NULLIF(TRIM({trad_label_expr}), '') AS narrative_label,
        COALESCE({trad_pub_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_trad')} AS t
      WHERE NULLIF(TRIM({trad_label_expr}), '') IS NOT NULL
      GROUP BY 1, 2, 3
    ),
    some_base AS (
      SELECT
        NULLIF(TRIM({some_label_expr}), '') AS narrative_label,
        COALESCE({some_pub_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown') AS publisher,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS media_type_platform,
        SUM(CAST(COALESCE(s.Reach, 0) AS INT64)) AS reach,
        COUNT(*) AS publications
      FROM {_table('amazon_2026_some')} AS s
      WHERE NULLIF(TRIM({some_label_expr}), '') IS NOT NULL
      GROUP BY 1, 2, 3
    )
    SELECT 'Trad' AS source, narrative_label, publisher, media_type_platform, reach, publications
    FROM trad_base
    WHERE LOWER(narrative_label) NOT IN ('noise', 'unknown')
    UNION ALL
    SELECT 'SoMe' AS source, narrative_label, publisher, media_type_platform, reach, publications
    FROM some_base
    WHERE LOWER(narrative_label) NOT IN ('noise', 'unknown')
    ORDER BY narrative_label, source, reach DESC
    """
    return safe_query(sql, fallback=_narrative_top_publishers_fixture())


def load_narrative_top_journalists() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    trad_label_expr = _optional_string_expr("t", trad_columns, ["narrative_label"])
    journalist_expr = _optional_string_expr("t", trad_columns, ["Journalist", "Byline", "Author"])

    sql = f"""
    WITH journalist_base AS (
      SELECT
        NULLIF(TRIM({trad_label_expr}), '') AS narrative_label,
        COALESCE(NULLIF(TRIM({journalist_expr}), ''), 'Unknown') AS journalist,
        COUNT(*) AS publications,
        SUM(CAST(COALESCE(t.Reach, 0) AS INT64)) AS reach
      FROM {_table('amazon_2026_trad')} AS t
      WHERE NULLIF(TRIM({trad_label_expr}), '') IS NOT NULL
        AND LOWER(TRIM({trad_label_expr})) NOT IN ('noise', 'unknown')
      GROUP BY 1, 2
    )
    SELECT narrative_label, journalist, publications, reach
    FROM journalist_base
    WHERE LOWER(journalist) NOT IN ('unknown', 'brak', 'brak danych', 'n/a', 'na', 'none', '-')
    ORDER BY narrative_label, reach DESC
    """
    return safe_query(sql, fallback=_narrative_top_journalists_fixture())


def load_narrative_top_publications() -> pd.DataFrame:
    angle_columns = _table_column_map("amazon_2026_angles")
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    angle_id_expr = _optional_string_expr("a", angle_columns, ["angle_id", "id"])
    trad_label_expr = _optional_string_expr("t", trad_columns, ["narrative_label"])
    some_label_expr = _optional_string_expr("s", some_columns, ["narrative_label"])
    trad_summary_expr = _coalesce_string_expr("t", trad_columns, ["Description", "_3P_Description", "Main_Text", "Summary"])
    some_sentiment_expr = _optional_string_expr("s", some_columns, ["Sentiment"])
    some_content_expr = _coalesce_string_expr("s", some_columns, ["Main_Text", "Description", "_3P_Description"])
    trad_angle_id_expr = _optional_string_expr("t", trad_columns, ["dominant_angle_id", "angle_id"])
    some_angle_id_expr = _optional_string_expr("s", some_columns, ["dominant_angle_id", "angle_id"])
    trad_angle_expr = _optional_string_expr("t", trad_columns, ["dominant_angle_label"])
    some_angle_expr = _optional_string_expr("s", some_columns, ["dominant_angle_label"])

    sql = f"""
    WITH angle_lookup AS (
      SELECT
        COALESCE(NULLIF(n.narrative_label, ''), a.narrative_id) AS narrative_label,
        a.angle_label,
        {angle_id_expr} AS angle_id
      FROM {_table('amazon_2026_angles')} AS a
      LEFT JOIN {_table('amazon_2026_narratives')} AS n
        ON a.narrative_id = n.narrative_id
    ),
    trad_pubs AS (
      SELECT
        NULLIF(TRIM({trad_label_expr}), '') AS narrative_label,
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
        COALESCE({trad_angle_id_expr}, '') AS Angle_ID,
        COALESCE({trad_angle_expr}, '') AS Angle
      FROM {_table('amazon_2026_trad')} AS t
      WHERE t.Published_At IS NOT NULL
        AND NULLIF(TRIM({trad_label_expr}), '') IS NOT NULL
        AND LOWER(TRIM({trad_label_expr})) NOT IN ('noise', 'unknown')
    ),
    some_pubs AS (
      SELECT
        NULLIF(TRIM({some_label_expr}), '') AS narrative_label,
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
        COALESCE({some_angle_id_expr}, '') AS Angle_ID,
        COALESCE({some_angle_expr}, '') AS Angle
      FROM {_table('amazon_2026_some')} AS s
      WHERE s.Published_At IS NOT NULL
        AND NULLIF(TRIM({some_label_expr}), '') IS NOT NULL
        AND LOWER(TRIM({some_label_expr})) NOT IN ('noise', 'unknown')
    ),
    combined AS (
      SELECT * FROM trad_pubs
      UNION ALL
      SELECT * FROM some_pubs
    )
    SELECT
      c.narrative_label,
      c.Date,
      c.Source,
      c.Type,
      c.Publication,
      c.Author,
      c.Title,
      c.Summary,
      c.URL,
      c.Sentiment,
      c.Reach,
      c.Engagement,
      COALESCE(NULLIF(c.Angle_ID, ''), al.angle_id, '') AS Angle_ID,
      c.Angle
    FROM combined AS c
    LEFT JOIN angle_lookup AS al
      ON LOWER(TRIM(c.narrative_label)) = LOWER(TRIM(al.narrative_label))
      AND LOWER(TRIM(c.Angle)) = LOWER(TRIM(al.angle_label))
    ORDER BY c.narrative_label, c.Source, COALESCE(c.Reach, 0) DESC, COALESCE(c.Engagement, 0) DESC
    """
    return safe_query(sql, fallback=_narrative_top_publications_fixture())
