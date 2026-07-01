"""
Admin panel: manage users, operators, clients, dashboards, and access policy.

All routes are gated by ``admin_required``. The UI is intentionally simple
server-rendered HTML - the goal is a reliable management workflow, not a SPA.

Security notes:
  * Every value that originates from user input is HTML-escaped before being
    interpolated into the page (defends against stored XSS).
  * Every state-changing POST is CSRF-protected and re-validates its inputs.

Business logic lives in admin/services.py; HTML-rendering helpers and the
per-page detail-panel builders live in admin/views.py. This file is just the
Blueprint and its view functions, plus small per-route rendering closures
that close over a route's own local variables (so they aren't reusable
enough to be worth promoting to admin/views.py).
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from flask import Blueprint, redirect, request
from markupsafe import escape

from auth.middleware import admin_required, current_user
from security import csrf_input, csrf_protect
from tenancy.access import dashboard_owner_map
from tenancy.events import record_audit
from tenancy.models import Client, User
from tenancy.users import get_user_store

from admin.services import (
    PENDING_PREFIX,
    all_slugs,
    assign_dashboard_owner,
    clean_role,
    dashboard_options,
    dashboard_titles,
    effective_company_dashboards,
    is_pending,
    logo_data_uri_from_upload,
    registry,
    sanitize_user_for_role,
    send_invite,
    valid_client_id,
)
from admin.views import (
    MD_EMPTY,
    admin_page,
    checklist,
    client_detail,
    dashboard_detail,
    md_layout,
    md_row,
    operator_detail,
    pill_list,
    section_title,
    user_detail,
)

logger = logging.getLogger(__name__)

bp = Blueprint("admin", __name__, url_prefix="/admin")

_AUDIT_PAGE_SIZE = 50


@bp.route("/")
@admin_required
def home():
    store = get_user_store()
    operators = sum(1 for user in store.list_users() if user.is_operator)
    body = (
        '<div class="section"><h2>Admin</h2>'
        '<p class="muted">Manage dashboards, users, operators, clients, and access policy.</p>'
        '<a class="btn" href="/admin/dashboards"><button>Dashboards</button></a> '
        '<a class="btn" href="/admin/users"><button class="secondary">Users</button></a> '
        '<a class="btn" href="/admin/clients"><button class="secondary">Clients</button></a> '
        '<a class="btn" href="/admin/operators"><button class="secondary">Operators</button></a>'
        "</div>"
        '<div class="section"><h3 class="muted">Insights</h3>'
        '<a class="btn" href="/admin/audit"><button class="secondary">Audit log</button></a> '
        '<a class="btn" href="/admin/usage"><button class="secondary">Usage</button></a> '
        '<a class="btn" href="/admin/health"><button class="secondary">Data health</button></a>'
        "</div>"
        f'<p class="muted">{len(store.list_users())} accounts · '
        f"{operators} operators · {len(store.list_clients())} clients · {len(all_slugs())} dashboards</p>"
    )
    return admin_page("Admin", body)


@bp.route("/users")
@admin_required
def users():
    store = get_user_store()
    clients = {c.id: c for c in store.list_clients()}
    titles = dashboard_titles()
    q = request.args.get("q", "").strip().lower()
    me = current_user()

    roster = [u for u in store.list_users() if u.is_company_user]
    if q:
        roster = [u for u in roster if q in u.email.lower() or q in u.uid.lower()]
    roster.sort(key=lambda u: u.email.lower())

    sel_uid = request.args.get("uid", "") or (roster[0].uid if roster else "")

    def _group_label(key: str) -> str:
        if key == "__unassigned__":
            return "No company"
        return clients[key].name if key in clients else key

    groups: dict[str, list[User]] = {}
    for user in roster:
        groups.setdefault(user.client_id or "__unassigned__", []).append(user)

    def _row_meta(u: User) -> str:
        count = len(effective_company_dashboards(u, clients))
        meta = f"{count} dashboard{'' if count == 1 else 's'}"
        if is_pending(u.uid):
            meta += " · (invite pending)"
        if u.disabled:
            meta += " · (suspended)"
        return meta

    def _row_href(u: User) -> str:
        href = f"/admin/users?uid={quote(u.uid)}"
        return f"{href}&q={quote(q)}" if q else href

    list_html = "".join(
        f'<div class="md-group-label">{escape(_group_label(key))} <span class="pill">{len(users_in)}</span></div>'
        + "".join(
            md_row(_row_href(u), u.uid == sel_uid, escape(u.email), _row_meta(u)) for u in users_in
        )
        for key, users_in in sorted(groups.items(), key=lambda kv: _group_label(kv[0]).lower())
    ) or '<p class="muted">No users match that search.</p>'

    selected = store.get_user(sel_uid) if sel_uid else None
    if selected is not None and not selected.is_company_user:
        selected = None
    detail_html = user_detail(selected, clients, titles, me) if selected else MD_EMPTY

    search_form = (
        '<form class="admin-filter-row" method="get">'
        f'<input name="q" placeholder="Search by email or UID" value="{escape(q)}" style="min-width:260px">'
        "<button>Search</button>"
        + (' <a class="btn" href="/admin/users"><button class="secondary">Clear</button></a>' if q else "")
        + "</form>"
    )

    client_opts = '<option value="">- none -</option>' + "".join(
        f'<option value="{escape(cid)}">{escape(c.name)}</option>' for cid, c in clients.items()
    )
    create = (
        "<h3>Invite user</h3>"
        '<form class="inline" method="post" action="/admin/users/create">'
        f"{csrf_input()}"
        '<label>Email<input name="email" type="email" required></label>'
        f'<label>Company<select name="client_id">{client_opts}</select></label>'
        "<button>Invite</button></form>"
    )

    body = (
        f'<div class="section">{section_title("Users", include_back=True)}'
        '<p class="muted">Company users inherit dashboards from their company. Admins can only '
        "remove dashboards for an individual user here; they cannot extend access beyond the "
        "company scope. Inviting a user emails them a sign-in link; they're matched to this record "
        'automatically on first login. Use <a href="/admin/operators">Operators</a> to create admin '
        "or operator accounts.</p>"
        f"{search_form}{md_layout(list_html, detail_html)}</div><div class='section'>{create}</div>"
    )
    return admin_page("Users", body)


@bp.route("/users/create", methods=["POST"])
@admin_required
@csrf_protect
def users_create():
    client_id = valid_client_id(request.form.get("client_id", ""))
    email = request.form["email"].strip().lower()
    user = User(
        uid=f"{PENDING_PREFIX}{email}",
        email=email,
        role="user",
        client_id=client_id,
    )
    get_user_store().upsert_user(sanitize_user_for_role(user))
    record_audit("user.create", target=user.uid, detail=f"email={user.email} role={user.role}")
    logger.info("Admin invited user email=%s role=%s", email, user.role)
    send_invite(email)
    return redirect(f"/admin/users?uid={quote(user.uid)}")


@bp.route("/users/<uid>/resend-invite", methods=["POST"])
@admin_required
@csrf_protect
def users_resend_invite(uid: str):
    user = get_user_store().get_user(uid)
    if user is not None and is_pending(user.uid):
        send_invite(user.email)
        record_audit("user.invite.resend", target=uid)
        logger.info("Admin resent invite uid=%s", uid)
    return redirect(f"/admin/users?uid={quote(uid)}")


@bp.route("/users/<uid>/save", methods=["POST"])
@admin_required
@csrf_protect
def users_save(uid: str):
    store = get_user_store()
    user = store.get_user(uid)
    if user is None or not user.is_company_user:
        return redirect("/admin/users")
    old_client_id = user.client_id
    client_id = valid_client_id(request.form.get("client_id", ""))
    user.client_id = client_id
    if client_id != old_client_id:
        # The access checklist on screen was rendered for the *old* company,
        # so it can't be trusted here - just drop any restrictions that no
        # longer apply and let the next save (after the page reloads with
        # the new company's checklist) set access for it.
        allowed = set(store.get_client(client_id).dashboard_slugs) if client_id else set()
        user.restricted_dashboard_slugs = [slug for slug in user.restricted_dashboard_slugs if slug in allowed]
        store.upsert_user(sanitize_user_for_role(user))
        record_audit("user.client", target=uid, detail=f"client={client_id or '(none)'}")
        logger.info("Admin set user company uid=%s client=%s", uid, client_id)
    else:
        client = store.get_client(client_id) if client_id else None
        company = set(client.dashboard_slugs) if client is not None else set()
        # The checklist shows checked = has access, so anything left
        # unchecked out of the company's dashboards is what becomes restricted.
        has_access = {slug for slug in request.form.getlist("slugs") if slug in company}
        user.restricted_dashboard_slugs = sorted(company - has_access)
        store.upsert_user(sanitize_user_for_role(user))
        record_audit(
            "user.restrictions",
            target=uid,
            detail=f"slugs={','.join(user.restricted_dashboard_slugs)}",
        )
        logger.info("Admin set restrictions uid=%s slugs=%s", uid, user.restricted_dashboard_slugs)
    return redirect(f"/admin/users?uid={quote(uid)}")


@bp.route("/users/<uid>/role", methods=["POST"])
@admin_required
@csrf_protect
def users_role(uid: str):
    # Only the Operators page exposes a role-change control (Users page
    # rosters company users only, who are always role="user"), so this
    # always redirects back there, not to /admin/users.
    me = current_user()
    if me is not None and uid == me.uid:
        return redirect("/admin/operators")
    store = get_user_store()
    user = store.get_user(uid)
    if user is None:
        return redirect("/admin/operators")
    user.role = clean_role(request.form.get("role", "user"))
    store.upsert_user(sanitize_user_for_role(user))
    record_audit("user.role", target=uid, detail=f"role={user.role}")
    logger.info("Admin set role uid=%s role=%s", uid, user.role)
    return redirect(f"/admin/operators?uid={quote(uid)}")


@bp.route("/users/<uid>/disable", methods=["POST"])
@admin_required
@csrf_protect
def users_disable(uid: str):
    me = current_user()
    if me is not None and uid == me.uid:
        return redirect(f"/admin/users?uid={quote(uid)}")
    store = get_user_store()
    user = store.get_user(uid)
    if user is not None:
        user.disabled = not user.disabled
        store.upsert_user(user)
        record_audit("user.disable" if user.disabled else "user.enable", target=uid)
        logger.info("Admin set disabled uid=%s disabled=%s", uid, user.disabled)
    return redirect(f"/admin/users?uid={quote(uid)}")


@bp.route("/users/<uid>/delete", methods=["POST"])
@admin_required
@csrf_protect
def users_delete(uid: str):
    get_user_store().delete_user(uid)
    record_audit("user.delete", target=uid)
    logger.info("Admin deleted user uid=%s", uid)
    return redirect("/admin/users")  # selection cleared - that user is gone


@bp.route("/operators")
@admin_required
def operators():
    store = get_user_store()
    clients = {c.id: c for c in store.list_clients()}
    titles = dashboard_titles()
    q = request.args.get("q", "").strip().lower()
    me = current_user()

    roster = [u for u in store.list_users() if u.is_operator or u.is_admin]
    if q:
        roster = [u for u in roster if q in u.email.lower() or q in u.uid.lower()]
    roster.sort(key=lambda u: u.email.lower())

    sel_uid = request.args.get("uid", "") or (roster[0].uid if roster else "")

    def _row_meta(u: User) -> str:
        if u.is_admin:
            meta = "all dashboards"
        else:
            meta = f"{len(u.allowed_client_ids)} client{'' if len(u.allowed_client_ids) == 1 else 's'}"
        if is_pending(u.uid):
            meta += " · (invite pending)"
        if u.disabled:
            meta += " · (suspended)"
        return meta

    def _row_href(u: User) -> str:
        href = f"/admin/operators?uid={quote(u.uid)}"
        return f"{href}&q={quote(q)}" if q else href

    groups = {
        "Administrators": [u for u in roster if u.is_admin],
        "Operators": [u for u in roster if u.is_operator],
    }
    list_html = (
        "".join(
            f'<div class="md-group-label">{escape(label)} <span class="pill">{len(users_in)}</span></div>'
            + "".join(
                md_row(_row_href(u), u.uid == sel_uid, escape(u.email), _row_meta(u)) for u in users_in
            )
            for label, users_in in groups.items()
            if users_in
        )
        or '<p class="muted">No operators match that search.</p>'
    )

    selected = store.get_user(sel_uid) if sel_uid else None
    if selected is not None and not (selected.is_operator or selected.is_admin):
        selected = None
    detail_html = operator_detail(selected, clients, titles, me) if selected else MD_EMPTY

    search_form = (
        '<form class="admin-filter-row" method="get">'
        f'<input name="q" placeholder="Search by email or UID" value="{escape(q)}" style="min-width:260px">'
        "<button>Search</button>"
        + (' <a class="btn" href="/admin/operators"><button class="secondary">Clear</button></a>' if q else "")
        + "</form>"
    )

    create = (
        "<h3>Invite account</h3>"
        '<form class="inline" method="post" action="/admin/operators/create">'
        f"{csrf_input()}"
        '<label>Email<input name="email" type="email" required></label>'
        '<label>Type<select name="role"><option value="operator">operator</option>'
        '<option value="admin">admin</option></select></label>'
        "<button>Invite</button></form>"
    )

    body = (
        f'<div class="section">{section_title("Operators", include_back=True)}'
        '<p class="muted">Administrators and operators are the two non-company-scoped account types. Admins get '
        "every dashboard implicitly; operators get cross-client access to whole companies, inheriting every "
        "dashboard those companies own - the same model as a company user's own client.</p>"
        f"{search_form}{md_layout(list_html, detail_html)}</div><div class='section'>{create}</div>"
    )
    return admin_page("Operators", body)


@bp.route("/operators/create", methods=["POST"])
@admin_required
@csrf_protect
def operators_create():
    role = request.form.get("role", "operator")
    role = role if role in {"operator", "admin"} else "operator"
    email = request.form["email"].strip().lower()
    user = User(
        uid=f"{PENDING_PREFIX}{email}",
        email=email,
        role=role,
    )
    get_user_store().upsert_user(sanitize_user_for_role(user))
    record_audit(f"{role}.create", target=user.uid, detail=f"email={user.email}")
    logger.info("Admin invited %s email=%s", role, email)
    send_invite(email)
    return redirect(f"/admin/operators?uid={quote(user.uid)}")


@bp.route("/operators/<uid>/resend-invite", methods=["POST"])
@admin_required
@csrf_protect
def operators_resend_invite(uid: str):
    user = get_user_store().get_user(uid)
    if user is not None and is_pending(user.uid):
        send_invite(user.email)
        record_audit("operator.invite.resend", target=uid)
        logger.info("Admin resent invite uid=%s", uid)
    return redirect(f"/admin/operators?uid={quote(uid)}")


@bp.route("/operators/<uid>/access", methods=["POST"])
@admin_required
@csrf_protect
def operators_access(uid: str):
    store = get_user_store()
    user = store.get_user(uid)
    if user is None or not user.is_operator:
        return redirect("/admin/operators")
    valid = {c.id for c in store.list_clients()}
    user.allowed_client_ids = [cid for cid in request.form.getlist("client_ids") if cid in valid]
    store.upsert_user(sanitize_user_for_role(user))
    record_audit("operator.access", target=uid, detail=f"clients={','.join(user.allowed_client_ids)}")
    logger.info("Admin set operator access uid=%s clients=%s", uid, user.allowed_client_ids)
    return redirect(f"/admin/operators?uid={quote(uid)}")


@bp.route("/operators/<uid>/disable", methods=["POST"])
@admin_required
@csrf_protect
def operators_disable(uid: str):
    me = current_user()
    if me is not None and uid == me.uid:
        return redirect(f"/admin/operators?uid={quote(uid)}")
    store = get_user_store()
    user = store.get_user(uid)
    if user is not None and (user.is_operator or user.is_admin):
        user.disabled = not user.disabled
        store.upsert_user(user)
        record_audit("operator.disable" if user.disabled else "operator.enable", target=uid)
        logger.info("Admin set operator disabled uid=%s disabled=%s", uid, user.disabled)
    return redirect(f"/admin/operators?uid={quote(uid)}")


@bp.route("/operators/<uid>/delete", methods=["POST"])
@admin_required
@csrf_protect
def operators_delete(uid: str):
    get_user_store().delete_user(uid)
    record_audit("operator.delete", target=uid)
    logger.info("Admin deleted operator uid=%s", uid)
    return redirect("/admin/operators")


@bp.route("/clients")
@admin_required
def clients():
    store = get_user_store()
    dash_opts = dashboard_options()
    all_clients = sorted(store.list_clients(), key=lambda c: c.name.lower())
    sel_id = request.args.get("id", "") or (all_clients[0].id if all_clients else "")

    def _row_meta(client: Client) -> str:
        n = len(client.dashboard_slugs)
        return f"{n} dashboard{'' if n == 1 else 's'} · {escape(client.id)}"

    list_html = "".join(
        md_row(f"/admin/clients?id={quote(c.id)}", c.id == sel_id, escape(c.name), _row_meta(c))
        for c in all_clients
    ) or '<p class="muted">No clients yet.</p>'

    selected = next((c for c in all_clients if c.id == sel_id), None)
    detail_html = client_detail(selected, dash_opts) if selected else MD_EMPTY

    create = (
        "<h3>Add client</h3>"
        '<form class="inline" method="post" action="/admin/clients/create" enctype="multipart/form-data">'
        f"{csrf_input()}"
        '<label>ID<input name="id" required></label>'
        '<label>Name<input name="name" required></label>'
        '<label>BQ dataset<input name="bq_dataset" placeholder="(optional override)"></label>'
        '<label>Logo<input name="logo" type="file" accept="image/*"></label>'
        "<button>Create</button></form>"
    )
    body = (
        f'<div class="section">{section_title("Clients", include_back=True)}'
        '<p class="muted">Assign dashboards to a company. Each dashboard has one owner only, so saving here moves any '
        'selected dashboard off any other client automatically.</p>'
        f"{md_layout(list_html, detail_html)}</div><div class='section'>{create}</div>"
    )
    return admin_page("Clients", body)


@bp.route("/clients/create", methods=["POST"])
@admin_required
@csrf_protect
def clients_create():
    client = Client(
        id=request.form["id"].strip(),
        name=request.form["name"].strip(),
        bq_dataset=request.form.get("bq_dataset", "").strip(),
        logo_data_uri=logo_data_uri_from_upload(request.files.get("logo")),
    )
    get_user_store().upsert_client(client)
    record_audit("client.create", target=client.id, detail=f"name={client.name}")
    logger.info("Admin created client id=%s", client.id)
    return redirect(f"/admin/clients?id={quote(client.id)}")


@bp.route("/clients/<client_id>/save", methods=["POST"])
@admin_required
@csrf_protect
def clients_save(client_id: str):
    store = get_user_store()
    client = store.get_client(client_id)
    if client is not None:
        client.name = request.form.get("name", client.name).strip() or client.name
        client.bq_dataset = request.form.get("bq_dataset", "").strip()
        if request.form.get("remove_logo"):
            client.logo_data_uri = ""
        else:
            logo = logo_data_uri_from_upload(request.files.get("logo"))
            if logo:
                client.logo_data_uri = logo
        store.upsert_client(client)
        record_audit("client.update", target=client_id, detail=f"name={client.name}")
        logger.info("Admin updated client id=%s", client_id)

        valid = set(all_slugs())
        slugs = [slug for slug in request.form.getlist("slugs") if slug in valid]
        store.set_client_dashboards(client_id, slugs)
        record_audit("client.dashboards", target=client_id, detail=f"slugs={','.join(slugs)}")
        logger.info("Admin set client dashboards id=%s slugs=%s", client_id, slugs)
    return redirect(f"/admin/clients?id={quote(client_id)}")


@bp.route("/clients/<client_id>/delete", methods=["POST"])
@admin_required
@csrf_protect
def clients_delete(client_id: str):
    store = get_user_store()
    if store.get_client(client_id) is not None:
        if any(user.client_id == client_id for user in store.list_users() if user.is_company_user):
            return redirect(f"/admin/clients?id={quote(client_id)}")
        store.delete_client(client_id)
        record_audit("client.delete", target=client_id)
        logger.info("Admin deleted client id=%s", client_id)
    return redirect("/admin/clients")  # selection cleared if it was actually deleted


@bp.route("/dashboards")
@admin_required
def dashboards():
    store = get_user_store()
    clients = {c.id: c for c in store.list_clients()}
    owners = dashboard_owner_map()
    users = store.list_users()
    operators = [u for u in users if u.is_operator]
    dash_options = dashboard_options()

    sel_slug = request.args.get("slug", "") or (dash_options[0][0] if dash_options else "")

    def _row_meta(slug: str) -> str:
        owner_id = owners.get(slug, "")
        return clients[owner_id].name if owner_id in clients else "unassigned"

    list_html = "".join(
        md_row(f"/admin/dashboards?slug={quote(slug)}", slug == sel_slug, escape(title), escape(_row_meta(slug)))
        for slug, title in dash_options
    ) or '<p class="muted">No dashboards registered.</p>'

    titles = dict(dash_options)
    detail_html = (
        dashboard_detail(sel_slug, titles.get(sel_slug, sel_slug), owners.get(sel_slug, ""), clients, users, operators)
        if sel_slug
        else MD_EMPTY
    )

    body = (
        f'<div class="section">{section_title("Dashboards", include_back=True)}'
        '<p class="muted">Manage dashboard ownership and access from the dashboard point of view. Every company '
        "user has access by default; uncheck someone to remove it. Operators inherit access via their client "
        'scope, managed on the <a href="/admin/operators">Operators</a> page.</p>'
        f"{md_layout(list_html, detail_html)}</div>"
    )
    return admin_page("Dashboards", body)


@bp.route("/dashboards/<slug>/save", methods=["POST"])
@admin_required
@csrf_protect
def dashboards_save(slug: str):
    if slug not in set(all_slugs()):
        return redirect("/admin/dashboards")
    old_owner_id = dashboard_owner_map().get(slug, "")
    client_id = valid_client_id(request.form.get("client_id", ""))
    assign_dashboard_owner(slug, client_id)
    record_audit("dashboard.owner", target=slug, detail=f"client={client_id or '(none)'}")
    logger.info("Admin set dashboard owner slug=%s client=%s", slug, client_id)

    if client_id and client_id == old_owner_id:
        # The access checklist on screen was rendered for this same owner,
        # so it can be trusted here. If the owner is changing instead, skip
        # it - the checklist reflected the *old* owner's company users, and
        # the next save (after the page reloads with the new owner's
        # checklist) is what sets access for the new owner.
        store = get_user_store()
        company_users = [u for u in store.list_users() if u.is_company_user and u.client_id == client_id]
        has_access = {uid for uid in request.form.getlist("uids") if any(u.uid == uid for u in company_users)}
        # The checklist shows checked = has access, so unchecked users are
        # who gets added to/kept in restricted_dashboard_slugs.
        for user in company_users:
            restricted = set(user.restricted_dashboard_slugs)
            if user.uid in has_access:
                restricted.discard(slug)
            else:
                restricted.add(slug)
            user.restricted_dashboard_slugs = sorted(restricted)
            store.upsert_user(sanitize_user_for_role(user))
        record_audit("dashboard.restrictions", target=slug, detail=f"uids={','.join(sorted(has_access))}")
        logger.info("Admin set dashboard access slug=%s uids=%s", slug, sorted(has_access))
    return redirect(f"/admin/dashboards?slug={quote(slug)}")


@bp.route("/audit")
@admin_required
def audit():
    store = get_user_store()
    q = request.args.get("q", "").strip().lower()
    try:
        page_num = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page_num = 1

    events = store.list_audit_events(limit=1000)
    if q:
        events = [
            event
            for event in events
            if q in event.actor_email.lower()
            or q in event.actor_uid.lower()
            or q in event.action.lower()
            or q in event.target.lower()
            or q in event.detail.lower()
        ]

    total_pages = max(1, (len(events) + _AUDIT_PAGE_SIZE - 1) // _AUDIT_PAGE_SIZE)
    page_num = min(page_num, total_pages)
    page_events = events[(page_num - 1) * _AUDIT_PAGE_SIZE : page_num * _AUDIT_PAGE_SIZE]

    if page_events:
        rows = "".join(
            f"<tr><td class='muted'>{escape(event.created_at)}</td>"
            f"<td>{escape(event.actor_email) or escape(event.actor_uid)}</td>"
            f"<td><code>{escape(event.action)}</code></td>"
            f"<td>{escape(event.target) or '-'}</td>"
            f"<td class='muted'>{escape(event.detail) or '-'}</td></tr>"
            for event in page_events
        )
        table = (
            "<table><tr><th>Time (UTC)</th><th>Actor</th><th>Action</th>"
            f"<th>Target</th><th>Detail</th></tr>{rows}</table>"
        )
    else:
        table = '<p class="muted">No audit events match.</p>'

    def _page_link(label: str, number: int, enabled: bool) -> str:
        if not enabled:
            return f'<span class="muted">{label}</span>'
        href = f"/admin/audit?page={number}" + (f"&q={quote(q)}" if q else "")
        return f'<a class="btn" href="{href}"><button class="secondary">{label}</button></a>'

    pager = (
        '<div class="admin-pager">'
        f"{_page_link('&larr; Newer', page_num - 1, page_num > 1)}"
        f'<span class="muted">Page {page_num} of {total_pages} · {len(events)} matching events</span>'
        f"{_page_link('Older &rarr;', page_num + 1, page_num < total_pages)}"
        "</div>"
    )
    search_form = (
        '<form class="admin-filter-row" method="get">'
        f'<input name="q" placeholder="Search actor, action, target, detail" value="{escape(q)}" style="min-width:300px">'
        "<button>Search</button>"
        + (' <a class="btn" href="/admin/audit"><button class="secondary">Clear</button></a>' if q else "")
        + "</form>"
    )
    body = (
        f'<div class="section">{section_title("Audit log", include_back=True)}'
        '<p class="muted">Most recent administrative actions (newest first).</p>'
        f"{search_form}{table}{pager}</div>"
    )
    return admin_page("Audit log", body)


@bp.route("/usage")
@admin_required
def usage():
    store = get_user_store()
    events = store.list_usage_events(limit=5000)
    titles = dashboard_titles()

    agg: dict[str, dict] = {}
    for event in events:
        entry = agg.setdefault(event.slug, {"opens": 0, "users": set(), "last": ""})
        entry["opens"] += 1
        entry["users"].add(event.uid)
        if event.created_at > entry["last"]:
            entry["last"] = event.created_at

    if agg:
        ordered = sorted(agg.items(), key=lambda kv: kv[1]["opens"], reverse=True)
        rows = "".join(
            f"<tr><td>{escape(titles.get(slug, slug))}<br><span class='muted'>{escape(slug)}</span></td>"
            f"<td>{data['opens']}</td><td>{len(data['users'])}</td>"
            f"<td class='muted'>{escape(data['last'])}</td></tr>"
            for slug, data in ordered
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
        f'<div class="section">{section_title("Usage analytics", include_back=True)}'
        '<p class="muted">Dashboard opens by HTML page load.</p>'
        f"{table}{total}</div>"
    )
    return admin_page("Usage", body)


@bp.route("/health")
@admin_required
def health():
    rows = []
    for entry in registry():
        title = escape(entry.manifest.title)
        if entry.data_health is not None:
            try:
                sources = entry.data_health()
            except Exception as exc:  # noqa: BLE001
                rows.append(
                    f"<tr><td>{title}</td><td>(health check)</td>"
                    f"<td><span class='status-error'>error</span></td>"
                    f"<td class='muted'>{escape(type(exc).__name__)}: {escape(str(exc))}</td>"
                    "<td>-</td></tr>"
                )
                continue
            for source in sources:
                rows.append(
                    f"<tr><td>{title}</td><td>{escape(source.name)}</td>"
                    f"<td><span class='status-{escape(source.status)}'>{escape(source.status)}</span></td>"
                    f"<td class='muted'>{escape(source.detail) or '-'}</td>"
                    f"<td class='muted'>{('rows=' + str(source.rows)) if source.rows is not None else ''}"
                    f"{(' · ' + escape(source.as_of)) if source.as_of else ''}</td></tr>"
                )
        else:
            for req in entry.manifest.data_requirements or ["(unspecified)"]:
                rows.append(
                    f"<tr><td>{title}</td><td>{escape(req)}</td>"
                    "<td><span class='muted'>unknown</span></td>"
                    "<td class='muted'>No health probe defined.</td><td>-</td></tr>"
                )

    table = (
        "<table><tr><th>Dashboard</th><th>Source</th><th>Status</th><th>Detail</th><th>Info</th></tr>"
        f"{''.join(rows)}</table>"
    )
    body = (
        f'<div class="section">{section_title("Data-source health", include_back=True)}'
        '<p class="muted">Live probe of each dashboard\'s data dependencies.</p>'
        f"{table}</div>"
    )
    return admin_page("Data health", body)
