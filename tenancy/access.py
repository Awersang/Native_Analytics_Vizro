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

    if not user.is_company_user or not user.client_id:
        return ""
    client = get_user_store().get_client(user.client_id)
    if client and client.bq_dataset:
        return client.bq_dataset
    return f"{settings.bq_dataset_prefix}{user.client_id}"


def operator_slugs(user: User) -> set[str]:
    """Dashboards an operator may open: the union of every allowed client's
    dashboards - the same company-inherits-dashboards model as a regular
    user, just applied across multiple clients instead of one."""
    from tenancy.users import get_user_store

    store = get_user_store()
    allowed: set[str] = set()
    for client_id in user.allowed_client_ids:
        client = store.get_client(client_id)
        if client:
            allowed.update(client.dashboard_slugs)
    return allowed


def accessible_slugs(user: User, all_slugs: list[str]) -> list[str]:
    """Slugs the user may open, preserving registry order."""
    if user.is_admin:
        return list(all_slugs)
    if user.is_operator:
        allowed = operator_slugs(user)
        return [s for s in all_slugs if s in allowed]

    company = set(company_slugs(user))
    restricted = set(user.restricted_dashboard_slugs) & company
    allowed = company - restricted
    return [s for s in all_slugs if s in allowed]


def company_slugs(user: User) -> list[str]:
    """Dashboards assigned to the user's company (empty if none/unknown)."""
    if not user.is_company_user or not user.client_id:
        return []
    from tenancy.users import get_user_store

    client = get_user_store().get_client(user.client_id)
    return list(client.dashboard_slugs) if client else []


def can_access(user: User, slug: str) -> bool:
    """Whether ``user`` may open dashboard ``slug`` (store-aware)."""
    if user.is_admin:
        return True
    if user.is_operator:
        return slug in operator_slugs(user)
    return slug in set(company_slugs(user)) - set(user.restricted_dashboard_slugs)


def dashboard_owner_map() -> dict[str, str]:
    """Return the owning client id for each dashboard slug.

    Ownership is derived from ``Client.dashboard_slugs`` and is intentionally
    single-owner: if duplicate assignments exist in storage, the first one wins
    here and the admin UI can be used to repair the data.
    """
    from tenancy.users import get_user_store

    owners: dict[str, str] = {}
    for client in get_user_store().list_clients():
        for slug in client.dashboard_slugs:
            owners.setdefault(slug, client.id)
    return owners


def dashboard_owner_client_id(slug: str) -> str:
    return dashboard_owner_map().get(slug, "")
