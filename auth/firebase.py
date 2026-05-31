"""
Firebase / Identity Platform integration (production auth).

Responsibilities:
  * Initialise the Firebase Admin SDK once per process.
  * Verify the ID token a browser obtains from Firebase JS SDK on /login.
  * Exchange it for a long-lived, HttpOnly session cookie.
  * Verify that session cookie on subsequent requests.

``firebase_admin`` is imported lazily so that local dev (AUTH_ENABLED=false)
runs without the dependency installed.
"""

from __future__ import annotations

import datetime
import hashlib
import time
from functools import lru_cache
from typing import Any

from config import settings

# Session cookies live for 5 days; the browser must re-login afterwards.
SESSION_COOKIE_TTL = datetime.timedelta(days=5)

# In-process cache of verified session-cookie claims, so we do not re-verify
# (and re-check revocation against Firebase) on every single request. Keyed by a
# hash of the cookie; values are (claims, verified_at, last_revocation_check_at)
# using a monotonic clock.
_claims_cache: dict[str, tuple[dict[str, Any], float, float]] = {}


def _cookie_key(cookie: str) -> str:
    return hashlib.sha256(cookie.encode("utf-8")).hexdigest()



@lru_cache
def _ensure_initialised() -> None:
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:  # already initialised
        return

    if settings.firebase_credentials_file:
        cred = credentials.Certificate(settings.firebase_credentials_file)
    else:
        # Application Default Credentials (recommended on Cloud Run).
        cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(
        cred,
        {"projectId": settings.gcp_project_id} if settings.gcp_project_id else None,
    )


def verify_id_token(id_token: str) -> dict[str, Any]:
    """Verify a Firebase ID token; returns decoded claims or raises."""
    _ensure_initialised()
    from firebase_admin import auth as fb_auth

    return fb_auth.verify_id_token(id_token)


def create_session_cookie(id_token: str) -> tuple[str, datetime.timedelta]:
    """Exchange a verified ID token for a session cookie value + TTL."""
    _ensure_initialised()
    from firebase_admin import auth as fb_auth

    cookie = fb_auth.create_session_cookie(id_token, expires_in=SESSION_COOKIE_TTL)
    return cookie, SESSION_COOKIE_TTL


def verify_session_cookie(cookie: str) -> dict[str, Any]:
    """Verify a session cookie; returns decoded claims or raises.

    Results are cached in-process for ``settings.session_verify_cache_ttl``
    seconds to avoid the per-request cost of full verification. A full
    revocation check against Firebase is forced at most every
    ``settings.session_revocation_check_interval`` seconds per cookie.
    """
    _ensure_initialised()
    from firebase_admin import auth as fb_auth

    key = _cookie_key(cookie)
    now = time.monotonic()
    cached = _claims_cache.get(key)

    if cached is not None:
        claims, verified_at, last_revocheck = cached
        if now - verified_at < settings.session_verify_cache_ttl:
            if now - last_revocheck >= settings.session_revocation_check_interval:
                # Periodic revocation check; refresh the timestamp on success.
                claims = fb_auth.verify_session_cookie(cookie, check_revoked=True)
                _claims_cache[key] = (claims, verified_at, now)
            return claims
        # Cache entry expired.
        _claims_cache.pop(key, None)

    # Cache miss / expired: verify fully (including revocation).
    claims = fb_auth.verify_session_cookie(cookie, check_revoked=True)
    _claims_cache[key] = (claims, now, now)
    return claims

