"""End-to-end route smoke tests via Flask's in-process test client (dev mode)."""

import re

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
    assert client.get("/admin/users").status_code == 200
    assert client.get("/admin/clients").status_code == 200
    assert client.get("/admin/audit").status_code == 200
    assert client.get("/admin/usage").status_code == 200
    assert client.get("/admin/health").status_code == 200


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_dashboard_routes_render():
    for slug in ("timeline", "breakdown", "bq_sample"):
        assert client.get(f"/app/d/{slug}").status_code == 200


def test_admin_can_create_user_and_set_grants():
    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={
            "uid": "t1",
            "email": "t1@x.local",
            "role": "user",
            "client_id": "acme",
            "_csrf_token": token,
        },
    )
    from tenancy.users import get_user_store

    store = get_user_store()
    assert store.get_user("t1") is not None

    c.post(
        "/admin/users/t1/grants",
        data={"slugs": ["timeline"], "_csrf_token": token},
    )
    assert store.get_user("t1").dashboard_slugs == ["timeline"]


def test_account_page_renders():
    r = client.get("/account")
    assert r.status_code == 200
    assert b"My account" in r.data
    # Dev admin email should appear on the page.
    assert b"admin@dev.local" in r.data


def test_access_request_queue_and_approve():
    from datetime import datetime, timezone

    from tenancy.models import AccessRequest
    from tenancy.users import get_user_store

    store = get_user_store()
    # A non-admin fixture user requests a dashboard they don't have.
    store.add_access_request(
        AccessRequest(
            uid="dev-user-globex",
            email="user@globex.local",
            slug="timeline",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    assert any(r.slug == "timeline" for r in store.list_access_requests("pending"))

    c = appmod.server.test_client()
    queue = c.get("/admin/requests")
    assert queue.status_code == 200
    assert b"user@globex.local" in queue.data

    req_id = "dev-user-globex__timeline"
    token = _csrf_token(c, url="/admin/requests")
    c.post(f"/admin/requests/{req_id}/approve", data={"_csrf_token": token})

    # Company-first model: approval assigns the dashboard to the user's company,
    # so every user of that company (incl. the requester) gains access.
    assert "timeline" in store.get_client("globex").dashboard_slugs
    from tenancy.access import can_access

    assert can_access(store.get_user("dev-user-globex"), "timeline")
    assert all(
        r.id != req_id for r in store.list_access_requests("pending")
    )


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
        "/admin/clients/acme/dashboards",
        data={"slugs": ["breakdown"], "_csrf_token": token},
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


def test_admin_action_records_audit_event():
    from tenancy.users import get_user_store

    c = appmod.server.test_client()
    token = _csrf_token(c)
    c.post(
        "/admin/users/create",
        data={
            "uid": "audit-t1",
            "email": "audit-t1@x.local",
            "role": "user",
            "client_id": "",
            "_csrf_token": token,
        },
    )
    events = get_user_store().list_audit_events()
    assert any(e.action == "user.create" and e.target == "audit-t1" for e in events)


def test_dashboard_open_records_usage_event():
    from tenancy.users import get_user_store

    client.get("/app/d/timeline", headers={"Accept": "text/html"})
    events = get_user_store().list_usage_events()
    assert any(e.slug == "timeline" for e in events)

