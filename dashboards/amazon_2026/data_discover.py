from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import (
    _coalesce_string_expr,
    _optional_numeric_expr,
    _optional_string_expr,
    _sentiment_case,
    _table,
    _table_column_map,
)

PUBLISHER_LOOKUP_CTE = """publisher_lookup AS (
      SELECT
        publisher_uid,
        ANY_VALUE(NULLIF(TRIM(display_name), '')) AS display_name
      FROM {table}
      GROUP BY publisher_uid
    )"""
from dashboards.amazon_2026.fixtures import _discover_items_fixture
from data_sources.bq import safe_query


def load_discover_items() -> pd.DataFrame:
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")

    trad_summary_expr = _coalesce_string_expr("t", trad_columns, ["Description", "_3P_Description", "Main_Text", "Summary"])
    trad_full_text_expr = _coalesce_string_expr(
        "t", trad_columns, ["Main_Text", "Body", "Article_Text", "Content", "Full_Text", "Description", "_3P_Description", "Summary"]
    )
    trad_topic_area_expr = _optional_string_expr("t", trad_columns, ["Topic_Area"])
    trad_narrative_expr = _optional_string_expr("t", trad_columns, ["narrative_label", "dominant_narrative"])
    trad_journalist_expr = _optional_string_expr("t", trad_columns, ["Journalist", "Byline", "Author"])

    some_content_expr = _coalesce_string_expr("s", some_columns, ["Main_Text", "Description", "_3P_Description"])
    some_topic_area_expr = _optional_string_expr("s", some_columns, ["Topic_Area"])
    some_narrative_expr = _optional_string_expr("s", some_columns, ["narrative_label", "dominant_narrative"])
    some_engagement_positive_expr = _optional_numeric_expr("s", some_columns, ["engagement_positive"])
    some_engagement_negative_expr = _optional_numeric_expr("s", some_columns, ["engagement_negative"])
    some_engagement_neutral_expr = _optional_numeric_expr("s", some_columns, ["engagement_neutral"])
    some_followers_expr = _optional_numeric_expr("s", some_columns, ["Followers", "followers", "follower_count"])

    trad_uid_expr = _optional_string_expr("t", trad_columns, ["publisher_uid"])
    trad_display_expr = _optional_string_expr("t", trad_columns, ["publisher_display"])
    some_uid_expr = _optional_string_expr("s", some_columns, ["publisher_uid"])
    some_display_expr = _optional_string_expr("s", some_columns, ["publisher_display"])

    publisher_lookup_cte = PUBLISHER_LOOKUP_CTE.format(table=_table("amazon_2026_publishers"))

    sql = f"""
    WITH {publisher_lookup_cte},
    trad_items AS (
      SELECT
        CAST(DATE(t.Published_At) AS STRING) AS Date,
        'Trad' AS Source,
        {_sentiment_case('t.Sentiment')} AS Sentiment,
        COALESCE(pl.display_name, {trad_display_expr}, NULLIF(TRIM(t.Publisher), ''), 'Unknown') AS Publisher,
        COALESCE({trad_topic_area_expr}, '') AS Topic_Area,
        COALESCE({trad_narrative_expr}, '') AS Narrative,
        COALESCE(NULLIF(TRIM(t.Media_Type), ''), 'Unknown') AS Media_Type,
        COALESCE(NULLIF(TRIM(t.Title), ''), '(untitled)') AS Title,
        COALESCE({trad_summary_expr}, '') AS Summary,
        COALESCE(NULLIF(TRIM(t.URL), ''), '') AS URL,
        CAST(COALESCE(t.Reach, 0) AS INT64) AS Reach,
        CAST(0 AS INT64) AS Engagement,
        CAST(0 AS INT64) AS Engagement_Positive,
        CAST(0 AS INT64) AS Engagement_Negative,
        CAST(0 AS INT64) AS Engagement_Neutral,
        CAST(0 AS INT64) AS Followers,
        COALESCE({trad_journalist_expr}, '') AS Journalist,
        COALESCE({trad_full_text_expr}, '') AS Full_Text,
        t.umap_x AS umap_x,
        t.umap_y AS umap_y
      FROM {_table('amazon_2026_trad')} AS t
      LEFT JOIN publisher_lookup AS pl
        ON pl.publisher_uid = COALESCE({trad_uid_expr}, NULLIF(TRIM(t.Publisher), ''))
      WHERE t.Published_At IS NOT NULL
    ),
    some_items AS (
      SELECT
        CAST(DATE(s.Published_At) AS STRING) AS Date,
        'SoMe' AS Source,
        {_sentiment_case('s.Sentiment')} AS Sentiment,
        COALESCE(pl.display_name, {some_display_expr}, NULLIF(TRIM(s.Author), ''), 'Unknown') AS Publisher,
        COALESCE({some_topic_area_expr}, '') AS Topic_Area,
        COALESCE({some_narrative_expr}, '') AS Narrative,
        COALESCE(NULLIF(TRIM(s.Platform), ''), 'Unknown') AS Media_Type,
        COALESCE({some_content_expr}, '(no content)') AS Title,
        '' AS Summary,
        COALESCE(NULLIF(TRIM(s.URL), ''), '') AS URL,
        CAST(COALESCE(s.Reach, 0) AS INT64) AS Reach,
        CAST(COALESCE(s.Engagement, 0) AS INT64) AS Engagement,
        CAST(COALESCE({some_engagement_positive_expr}, 0) AS INT64) AS Engagement_Positive,
        CAST(COALESCE({some_engagement_negative_expr}, 0) AS INT64) AS Engagement_Negative,
        CAST(COALESCE({some_engagement_neutral_expr}, 0) AS INT64) AS Engagement_Neutral,
        CAST(COALESCE({some_followers_expr}, 0) AS INT64) AS Followers,
        '' AS Journalist,
        COALESCE({some_content_expr}, '') AS Full_Text,
        s.umap_x AS umap_x,
        s.umap_y AS umap_y
      FROM {_table('amazon_2026_some')} AS s
      LEFT JOIN publisher_lookup AS pl
        ON pl.publisher_uid = COALESCE({some_uid_expr}, NULLIF(TRIM(s.Author), ''))
      WHERE s.Published_At IS NOT NULL
    )
    SELECT * FROM trad_items
    UNION ALL
    SELECT * FROM some_items
    ORDER BY Date DESC
    """
    return safe_query(sql, fallback=_discover_items_fixture())
