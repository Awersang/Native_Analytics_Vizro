"""
Lightweight CSRF protection for the server-rendered forms (admin panel, etc.).

Uses the synchroniser-token pattern: a random token is stored in the signed
Flask session and embedded as a hidden field in every state-changing form. On
POST the submitted token must match the session token.

Why not Flask-WTF? This keeps the dependency surface small while covering the
handful of HTML forms in this app. JSON/token endpoints (e.g. ``/sessionLogin``)
are not CSRF-sensitive because they require an unguessable Firebase ID token.
"""

from __future__ import annotations

import functools
import secrets
from typing import Callable

from flask import abort, request, session
from markupsafe import Markup

_SESSION_KEY = "_csrf_token"


def csrf_token() -> str:
    """Return the session CSRF token, creating one on first use."""
    token = session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_SESSION_KEY] = token
    return token


def csrf_input() -> Markup:
    """Hidden ``<input>`` carrying the CSRF token, safe to embed in HTML."""
    return Markup(f'<input type="hidden" name="_csrf_token" value="{csrf_token()}">')


def validate_csrf() -> None:
    """Abort with 400 if the submitted token is missing or wrong."""
    submitted = request.form.get("_csrf_token", "")
    expected = session.get(_SESSION_KEY, "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400, description="Invalid or missing CSRF token")


def csrf_protect(view: Callable) -> Callable:
    """Decorator that validates the CSRF token before a state-changing view."""

    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        validate_csrf()
        return view(*args, **kwargs)

    return wrapper
