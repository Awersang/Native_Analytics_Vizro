"""
Admin panel: manage users, clients (tenants) and per-user dashboard grants.

All routes are gated by ``admin_required``. The UI is intentionally simple
server-rendered HTML — the goal is a reliable management workflow, not a SPA.

Security notes:
  * Every value that originates from user input is HTML-escaped before being
    interpolated into the page (defends against stored XSS).
  * Every state-changing POST is CSRF-protected and re-validates its inputs.
"""

from __future__ import annotations

import logging
import re

from flask import Blueprint, redirect, request
from markupsafe import escape

from auth.middleware import admin_required, current_user
from pages_landing.shell import page
from security import csrf_input, csrf_protect
from tenancy.events import record_audit
from tenancy.models import Client, User
from tenancy.users import get_user_store

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")

_VALID_ROLES = {"user", "admin"}
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _all_slugs() -> list[str]:
    from dashboards import get_registry

    return [d.manifest.slug for d in get_registry()]


def _registry():
    from dashboards import get_registry

    return get_registry()


def _clean_role(raw: str) -> str:
    """Coerce a posted role to a known value (defaults to 'user')."""
    role = (raw or "").strip().lower()
    return role if role in _VALID_ROLES else "user"


@bp.route("/")
@admin_required
def home():
    store = get_user_store()
    pending = len(store.list_access_requests("pending"))
    pending_badge = f" ({pending})" if pending else ""
    body = (
        '<div class="section"><h2>Admin</h2>'
        '<p class="muted">Manage users, clients and dashboard access.</p>'
        '<a class="btn" href="/admin/users"><button>Users</button></a> '
        '<a class="btn" href="/admin/clients"><button class="secondary">Clients</button></a> '
        f'<a class="btn" href="/admin/requests"><button class="secondary">'
        f"Access requests{escape(pending_badge)}</button></a>"
        "</div>"
        '<div class="section"><h3 class="muted">Insights</h3>'
        '<a class="btn" href="/admin/audit"><button class="secondary">Audit log</button></a> '
        '<a class="btn" href="/admin/usage"><button class="secondary">Usage</button></a> '
        '<a class="btn" href="/admin/health"><button class="secondary">Data health</button></a>'
        "</div>"
        f'<p class="muted">{len(store.list_users())} users · '
        f"{len(store.list_clients())} clients · {len(_all_slugs())} dashboards · "
        f"{pending} pending request(s)</p>"
    )
    return page("Admin", body, user=current_user())


# ── Access requests ───────────────────────────────────────────────────────────
@bp.route("/requests")
@admin_required
def requests_queue():
    store = get_user_store()
    titles = {d.manifest.slug: d.manifest.title for d in _registry()}
    pending = store.list_access_requests("pending")
    if pending:
        rows = "".join(
            f"<tr><td>{escape(r.email)}<br><span class='muted'>{escape(r.uid)}</span></td>"
            f"<td>{escape(titles.get(r.slug, r.slug))}</td>"
            f"<td class='muted'>{escape(r.created_at)}</td>"
            f"<td><form class='inline' method='post' action='/admin/requests/{escape(r.id)}/approve'>"
            f"{csrf_input()}<button>Approve</button></form></td>"
            f"<td><form method='post' action='/admin/requests/{escape(r.id)}/deny'>"
            f"{csrf_input()}<button class='secondary'>Deny</button></form></td></tr>"
            for r in pending
        )
        table = (
            "<table><tr><th>User</th><th>Dashboard</th><th>Requested</th>"
            f"<th></th><th></th></tr>{rows}</table>"
        )
    else:
        table = '<p class="muted">No pending access requests.</p>'
    body = (
        '<div class="section"><h2>Access requests</h2>'
        '<p class="muted">Approving assigns the dashboard to the user\'s company, '
        "so every user in that company gains access.</p>"
        f"{table}</div>"
    )
    return page("Access requests", body, user=current_user())


@bp.route("/requests/<request_id>/approve", methods=["POST"])
@admin_required
@csrf_protect
def requests_approve(request_id: str):
    store = get_user_store()
    req = next((r for r in store.list_access_requests() if r.id == request_id), None)
    if req is not None:
        user = store.get_user(req.uid)
        # Company-first model: grant the dashboard to the requester's company so
        # all of its users inherit access. Fall back to a per-user grant only
        # when the user has no company.
        if user is not None and req.slug in _all_slugs():
            client = store.get_client(user.client_id) if user.client_id else None
            if client is not None:
                slugs = sorted(set(client.dashboard_slugs) | {req.slug})
                store.set_client_dashboards(client.id, slugs)
                record_audit("request.approve", target=req.uid,
                             detail=f"slug={req.slug} company={client.id}")
            else:
                slugs = sorted(set(user.dashboard_slugs) | {req.slug})
                store.set_grants(req.uid, slugs)
                record_audit("request.approve", target=req.uid,
                             detail=f"slug={req.slug} (per-user, no company)")
        store.set_request_status(request_id, "approved")
        logger.info("Admin approved access request id=%s slug=%s", request_id, req.slug)
    return redirect("/admin/requests")


@bp.route("/requests/<request_id>/deny", methods=["POST"])
@admin_required
@csrf_protect
def requests_deny(request_id: str):
    get_user_store().set_request_status(request_id, "denied")
    record_audit("request.deny", target=request_id)
    logger.info("Admin denied access request id=%s", request_id)
    return redirect("/admin/requests")



# ── Users ─────────────────────────────────────────────────────────────────────
@bp.route("/users")
@admin_required
def users():
    store = get_user_store()
    clients = {c.id: c for c in store.list_clients()}
    titles = {d.manifest.slug: d.manifest.title for d in _registry()}

    def _client_select(u):
        opts = '<option value="">— none —</option>' + "".join(
            f'<option value="{escape(cid)}"{" selected" if u.client_id == cid else ""}>'
            f"{escape(c.name)}</option>"
            for cid, c in clients.items()
        )
        return (
            f"<form class='inline' method='post' action='/admin/users/{escape(u.uid)}/client'>"
            f"{csrf_input()}<select name='client_id'>{opts}</select>"
            "<button>Set company</button></form>"
        )

    def _inherited(u):
        if u.is_admin:
            return '<span class="muted">all (admin)</span>'
        client = clients.get(u.client_id)
        company = list(client.dashboard_slugs) if client else []
        extra = [s for s in u.dashboard_slugs if s not in company]
        if not company and not extra:
            return '<span class="muted">none</span>'
        pills = "".join(f'<span class="pill">{escape(titles.get(s, s))}</span>' for s in company)
        pills += "".join(
            f'<span class="pill" title="per-user extra">+ {escape(titles.get(s, s))}</span>'
            for s in extra
        )
        return pills

    rows = []
    for u in store.list_users():
        rows.append(
            f"<tr><td>{escape(u.email)}<br><span class='muted'>{escape(u.uid)}</span></td>"
            f"<td>{escape(u.role)}</td>"
            f"<td>{_client_select(u)}</td>"
            f"<td>{_inherited(u)}</td>"
            f"<td><form method='post' action='/admin/users/{escape(u.uid)}/delete' "
            f"onsubmit=\"return confirm('Delete {escape(u.email)}?')\">"
            f"{csrf_input()}<button class='secondary'>Delete</button></form></td></tr>"
        )

    client_opts = '<option value="">— none —</option>' + "".join(
        f'<option value="{escape(cid)}">{escape(c.name)}</option>' for cid, c in clients.items()
    )
    create = (
        "<h3>Add user</h3>"
        '<form class="inline" method="post" action="/admin/users/create">'
        f"{csrf_input()}"
        '<label>Email<input name="email" type="email" required></label>'
        '<label>UID<input name="uid" placeholder="firebase uid" required></label>'
        '<label>Role<select name="role"><option>user</option><option>admin</option></select></label>'
        f'<label>Company<select name="client_id">{client_opts}</select></label>'
        "<button>Create</button></form>"
    )

    body = (
        '<div class="section"><h2>Users</h2>'
        '<p class="muted">Access comes from the user\'s company. Assign dashboards '
        'to companies on the <a href="/admin/clients">Clients</a> page.</p>'
        '<table><tr><th>User</th><th>Role</th><th>Company</th>'
        "<th>Dashboards (inherited)</th><th></th></tr>"
        f"{''.join(rows)}</table></div><div class='section'>{create}</div>"
    )
    return page("Users", body, user=current_user())


@bp.route("/users/create", methods=["POST"])
@admin_required
@csrf_protect
def users_create():
    store = get_user_store()
    user = User(
        uid=request.form["uid"].strip(),
        email=request.form["email"].strip().lower(),
        role=_clean_role(request.form.get("role", "user")),
        client_id=request.form.get("client_id", "").strip(),
    )
    store.upsert_user(user)
    record_audit("user.create", target=user.uid, detail=f"email={user.email} role={user.role}")
    logger.info("Admin created user uid=%s role=%s", user.uid, user.role)
    return redirect("/admin/users")


@bp.route("/users/<uid>/client", methods=["POST"])
@admin_required
@csrf_protect
def users_client(uid: str):
    client_id = request.form.get("client_id", "").strip()
    store = get_user_store()
    # Only accept a known company id (or empty to detach).
    if client_id and store.get_client(client_id) is None:
        client_id = ""
    store.set_user_client(uid, client_id)
    record_audit("user.client", target=uid, detail=f"client={client_id or '(none)'}")
    logger.info("Admin set user company uid=%s client=%s", uid, client_id)
    return redirect("/admin/users")


@bp.route("/users/<uid>/grants", methods=["POST"])
@admin_required
@csrf_protect
def users_grants(uid: str):
    slugs = [s for s in request.form.getlist("slugs") if s in _all_slugs()]
    get_user_store().set_grants(uid, slugs)
    record_audit("user.grants", target=uid, detail=f"slugs={','.join(slugs)}")
    logger.info("Admin set grants uid=%s slugs=%s", uid, slugs)
    return redirect("/admin/users")


@bp.route("/users/<uid>/delete", methods=["POST"])
@admin_required
@csrf_protect
def users_delete(uid: str):
    get_user_store().delete_user(uid)
    record_audit("user.delete", target=uid)
    logger.info("Admin deleted user uid=%s", uid)
    return redirect("/admin/users")


# ── Clients ───────────────────────────────────────────────────────────────────
@bp.route("/clients")
@admin_required
def clients():
    store = get_user_store()
    registry = _registry()
    dash_opts = [(d.manifest.slug, d.manifest.title) for d in registry]
    titles = dict(dash_opts)

    def _accent_cell(c):
        if not c.accent_color:
            return "—"
        col = escape(c.accent_color)
        return f"<span class='swatch' style='background:{col}'></span> {col}"

    def _assign_form(c):
        selected = set(c.dashboard_slugs)
        options = "".join(
            f'<option value="{escape(slug)}"{" selected" if slug in selected else ""}>'
            f"{escape(title)}</option>"
            for slug, title in dash_opts
        )
        pills = (
            "".join(f'<span class="pill">{escape(titles.get(s, s))}</span>' for s in c.dashboard_slugs)
            or '<span class="muted">none</span>'
        )
        return (
            f"<div>{pills}</div>"
            f'<form class="inline" method="post" action="/admin/clients/{escape(c.id)}/dashboards" '
            'style="margin-top:8px">'
            f"{csrf_input()}"
            f'<select name="slugs" multiple size="{min(max(len(dash_opts), 2), 6)}" '
            'style="min-width:220px">'
            f"{options}</select>"
            '<button>Save dashboards</button></form>'
        )

    rows = "".join(
        f"<tr><td>{escape(c.id)}</td><td>{escape(c.name)}</td>"
        f"<td>{escape(c.bq_dataset) or '(convention)'}</td>"
        f"<td>{escape(c.brand_name) or '—'}</td>"
        f"<td>{_accent_cell(c)}</td>"
        f"<td>{_assign_form(c)}</td></tr>"
        for c in store.list_clients()
    )
    create = (
        "<h3>Add client</h3>"
        '<form class="inline" method="post" action="/admin/clients/create">'
        f"{csrf_input()}"
        '<label>ID<input name="id" required></label>'
        '<label>Name<input name="name" required></label>'
        '<label>BQ dataset<input name="bq_dataset" placeholder="(optional override)"></label>'
        '<label>Brand name<input name="brand_name" placeholder="(optional)"></label>'
        '<label>Accent colour<input name="accent_color" type="color" value="#4a6cf7"></label>'
        "<button>Create</button></form>"
    )
    body = (
        '<style>.swatch{display:inline-block;width:12px;height:12px;border-radius:3px;'
        'vertical-align:middle;border:1px solid #0003;}</style>'
        '<div class="section"><h2>Clients</h2>'
        '<p class="muted">Assign dashboards to a company — every user in that '
        "company can open them. Hold Ctrl/Cmd to select multiple.</p>"
        "<table><tr><th>ID</th><th>Name</th><th>BigQuery dataset</th>"
        "<th>Brand</th><th>Accent</th><th>Dashboards</th></tr>"
        f"{rows}</table></div><div class='section'>{create}</div>"
    )
    return page("Clients", body, user=current_user())


@bp.route("/clients/<client_id>/dashboards", methods=["POST"])
@admin_required
@csrf_protect
def clients_dashboards(client_id: str):
    valid = set(_all_slugs())
    slugs = [s for s in request.form.getlist("slugs") if s in valid]
    store = get_user_store()
    if store.get_client(client_id) is not None:
        store.set_client_dashboards(client_id, slugs)
        record_audit("client.dashboards", target=client_id, detail=f"slugs={','.join(slugs)}")
        logger.info("Admin set client dashboards id=%s slugs=%s", client_id, slugs)
    return redirect("/admin/clients")



@bp.route("/clients/create", methods=["POST"])
@admin_required
@csrf_protect
def clients_create():
    accent = request.form.get("accent_color", "").strip()
    if accent and not _HEX_COLOR.match(accent):
        accent = ""
    client = Client(
        id=request.form["id"].strip(),
        name=request.form["name"].strip(),
        bq_dataset=request.form.get("bq_dataset", "").strip(),
        brand_name=request.form.get("brand_name", "").strip(),
        accent_color=accent,
    )
    get_user_store().upsert_client(client)
    record_audit("client.create", target=client.id, detail=f"name={client.name}")
    logger.info("Admin created client id=%s", client.id)
    return redirect("/admin/clients")


# ── Audit log (feature 7) ─────────────────────────────────────────────────────
@bp.route("/audit")
@admin_required
def audit():
    store = get_user_store()
    events = store.list_audit_events(limit=200)
    if events:
        rows = "".join(
            f"<tr><td class='muted'>{escape(e.created_at)}</td>"
            f"<td>{escape(e.actor_email) or escape(e.actor_uid)}</td>"
            f"<td><code>{escape(e.action)}</code></td>"
            f"<td>{escape(e.target) or '—'}</td>"
            f"<td class='muted'>{escape(e.detail) or '—'}</td></tr>"
            for e in events
        )
        table = (
            "<table><tr><th>Time (UTC)</th><th>Actor</th><th>Action</th>"
            f"<th>Target</th><th>Detail</th></tr>{rows}</table>"
        )
    else:
        table = '<p class="muted">No audit events recorded yet.</p>'
    body = (
        '<div class="section"><h2>Audit log</h2>'
        '<p class="muted">Most recent administrative actions (newest first).</p>'
        f"{table}</div>"
    )
    return page("Audit log", body, user=current_user())


# ── Usage analytics (feature 8) ───────────────────────────────────────────────
@bp.route("/usage")
@admin_required
def usage():
    store = get_user_store()
    events = store.list_usage_events(limit=5000)
    titles = {d.manifest.slug: d.manifest.title for d in _registry()}

    agg: dict[str, dict] = {}
    for e in events:
        a = agg.setdefault(e.slug, {"opens": 0, "users": set(), "last": ""})
        a["opens"] += 1
        a["users"].add(e.uid)
        if e.created_at > a["last"]:
            a["last"] = e.created_at

    if agg:
        ordered = sorted(agg.items(), key=lambda kv: kv[1]["opens"], reverse=True)
        rows = "".join(
            f"<tr><td>{escape(titles.get(slug, slug))}<br>"
            f"<span class='muted'>{escape(slug)}</span></td>"
            f"<td>{a['opens']}</td><td>{len(a['users'])}</td>"
            f"<td class='muted'>{escape(a['last'])}</td></tr>"
            for slug, a in ordered
        )
        table = (
            "<table><tr><th>Dashboard</th><th>Opens</th><th>Unique users</th>"
            f"<th>Last opened (UTC)</th></tr>{rows}</table>"
        )
        total = f"<p class='muted'>{len(events)} total opens tracked.</p>"
    else:
        table = '<p class="muted">No usage recorded yet.</p>'
        total = ""
    body = (
        '<div class="section"><h2>Usage analytics</h2>'
        '<p class="muted">Dashboard opens by HTML page load.</p>'
        f"{table}{total}</div>"
    )
    return page("Usage", body, user=current_user())


# ── Data-source health (feature 9) ────────────────────────────────────────────
@bp.route("/health")
@admin_required
def health():
    rows = []
    for entry in _registry():
        title = escape(entry.manifest.title)
        if entry.data_health is not None:
            try:
                sources = entry.data_health()
            except Exception as exc:  # noqa: BLE001 — surface failure as a row
                rows.append(
                    f"<tr><td>{title}</td><td>(health check)</td>"
                    f"<td><span class='status-error'>error</span></td>"
                    f"<td class='muted'>{escape(type(exc).__name__)}: {escape(str(exc))}</td>"
                    "<td>—</td></tr>"
                )
                continue
            for s in sources:
                rows.append(
                    f"<tr><td>{title}</td><td>{escape(s.name)}</td>"
                    f"<td><span class='status-{escape(s.status)}'>{escape(s.status)}</span></td>"
                    f"<td class='muted'>{escape(s.detail) or '—'}</td>"
                    f"<td class='muted'>{('rows=' + str(s.rows)) if s.rows is not None else ''}"
                    f"{(' · ' + escape(s.as_of)) if s.as_of else ''}</td></tr>"
                )
        else:
            for req in entry.manifest.data_requirements or ["(unspecified)"]:
                rows.append(
                    f"<tr><td>{title}</td><td>{escape(req)}</td>"
                    f"<td><span class='muted'>unknown</span></td>"
                    f"<td class='muted'>No health probe defined.</td><td>—</td></tr>"
                )

    table = (
        '<style>.status-ok{color:#3ddc84}.status-degraded{color:#e6b800}'
        '.status-error{color:#f55}</style>'
        "<table><tr><th>Dashboard</th><th>Source</th><th>Status</th>"
        f"<th>Detail</th><th>Info</th></tr>{''.join(rows)}</table>"
    )
    body = (
        '<div class="section"><h2>Data-source health</h2>'
        '<p class="muted">Live probe of each dashboard\'s data dependencies.</p>'
        f"{table}</div>"
    )
    return page("Data health", body, user=current_user())

