"""End-to-end route smoke tests via Flask's in-process test client (dev mode)."""

import re
import time

import app as appmod

client = appmod.server.test_client()


def _csrf_token(test_client, url="/admin/users"):
    """Fetch a page and extract its CSRF token (also seeds the session cookie)."""
    html = test_client.get(url).data.decode()
    m = re.search(r'name="_csrf_token" value="([^"]+)"', html)
    assert m, "CSRF token not found on page"
    return m.group(1)


def test_landing_page_lists_dashboards():
    r = client.get("/")
    assert r.status_code == 200
    assert b"Your dashboards" in r.data


def test_login_redirects_in_dev():
    r = client.get("/login")
    assert r.status_code in (301, 302)


def test_admin_pages_accessible_in_dev():
    assert client.get("/admin/dashboards").status_code == 200
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/operators").status_code == 200
    assert client.get("/admin/clients").status_code == 200
    assert client.get("/admin/audit").status_code == 200
    assert client.get("/admin/usage").status_code == 200
    assert client.get("/admin/health").status_code == 200


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_unhandled_exception_renders_friendly_500(monkeypatch):
    """An unhandled exception in any route must hit the friendly error
    handler (app.py::_handle_server_error), not leak a raw traceback."""

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setitem(appmod.server.view_functions, "_healthz", _boom)
    r = client.get("/healthz")
    assert r.status_code == 500
    assert b"Something went wrong" in r.data
    assert b"RuntimeError" not in r.data


def test_dashboard_routes_render():
    for slug in ("timeline", "breakdown", "bq_sample", "amazon_2026"):
        assert client.get(f"/app/d/{slug}").status_code == 200


def test_amazon_2026_every_page_renders():
    """The flagship dashboard's 7 pages must each build/render, not just its
    base path — a page-builder break here would otherwise pass CI silently."""
    for sub_path in (
        "",
        "/topic-areas",
        "/narratives",
        "/campaigns",
        "/publishers",
        "/discover",
        "/archive",
    ):
        r = client.get(f"/app/d/amazon_2026{sub_path}")
        assert r.status_code == 200, f"page at amazon_2026{sub_path} failed to render"


def test_slug_for_path():
    from app import _slug_for_path

    assert _slug_for_path("/app/d/timeline") == "timeline"
    assert _slug_for_path("/app/d/amazon_2026/discover") == "amazon_2026"
    assert _slug_for_path("/app/assets/foo.css") is None
    assert _slug_for_path("/app/overview") is None
    assert _slug_for_path("/login") is None


def test_admin_can_invite_user_and_set_restrictions():
    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={
            "email": "t1@x.local",
            "role": "user",
            "client_id": "acme",
            "_csrf_token": token,
        },
    )
    from tenancy.users import get_user_store

    store = get_user_store()
    uid = "pending:t1@x.local"
    assert store.get_user(uid) is not None

    # The checklist is "checked = has access" - checking only bq_sample
    # means timeline (acme's other dashboard) becomes restricted. client_id
    # must match the user's current company so the save applies the access
    # change instead of treating it as a company change.
    c.post(
        f"/admin/users/{uid}/save",
        data={"client_id": "acme", "slugs": ["bq_sample"], "_csrf_token": token},
    )
    user = store.get_user(uid)
    assert user.restricted_dashboard_slugs == ["timeline"]

    from tenancy.access import accessible_slugs

    assert accessible_slugs(user, ["timeline", "breakdown", "bq_sample"]) == ["bq_sample"]


def test_invited_user_is_reclaimed_onto_real_uid_on_first_login(monkeypatch):
    """An admin-invited user is stored under a pending: placeholder uid until
    they actually sign in; the auth middleware must then move the record onto
    their real Firebase uid so future lookups key off it directly."""
    from tenancy.models import User
    from tenancy.users import get_user_store

    store = get_user_store()
    store.upsert_user(User(uid="pending:t2@x.local", email="t2@x.local", role="user", client_id="acme"))

    import auth.firebase as fb
    from config import settings

    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(fb, "verify_session_cookie", lambda cookie: {"uid": "real-uid-t2", "email": "t2@x.local"})

    from auth.middleware import _resolve_real_user

    with appmod.server.test_request_context(headers={"Cookie": "na_session=fake"}):
        user = _resolve_real_user()

    assert user is not None
    assert user.uid == "real-uid-t2"
    assert store.get_user("real-uid-t2") is not None
    assert store.get_user("pending:t2@x.local") is None


def test_account_page_renders():
    r = client.get("/account")
    assert r.status_code == 200
    assert b"My account" in r.data
    # Dev admin email should appear on the page.
    assert b"admin@dev.local" in r.data


def test_company_assignment_controls_user_access():
    from tenancy.access import accessible_slugs
    from tenancy.users import get_user_store

    store = get_user_store()
    user = store.get_user("dev-user-acme")
    # Fixture: ACME company is assigned timeline + bq_sample; the user inherits them.
    assert set(accessible_slugs(user, ["timeline", "breakdown", "bq_sample"])) == {
        "timeline",
        "bq_sample",
    }

    c = appmod.server.test_client()
    token = _csrf_token(c, url="/admin/clients")
    c.post(
        "/admin/clients/acme/save",
        data={"name": "ACME Corp", "slugs": ["breakdown"], "_csrf_token": token},
    )
    user = store.get_user("dev-user-acme")
    assert set(accessible_slugs(user, ["timeline", "breakdown", "bq_sample"])) == {"breakdown"}


def test_dev_view_as_switcher():
    c = appmod.server.test_client()
    # Switcher page lists fixture users.
    page = c.get("/dev")
    assert page.status_code == 200
    assert b"user@acme.local" in page.data

    # Impersonate a non-admin user → no Admin link, sees only company dashboards.
    c.get("/dev/as/dev-user-globex")
    home = c.get("/")
    assert home.status_code == 200
    assert b"viewing as" in home.data
    assert b"user@globex.local" in home.data

    # Reset back to the dev admin.
    c.get("/dev/exit")
    assert b"admin@dev.local" in c.get("/").data


def test_operator_panel_and_cross_client_audit():
    """An admin can create an operator, grant them cross-client access to a
    whole company in the dedicated Operators panel, and each dashboard open
    is audit-logged."""
    c = appmod.server.test_client()
    token = _csrf_token(c, url="/admin/operators")
    c.post(
        "/admin/operators/create",
        data={"email": "op1@x.local", "_csrf_token": token},
    )
    uid = "pending:op1@x.local"

    page = c.get(f"/admin/operators?uid={uid}")
    assert b"Save access" in page.data
    assert b"operator" in page.data.lower()

    c.post(
        f"/admin/operators/{uid}/access",
        data={"client_ids": ["acme"], "_csrf_token": token},
    )
    from tenancy.users import get_user_store

    store = get_user_store()
    assert store.get_user(uid).allowed_client_ids == ["acme"]

    c.get(f"/dev/as/{uid}")
    c.get("/app/d/timeline", headers={"Accept": "text/html"})

    events = store.list_audit_events()
    assert any(
        e.action == "dashboard.cross_client_open" and e.target == "timeline"
        for e in events
    )


def test_dashboard_view_can_restrict_company_user_and_shows_operator_access():
    from tenancy.access import accessible_slugs
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c, url="/admin/dashboards")

    # The checklist is "checked = has access" - leaving dev-user-acme (acme's
    # only company user) unchecked is what restricts them from timeline.
    # client_id must match timeline's current owner so the save applies the
    # access change instead of treating it as an owner change.
    c.post(
        "/admin/dashboards/timeline/save",
        data={"client_id": "acme", "_csrf_token": token},
    )

    store = get_user_store()
    user = store.get_user("dev-user-acme")
    assert "timeline" in user.restricted_dashboard_slugs
    assert accessible_slugs(user, ["timeline", "bq_sample"]) == ["bq_sample"]

    # Operators are granted access per-client on the Operators panel, not
    # per-dashboard here - the Dashboards page only reflects that grant.
    c.post(
        "/admin/operators/dev-operator/access",
        data={"client_ids": ["amazon"], "_csrf_token": _csrf_token(c, url="/admin/operators")},
    )
    operator = store.get_user("dev-operator")
    assert "amazon" in operator.allowed_client_ids
    assert "amazon_2026" in accessible_slugs(operator, ["amazon_2026", "timeline"])

    dashboards_page = c.get("/admin/dashboards")
    assert b"operator@dev.local" in dashboards_page.data


def test_dashboard_owner_changes_are_unique_across_clients():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c, url="/admin/dashboards")
    c.post(
        "/admin/dashboards/timeline/save",
        data={"client_id": "globex", "_csrf_token": token},
    )

    store = get_user_store()
    acme = store.get_client("acme")
    globex = store.get_client("globex")
    assert "timeline" not in acme.dashboard_slugs
    assert "timeline" in globex.dashboard_slugs


def test_admin_action_records_audit_event():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={
            "email": "audit-t1@x.local",
            "role": "user",
            "client_id": "",
            "_csrf_token": token,
        },
    )
    events = get_user_store().list_audit_events()
    assert any(e.action == "user.create" and e.target == "pending:audit-t1@x.local" for e in events)


def test_admin_can_change_role_and_suspend_user():
    """An admin can promote/demote a user's role and suspend/reactivate their
    account from the Users page; suspension also revokes "view as" — neither
    starting a new impersonation of a suspended account nor an existing
    impersonation session surviving mid-session suspension is allowed."""
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={"email": "lc1@x.local", "role": "user", "client_id": "", "_csrf_token": token},
    )
    store = get_user_store()
    uid = "pending:lc1@x.local"

    c.post(f"/admin/users/{uid}/role", data={"role": "admin", "_csrf_token": token})
    assert store.get_user(uid).role == "admin"
    c.post(f"/admin/users/{uid}/role", data={"role": "user", "_csrf_token": token})
    assert store.get_user(uid).role == "user"

    # Start impersonating lc1 while still enabled.
    c2 = appmod.server.test_client()
    c2.get(f"/dev/as/{uid}")
    assert b"lc1@x.local" in c2.get("/").data

    c.post(f"/admin/users/{uid}/disable", data={"_csrf_token": token})
    assert store.get_user(uid).disabled is True
    page = c.get("/admin/users")
    assert b"(suspended)" in page.data

    # The existing impersonation cookie stops granting lc1's identity — the
    # request now resolves back to the real admin instead (not a 500/loop;
    # there's no "logging out the admin" semantics for a stale view-as target).
    assert b"admin@dev.local" in c2.get("/").data

    # Starting a *new* impersonation of an already-suspended account is also
    # refused.
    c3 = appmod.server.test_client()
    c3.get(f"/dev/as/{uid}")
    assert b"admin@dev.local" in c3.get("/").data

    # Reactivating restores access.
    c.post(f"/admin/users/{uid}/disable", data={"_csrf_token": token})
    assert store.get_user(uid).disabled is False
    c2.get("/dev/exit")


def test_admin_can_edit_and_delete_client():
    """An admin can edit a client's name/dataset from the Clients page,
    and delete it — but deletion is refused while a user still belongs to
    that company, mirroring the user-lifecycle safety checks."""
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c, url="/admin/clients")
    store = get_user_store()

    c.post(
        "/admin/clients/create",
        data={"id": "lc-client", "name": "Old Name", "_csrf_token": token},
    )
    assert store.get_client("lc-client").name == "Old Name"

    c.post(
        "/admin/clients/lc-client/save",
        data={
            "name": "New Name",
            "bq_dataset": "lc_dataset",
            "_csrf_token": token,
        },
    )
    updated = store.get_client("lc-client")
    assert updated.name == "New Name"
    assert updated.bq_dataset == "lc_dataset"

    # A user still assigned to this company blocks deletion.
    c.post(
        "/admin/users/create",
        data={
            "email": "lcu@x.local",
            "role": "user",
            "client_id": "lc-client",
            "_csrf_token": token,
        },
    )
    c.post("/admin/clients/lc-client/delete", data={"_csrf_token": token})
    assert store.get_client("lc-client") is not None

    # Detaching the user allows the delete to proceed.
    c.post("/admin/users/pending:lcu@x.local/save", data={"client_id": "", "_csrf_token": token})
    c.post("/admin/clients/lc-client/delete", data={"_csrf_token": token})
    assert store.get_client("lc-client") is None

    events = store.list_audit_events()
    assert any(e.action == "client.update" and e.target == "lc-client" for e in events)
    assert any(e.action == "client.delete" and e.target == "lc-client" for e in events)


def test_disabled_real_user_is_denied():
    """The production case: a disabled user's *own* session (not someone
    else's "view as") must be denied outright at the auth layer, the single
    chokepoint every login_required/admin_required route routes through."""
    import auth.middleware as mw
    from tenancy.models import User

    disabled_user = User(uid="dx1", email="dx1@x.local", role="user", disabled=True)
    with appmod.server.test_request_context("/"):
        original = mw._resolve_real_user
        mw._resolve_real_user = lambda: disabled_user
        try:
            assert mw.current_user() is None
        finally:
            mw._resolve_real_user = original


def test_view_as_blocks_admin_targets_and_self():
    """An admin can't impersonate another admin (would misattribute
    subsequent admin actions/audit to the wrong uid) or themselves."""
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/operators/create",
        data={"email": "lc2@x.local", "role": "admin", "_csrf_token": token},
    )
    uid = "pending:lc2@x.local"

    c.get(f"/dev/as/{uid}")
    # Still the original dev admin — admin targets are refused.
    assert b"admin@dev.local" in c.get("/").data

    c.get("/dev/as/dev-admin")
    assert b"admin@dev.local" in c.get("/").data

    store = get_user_store()
    events = store.list_audit_events()
    assert not any(e.action == "user.impersonate_start" and e.target == uid for e in events)


def test_view_as_survives_exit_while_impersonating():
    """/dev/exit and /dev must stay reachable while impersonating a non-admin
    — they're gated on the *real* admin identity, not the effective one."""
    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={"email": "lc3@x.local", "role": "user", "client_id": "", "_csrf_token": token},
    )
    c.get("/dev/as/pending:lc3@x.local")
    assert b"lc3@x.local" in c.get("/").data

    assert c.get("/dev").status_code == 200
    c.get("/dev/exit")
    assert b"admin@dev.local" in c.get("/").data


def test_dashboard_open_records_usage_event():
    from tenancy.users import get_user_store

    client.get("/app/d/timeline", headers={"Accept": "text/html"})
    # record_usage() writes on a background thread (the page-nav request is
    # kept off the usage-store round-trip) - poll instead of asserting
    # immediately.
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline:
        events = get_user_store().list_usage_events()
        if any(e.slug == "timeline" for e in events):
            return
        time.sleep(0.02)
    assert False, "usage event for 'timeline' was not recorded within 1s"


def test_denied_dashboard_access_records_audit_event():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    c.get("/dev/as/dev-user-acme")  # ACME is only granted timeline + bq_sample
    r = c.get("/app/d/amazon_2026", headers={"Accept": "text/html"})
    assert r.status_code == 403

    store = get_user_store()
    assert any(
        e.action == "access.denied_dashboard" and e.target == "amazon_2026"
        for e in store.list_audit_events()
    )
    c.get("/dev/exit")


def test_denied_admin_access_records_audit_event():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    c.get("/dev/as/dev-user-acme")  # a regular user, not an admin
    r = c.get("/admin/users")
    assert r.status_code == 403

    store = get_user_store()
    assert any(e.action == "access.denied_admin" and e.target == "/admin/users" for e in store.list_audit_events())
    c.get("/dev/exit")


def test_users_page_search_filters_roster():
    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={"uid": "search1", "email": "findme@x.local", "role": "user", "client_id": "", "_csrf_token": token},
    )
    found = c.get("/admin/users?q=findme")
    assert b"findme@x.local" in found.data

    not_found = c.get("/admin/users?q=zzz-nobody-zzz")
    assert b"findme@x.local" not in not_found.data
    assert b"No users match" in not_found.data


def test_audit_log_search_and_pagination():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={"uid": "audit-pg", "email": "audit-pg@x.local", "role": "user", "client_id": "", "_csrf_token": token},
    )

    filtered = c.get("/admin/audit?q=audit-pg")
    assert b"user.create" in filtered.data
    assert b"audit-pg" in filtered.data

    empty = c.get("/admin/audit?q=zzz-nobody-zzz")
    assert b"No audit events match" in empty.data

    # Page far beyond the data clamps to the last page rather than erroring.
    last_page = c.get("/admin/audit?page=999")
    assert last_page.status_code == 200


def test_chat_endpoint_answers_with_local_fallback():
    # No GEMINI_API_KEY in dev → the offline pandas fallback answers.
    r = client.post(
        "/ext/chat/ask",
        json={"slug": "timeline", "question": "How many rows are there?"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["source"] == "local"
    assert "rows" in body["answer"].lower()


def test_chat_endpoint_validates_input():
    assert client.post("/ext/chat/ask", json={"slug": "timeline"}).status_code == 400
    assert client.post("/ext/chat/ask", json={"question": "hi"}).status_code == 400


def test_chat_endpoint_covers_amazon_2026():
    r = client.post(
        "/ext/chat/ask",
        json={"slug": "amazon_2026", "question": "How many rows are there?"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["source"] == "local"
    assert "rows" in body["answer"].lower()


def test_chat_endpoint_rate_limits_repeated_calls():
    import extensions.chat_with_data as chat_mod

    chat_mod._recent_calls.clear()
    payload = {"slug": "timeline", "question": "How many rows are there?"}
    for _ in range(chat_mod._RATE_LIMIT_CALLS):
        assert client.post("/ext/chat/ask", json=payload).status_code == 200
    assert client.post("/ext/chat/ask", json=payload).status_code == 429
    chat_mod._recent_calls.clear()

