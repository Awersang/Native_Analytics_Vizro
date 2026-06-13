from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import _table
from dashboards.amazon_2026.fixtures import _angles_fixture
from data_sources.bq import safe_query


def load_angles() -> pd.DataFrame:
    sql = f"""
    SELECT
      a.narrative_id,
      COALESCE(NULLIF(n.narrative_label, ''), a.narrative_id) AS narrative_label,
      a.angle_label,
      a.target_sentiment,
      a.article_count AS publications,
      a.reach,
      a.popularity
    FROM {_table('amazon_2026_angles')} AS a
    LEFT JOIN {_table('amazon_2026_narratives')} AS n
      ON a.narrative_id = n.narrative_id
    ORDER BY a.narrative_id, a.popularity DESC
    """
    return safe_query(sql, fallback=_angles_fixture())
