"""
Lightweight recorders for the admin audit log and usage analytics.

Both helpers are deliberately fail-soft: recording an event must never break
the request that triggered it, so any storage error is swallowed and logged.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from tenancy.models import AuditEvent, UsageEvent

logger = logging.getLogger(__name__)

# Usage events are written on every dashboard page navigation; recording them
# off-thread keeps the Firestore round-trip off the request's critical path.
_usage_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="usage-event")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit(action: str, target: str = "", detail: str = "", actor=None) -> None:
    """Record an admin-relevant action by ``actor`` (defaults to the current user).

    Pass ``actor`` explicitly when the effective ``current_user()`` isn't the
    real one performing the action — e.g. an admin impersonating someone else
    who switches "view as" targets directly should still be attributed to
    themselves, not the user they were impersonating a moment ago.
    """
    try:
        from tenancy.users import get_user_store

        if actor is None:
            from auth.middleware import current_user

            actor = current_user()
        user = actor
        get_user_store().add_audit_event(
            AuditEvent(
                actor_uid=getattr(user, "uid", "") or "",
                actor_email=getattr(user, "email", "") or "system",
                action=action,
                target=target,
                detail=detail,
                created_at=_now(),
            )
        )
    except Exception:  # never let auditing break the actual operation
        logger.exception("Failed to record audit event action=%s target=%s", action, target)


def record_usage(user, slug: str) -> None:
    """Record that ``user`` opened the dashboard ``slug``.

    Fire-and-forget: the write happens on a background thread so a page
    navigation never waits on the usage-store round-trip.
    """
    _usage_executor.submit(_record_usage_now, user, slug)


def _record_usage_now(user, slug: str) -> None:
    try:
        from tenancy.users import get_user_store

        get_user_store().add_usage_event(
            UsageEvent(
                uid=getattr(user, "uid", "") or "",
                email=getattr(user, "email", "") or "",
                slug=slug,
                created_at=_now(),
            )
        )
    except Exception:
        logger.exception("Failed to record usage event slug=%s", slug)
