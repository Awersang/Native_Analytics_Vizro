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


def _load_user_from_request() -> User | None:
    """Resolve the User for the current request, caching it on flask.g."""
    if "user" in g:
        return g.user

    if not settings.auth_enabled:
        # Dev mode: default to the fixture admin, but allow impersonating any
        # fixture user via the "View as" switcher (cookie ``na_dev_as``) so the
        # plain-user experience is reachable without enabling real auth.
        impersonate = request.cookies.get("na_dev_as")
        if impersonate:
            try:
                impersonated = get_user_store().get_user(impersonate)
            except Exception:
                impersonated = None
            if impersonated is not None:
                g.user = impersonated
                return g.user
        g.user = DEV_ADMIN
        return g.user

    cookie = request.cookies.get(settings.session_cookie_name)
    user: User | None = None
    if cookie:
        try:
            from auth.firebase import verify_session_cookie

            claims = verify_session_cookie(cookie)
            store = get_user_store()
            uid = claims.get("uid") or claims.get("sub", "")
            email = (claims.get("email") or "").lower()
            user = store.get_user(uid) or (store.get_user_by_email(email) if email else None)
            if user is None and email:
                if settings.auto_provision_users:
                    # Authenticated with Firebase but not yet provisioned: create
                    # a zero-access record so an admin can grant dashboards later.
                    user = User(uid=uid, email=email, role="user")
                    store.upsert_user(user)
                    logger.info("Auto-provisioned new user uid=%s email=%s", uid, email)
                else:
                    # Deny until an admin explicitly creates the user.
                    logger.warning(
                        "Authenticated but unprovisioned user denied: email=%s", email
                    )
        except Exception:
            logger.exception("Session cookie verification failed")
            user = None

    g.user = user
    return user


def current_user() -> User | None:
    return _load_user_from_request()


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
            return Response("403 — admin access required", status=403)
        return view(*args, **kwargs)

    return wrapper
