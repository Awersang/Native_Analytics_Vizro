from __future__ import annotations

import pandas as pd

from dashboards.amazon_2026.data_common import _table
from dashboards.amazon_2026.fixtures import _archive_scatter_fixture
from data_sources.bq import safe_query


def load_archive_scatter() -> pd.DataFrame:
    sql = f"""
    SELECT umap_x, umap_y, narrative_label, 'Trad' AS source
    FROM {_table('amazon_2026_trad')}
    WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
    UNION ALL
    SELECT umap_x, umap_y, narrative_label, 'SoMe' AS source
    FROM {_table('amazon_2026_some')}
    WHERE umap_x IS NOT NULL AND umap_y IS NOT NULL
    """
    return safe_query(sql, fallback=_archive_scatter_fixture())
