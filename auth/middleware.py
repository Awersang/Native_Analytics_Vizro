"""
Request-scoped authentication middleware.

Exposes:
  * ``current_user()``      → the ``User`` for this request (or None).
  * ``login_required``      → decorator; redirects to /login when unauthenticated.
  * ``admin_required``      → decorator; 403 for non-admins.
  * ``install_auth(server)``→ wires a before_request hook onto the Flask server.

When ``AUTH_ENABLED=false`` every request is treated as the fixture dev admin,
so the whole app is reachable with zero setup.
"""

from __future__ import annotations

import functools
import logging
from typing import Callable

from flask import Response, g, redirect, request

from auth.dev_users import DEV_ADMIN
from config import settings
from tenancy.models import User
from tenancy.users import get_user_store

logger = logging.getLogger(__name__)


_IMPERSONATE_COOKIE = "na_dev_as"


def _resolve_real_user() -> User | None:
    """Resolve the actually-authenticated principal, ignoring impersonation."""
    if not settings.auth_enabled:
        # Dev mode: the whole app is reachable as the fixture admin with zero
        # setup.
        return DEV_ADMIN

    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    try:
        from auth.firebase import verify_session_cookie

        claims = verify_session_cookie(cookie)
        store = get_user_store()
        uid = claims.get("uid") or claims.get("sub", "")
        email = (claims.get("email") or "").lower()
        user = store.get_user(uid)
        if user is None and email:
            # Admin-invited users are stored under a placeholder uid (pending
            # the first real login). Claim the record onto the real uid so
            # every later lookup goes straight through store.get_user(uid).
            user = store.get_user_by_email(email)
            if user is not None and user.uid != uid:
                store.reclaim_user(user.uid, uid)
                user.uid = uid
        if user is None and email:
            if settings.auto_provision_users:
                # Authenticated with Firebase but not yet provisioned: create a
                # zero-access record so an admin can grant dashboards later.
                user = User(uid=uid, email=email, role="user")
                store.upsert_user(user)
                logger.info("Auto-provisioned new user uid=%s email=%s", uid, email)
            else:
                # Deny until an admin explicitly creates the user.
                logger.warning("Authenticated but unprovisioned user denied: email=%s", email)
        return user
    except Exception:
        logger.exception("Session cookie verification failed")
        return None


def _load_user_from_request() -> User | None:
    """Resolve the effective acting User for this request, caching on flask.g.

    Distinguishes the *real* authenticated principal (``g.real_user``) from the
    *effective* one (``g.user``): an admin may impersonate another user via the
    "View as" switcher (cookie ``na_dev_as``) to see exactly what that user
    sees — in dev always (as the fixture admin) and in prod for real admins
    only. Impersonating another admin or a disabled account is refused.
    """
    if "user" in g:
        return g.user

    real = _resolve_real_user()
    if real is not None and real.disabled:
        # Suspended accounts are denied here, the single chokepoint every
        # login_required/admin_required caller routes through.
        real = None
    g.real_user = real

    user = real
    if real is not None and real.is_admin:
        impersonate = request.cookies.get(_IMPERSONATE_COOKIE)
        if impersonate:
            try:
                target = get_user_store().get_user(impersonate)
            except Exception:
                target = None
            if target is not None and not target.disabled and not target.is_admin:
                user = target

    g.user = user
    return user


def current_user() -> User | None:
    return _load_user_from_request()


def real_user() -> User | None:
    """The actually-authenticated admin, even while impersonating another user."""
    _load_user_from_request()
    return g.get("real_user")


def login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return redirect(f"/login?next={request.path}")
        return view(*args, **kwargs)

    return wrapper


def admin_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(f"/login?next={request.path}")
        if not user.is_admin:
            from tenancy.events import record_audit

            record_audit("access.denied_admin", target=request.path)
            return Response("403 — admin access required", status=403)
        return view(*args, **kwargs)

    return wrapper


def real_admin_required(view: Callable) -> Callable:
    """Like ``admin_required``, but checks the *real* authenticated identity
    rather than the effective one.

    Use this only for the "view as" controls themselves (start/switch/stop
    impersonation). Everything else should stay on ``admin_required``: while
    impersonating a non-admin, the effective identity correctly loses admin
    powers everywhere else, so the simulation is faithful.
    """

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        ru = real_user()
        if ru is None:
            return redirect(f"/login?next={request.path}")
        if not ru.is_admin:
            from tenancy.events import record_audit

            record_audit("access.denied_admin", target=request.path, actor=ru)
            return Response("403 — admin access required", status=403)
        return view(*args, **kwargs)

    return wrapper
