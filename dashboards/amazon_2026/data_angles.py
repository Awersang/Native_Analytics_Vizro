from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import _optional_string_expr, _table, _table_column_map
from dashboards.amazon_2026.fixtures import _angles_fixture
from data_sources.bq import safe_query


def load_angles() -> pd.DataFrame:
    angle_columns = _table_column_map("amazon_2026_angles")
    trad_columns = _table_column_map("amazon_2026_trad")
    some_columns = _table_column_map("amazon_2026_some")
    angle_id_expr = _optional_string_expr("a", angle_columns, ["angle_id", "id"])
    trad_angle_id_expr = _optional_string_expr("t", trad_columns, ["dominant_angle_id", "angle_id"])
    some_angle_id_expr = _optional_string_expr("s", some_columns, ["dominant_angle_id", "angle_id"])
    trad_angle_expr = _optional_string_expr("t", trad_columns, ["dominant_angle_label"])
    some_angle_expr = _optional_string_expr("s", some_columns, ["dominant_angle_label"])

    sql = f"""
    WITH
    trad_angle_id_counts AS (
      SELECT
        {trad_angle_id_expr} AS angle_id,
        COUNT(*) AS trad_count
      FROM {_table('amazon_2026_trad')} AS t
      WHERE {trad_angle_id_expr} IS NOT NULL
      GROUP BY 1
    ),
    trad_angle_label_counts AS (
      SELECT
        {trad_angle_expr} AS angle_label,
        COUNT(*) AS trad_count
      FROM {_table('amazon_2026_trad')} AS t
      WHERE {trad_angle_expr} IS NOT NULL
      GROUP BY 1
    ),
    some_angle_id_counts AS (
      SELECT
        {some_angle_id_expr} AS angle_id,
        COUNT(*) AS some_count
      FROM {_table('amazon_2026_some')} AS s
      WHERE {some_angle_id_expr} IS NOT NULL
      GROUP BY 1
    ),
    some_angle_label_counts AS (
      SELECT
        {some_angle_expr} AS angle_label,
        COUNT(*) AS some_count
      FROM {_table('amazon_2026_some')} AS s
      WHERE {some_angle_expr} IS NOT NULL
      GROUP BY 1
    )
    SELECT
      a.narrative_id,
      COALESCE(NULLIF(n.narrative_label, ''), a.narrative_id) AS narrative_label,
      {angle_id_expr} AS angle_id,
      a.angle_label,
      a.target_sentiment,
      a.article_count AS publications,
      COALESCE(tic.trad_count, tlc.trad_count, 0) AS trad_publications,
      COALESCE(sic.some_count, slc.some_count, 0) AS some_posts,
      a.reach,
      a.popularity
    FROM {_table('amazon_2026_angles')} AS a
    LEFT JOIN {_table('amazon_2026_narratives')} AS n
      ON a.narrative_id = n.narrative_id
    LEFT JOIN trad_angle_id_counts AS tic
      ON {angle_id_expr} IS NOT NULL
      AND LOWER(TRIM({angle_id_expr})) = LOWER(TRIM(tic.angle_id))
    LEFT JOIN trad_angle_label_counts AS tlc
      ON LOWER(TRIM(a.angle_label)) = LOWER(TRIM(tlc.angle_label))
    LEFT JOIN some_angle_id_counts AS sic
      ON {angle_id_expr} IS NOT NULL
      AND LOWER(TRIM({angle_id_expr})) = LOWER(TRIM(sic.angle_id))
    LEFT JOIN some_angle_label_counts AS slc
      ON LOWER(TRIM(a.angle_label)) = LOWER(TRIM(slc.angle_label))
    ORDER BY a.narrative_id, a.popularity DESC
    """
    return safe_query(sql, fallback=_angles_fixture())
