"""
Access resolution: which dashboards may a given user open?

This is the single source of truth used by both the landing page (to list
cards) and the request gate (to allow/deny ``/app/d/<slug>`` routes).
"""

from __future__ import annotations

from config import settings
from tenancy.models import User


def resolve_client_dataset(user: User) -> str:
    """Return the BigQuery dataset name that scopes this user's data.

    Convention: f"{bq_dataset_prefix}{client_id}" unless the client record
    overrides ``bq_dataset`` explicitly.
    """
    from tenancy.users import get_user_store

    if not user.client_id:
        return ""
    client = get_user_store().get_client(user.client_id)
    if client and client.bq_dataset:
        return client.bq_dataset
    return f"{settings.bq_dataset_prefix}{user.client_id}"


def accessible_slugs(user: User, all_slugs: list[str]) -> list[str]:
    """Slugs the user may open, preserving registry order.

    Access is company-first: a user inherits every dashboard assigned to their
    company. Any per-user ``dashboard_slugs`` are honoured as *extra* grants on
    top of the company set. Admins always see everything.
    """
    if user.is_admin:
        return list(all_slugs)
    allowed = set(company_slugs(user)) | set(user.dashboard_slugs)
    return [s for s in all_slugs if s in allowed]


def company_slugs(user: User) -> list[str]:
    """Dashboards assigned to the user's company (empty if none/unknown)."""
    if not user.client_id:
        return []
    from tenancy.users import get_user_store

    client = get_user_store().get_client(user.client_id)
    return list(client.dashboard_slugs) if client else []


def can_access(user: User, slug: str) -> bool:
    """Whether ``user`` may open dashboard ``slug`` (store-aware)."""
    if user.is_admin:
        return True
    return slug in company_slugs(user) or slug in user.dashboard_slugs

