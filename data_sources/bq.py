"""
BigQuery access helpers.

Design goals:
  * Per-client data isolation — queries are scoped to a client's dataset.
  * Lazy import of ``google.cloud.bigquery`` so dev without GCP still works.
  * A graceful local fallback: when credentials are unavailable (typical in
    local dev), ``safe_query`` returns a fixture DataFrame instead of crashing.
"""

from __future__ import annotations

import logging
from functools import lru_cache

import pandas as pd

from config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_bq_client():
    """Return a cached BigQuery client (raises if the library/creds missing)."""
    from google.cloud import bigquery  # lazy import

    return bigquery.Client(project=settings.gcp_project_id or None)


def run_query(sql: str) -> pd.DataFrame:
    """Execute a SQL query and return a DataFrame. Raises on any failure."""
    client = get_bq_client()
    return client.query(sql).to_dataframe()


def safe_query(sql: str, fallback: pd.DataFrame | None = None) -> pd.DataFrame:
    """Run a query, returning ``fallback`` only in development.

    In dev (``settings.is_dev``) a missing-credentials / library error falls
    back to fixture data so local work stays friction-free. In staging/prod we
    re-raise instead: serving fabricated numbers as if they were real client
    data would be worse than a visible error.
    """
    try:
        return run_query(sql)
    except Exception as exc:  # network/credentials dependent
        if fallback is not None and settings.is_dev:
            logger.warning("BigQuery query failed in dev; using fixture fallback: %s", exc)
            return fallback
        logger.error("BigQuery query failed: %s", exc)
        raise



def table_ref(dataset: str, table: str, project: str | None = None) -> str:
    """Build a fully-qualified `project.dataset.table` reference."""
    proj = project or settings.gcp_project_id
    return f"`{proj}.{dataset}.{table}`" if proj else f"`{dataset}.{table}`"
