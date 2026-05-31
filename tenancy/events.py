"""
Lightweight recorders for the admin audit log and usage analytics.

Both helpers are deliberately fail-soft: recording an event must never break
the request that triggered it, so any storage error is swallowed and logged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from tenancy.models import AuditEvent, UsageEvent

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit(action: str, target: str = "", detail: str = "") -> None:
    """Record an admin-relevant action by the current user."""
    try:
        from auth.middleware import current_user
        from tenancy.users import get_user_store

        user = current_user()
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
    """Record that ``user`` opened the dashboard ``slug``."""
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
