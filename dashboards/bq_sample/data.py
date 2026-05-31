"""
Data loader for the BigQuery disinformation-timeline dashboard.

Demonstrates the BigQuery integration + the per-request data pattern:

* Registered with Vizro's ``data_manager`` as *dynamic data*, so the function
  runs at render time (inside the Flask request context). This is the hook
  where real per-client dataset scoping would call
  ``tenancy.access.resolve_client_dataset(current_user())`` to pick the dataset.
* Falls back to a local fixture when BigQuery is unreachable, keeping offline
  dev and CI green.
"""

from __future__ import annotations

import logging

import pandas as pd

from config import settings
from dashboards._base import DataSourceHealth
from data_sources.bq import safe_query, table_ref
from data_sources.fixtures import disinformation_timeline_fixture

logger = logging.getLogger(__name__)

DATA_KEY = "bq_disinformation_timeline"


def _fixture() -> pd.DataFrame:
    df = disinformation_timeline_fixture()
    return df.sort_values(["day", "stage"]).reset_index(drop=True)


def _resolve_dataset() -> str:
    """Pick the BigQuery dataset for the *current* user's client.

    Per-tenant isolation: a client user's data lives in their own dataset
    (``resolve_client_dataset``). Admins / dev (no client) fall back to the
    configured default dataset. Resolved per request so two clients never share
    a dataset.

    IMPORTANT: this relies on Vizro's ``data_manager`` NOT caching this source
    across users (the default is no caching). Do not enable a shared cache for
    ``DATA_KEY`` without keying it by ``client_id`` — doing so would leak one
    tenant's rows to another.
    """
    try:
        from auth.middleware import current_user
        from tenancy.access import resolve_client_dataset

        user = current_user()
        if user is not None:
            dataset = resolve_client_dataset(user)
            if dataset:
                return dataset
    except Exception as exc:  # outside request context, or store unavailable
        logger.debug("Falling back to default dataset: %s", exc)
    return settings.bq_sample_dataset


def load_disinformation_timeline() -> pd.DataFrame:
    """Daily publication counts per disinformation-lifecycle stage.

    Queries ``{bq_sample_project}.{<client dataset>}.{bq_sample_table}``,
    falling back to a local fixture when BigQuery is unreachable (dev only).
    """
    ref = table_ref(
        _resolve_dataset(),
        settings.bq_sample_table,
        project=settings.bq_sample_project,
    )
    sql = f"""
        SELECT
            day,
            stage,
            number_of_publications
        FROM {ref}
        WHERE day IS NOT NULL AND stage IS NOT NULL
        ORDER BY day, stage
    """
    return safe_query(sql, fallback=_fixture())


def data_health() -> list[DataSourceHealth]:
    """Probe the BigQuery source for the admin data-health page.

    Tries a live query; on success reports row count + latest day. If BigQuery
    is unreachable it reports a *degraded* status and falls back to the fixture
    so the page still shows useful numbers.
    """
    name = f"bigquery:{settings.bq_sample_dataset}.{settings.bq_sample_table}"
    ref = table_ref(
        _resolve_dataset(),
        settings.bq_sample_table,
        project=settings.bq_sample_project,
    )
    try:
        from data_sources.bq import run_query

        df = run_query(f"SELECT day, stage, number_of_publications FROM {ref}")
        as_of = str(df["day"].max()) if not df.empty else ""
        return [
            DataSourceHealth(
                name=name, status="ok", detail="Live from BigQuery.", rows=len(df), as_of=as_of
            )
        ]
    except Exception as exc:
        df = _fixture()
        as_of = str(df["day"].max()) if not df.empty else ""
        return [
            DataSourceHealth(
                name=name,
                status="degraded",
                detail=f"BigQuery unavailable — using offline fixture ({type(exc).__name__}).",
                rows=len(df),
                as_of=as_of,
            )
        ]


