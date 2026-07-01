"""
Admin panel: business-logic helpers (no HTTP routing, no HTML rendering).

Split out of admin/routes.py (alongside admin/views.py for the HTML-rendering
helpers) once that file grew past 1100 lines mixing routing, presentation,
and business logic — the same shape of split charts_shared.py got in the
amazon_2026 dashboard (theme.py / timeline_charts.py / ui_components.py).
Pure logic lives here so routes.py stays a thin list of view functions.
"""

from __future__ import annotations

import base64
import logging

from flask import request

from tenancy.models import Client, User
from tenancy.users import get_user_store

logger = logging.getLogger(__name__)

VALID_ROLES = {"user", "admin"}
# Placeholder uid for an admin-invited user who hasn't signed in yet. Claimed
# onto their real Firebase uid on first login (auth/middleware.py).
PENDING_PREFIX = "pending:"
# Logos ride inline as a data: URI in the Client Firestore doc (capped well
# under Firestore's 1MiB document limit) rather than needing a separate file
# store/bucket for what's expected to be a small per-client image.
_MAX_LOGO_BYTES = 150 * 1024


def is_pending(uid: str) -> bool:
    return uid.startswith(PENDING_PREFIX)


def send_invite(email: str) -> None:
    """Email a sign-in link to a newly-invited user. Best-effort: the admin
    can retry via "Resend invite" if this fails (e.g. dev has no real
    Firebase project), so a failure here must not block user creation."""
    from config import settings

    if not settings.auth_enabled:
        return
    try:
        from auth.firebase import send_signin_link_email

        send_signin_link_email(email, continue_url=f"{request.url_root}login")
    except Exception:
        logger.exception("Failed to send invite email to %s", email)


def registry():
    from dashboards import get_registry

    return get_registry()


def all_slugs() -> list[str]:
    return [d.manifest.slug for d in registry()]


def dashboard_options() -> list[tuple[str, str]]:
    return [(d.manifest.slug, d.manifest.title) for d in registry()]


def dashboard_titles() -> dict[str, str]:
    return dict(dashboard_options())


def clean_role(raw: str) -> str:
    role = (raw or "").strip().lower()
    return role if role in VALID_ROLES else "user"


def logo_data_uri_from_upload(file_storage) -> str:
    """Encode an uploaded image as a data: URI. Returns "" if nothing usable
    was uploaded (no file, wrong type, or over the size cap) - the caller
    then leaves the client's existing logo untouched."""
    if file_storage is None or not file_storage.filename:
        return ""
    raw = file_storage.read()
    if not raw or len(raw) > _MAX_LOGO_BYTES or not (file_storage.mimetype or "").startswith("image/"):
        return ""
    return f"data:{file_storage.mimetype};base64,{base64.b64encode(raw).decode('ascii')}"


def valid_client_id(raw: str) -> str:
    client_id = (raw or "").strip()
    if client_id and get_user_store().get_client(client_id) is None:
        return ""
    return client_id


def effective_company_dashboards(user: User, clients: dict[str, Client]) -> list[str]:
    if not user.is_company_user:
        return []
    client = clients.get(user.client_id)
    if client is None:
        return []
    company = list(client.dashboard_slugs)
    restricted = set(user.restricted_dashboard_slugs)
    return [slug for slug in company if slug not in restricted]


def sanitize_user_for_role(user: User) -> User:
    if user.is_admin:
        user.client_id = ""
        user.allowed_client_ids = []
        user.restricted_dashboard_slugs = []
    elif user.is_operator:
        user.client_id = ""
        user.restricted_dashboard_slugs = []
    else:
        user.allowed_client_ids = []
    return user


def assign_dashboard_owner(slug: str, client_id: str) -> None:
    store = get_user_store()
    if client_id:
        client = store.get_client(client_id)
        if client is None:
            return
        desired = list(client.dashboard_slugs)
        if slug not in desired:
            desired.append(slug)
        store.set_client_dashboards(client_id, desired)
        return

    for client in store.list_clients():
        if slug in client.dashboard_slugs:
            client.dashboard_slugs = [s for s in client.dashboard_slugs if s != slug]
            store.upsert_client(client)
