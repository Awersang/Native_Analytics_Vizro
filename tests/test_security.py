"""Security-focused tests: CSRF, stored-XSS escaping, role validation, and the
production-mode BigQuery fallback behaviour."""

import re

import pytest

import app as appmod
from config import settings

client = appmod.server.test_client()


def _csrf_token(test_client, url="/admin/users"):
    html = test_client.get(url).data.decode()
    m = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    assert m, "CSRF token not found"
    return m.group(1)


# ── CSRF ──────────────────────────────────────────────────────────────────────
def test_post_without_csrf_token_is_rejected():
    c = appmod.server.test_client()
    r = c.post(
        "/admin/users/create",
        data={"uid": "nocsrf", "email": "n@x.local", "role": "user"},
    )
    assert r.status_code == 400


def test_post_with_wrong_csrf_token_is_rejected():
    c = appmod.server.test_client()
    _csrf_token(c)  # seed a session token
    r = c.post(
        "/admin/users/create",
        data={"uid": "badcsrf", "email": "b@x.local", "_csrf_token": "wrong"},
    )
    assert r.status_code == 400


# ── Stored XSS ────────────────────────────────────────────────────────────────
def test_admin_user_list_escapes_html():
    c = appmod.server.test_client()
    token = _csrf_token(c)
    payload_email = "evil+<script>alert(1)</script>@x.local"
    c.post(
        "/admin/users/create",
        data={
            "uid": "xss<b>",
            "email": payload_email,
            "role": "user",
            "_csrf_token": token,
        },
    )
    html = c.get("/admin/users").data.decode()
    # The raw script tag must not appear unescaped.
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


# ── Role validation ───────────────────────────────────────────────────────────
def test_invalid_role_is_coerced_to_user():
    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={
            "email": "r@x.local",
            "role": "superadmin",
            "_csrf_token": token,
        },
    )
    from tenancy.users import get_user_store

    u = get_user_store().get_user("pending:r@x.local")
    assert u is not None
    assert u.role == "user"


# ── BigQuery fail-loud in prod ────────────────────────────────────────────────
def test_safe_query_returns_fallback_in_dev(monkeypatch):
    import pandas as pd

    from data_sources import bq

    monkeypatch.setattr(bq, "run_query", lambda sql: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(bq.settings, "env", "dev")
    fallback = pd.DataFrame({"x": [1]})
    out = bq.safe_query("SELECT 1", fallback=fallback)
    assert out.equals(fallback)


def test_safe_query_raises_in_prod(monkeypatch):
    import pandas as pd

    from data_sources import bq

    monkeypatch.setattr(bq, "run_query", lambda sql: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(bq.settings, "env", "prod")
    with pytest.raises(RuntimeError):
        bq.safe_query("SELECT 1", fallback=pd.DataFrame({"x": [1]}))
