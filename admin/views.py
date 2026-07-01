"""
Admin panel: HTML-rendering helpers (no HTTP routing - that's admin/routes.py;
no business logic - that's admin/services.py).

Generic list/detail-panel widgets, plus the per-page detail-panel builders
(one render function per master-detail page: users, operators, clients,
dashboards). Split out of admin/routes.py once that file grew past 1100 lines
mixing routing, presentation, and business logic.
"""

from __future__ import annotations

from markupsafe import escape

from auth.middleware import current_user
from pages_landing.shell import page
from security import csrf_input
from tenancy.models import Client, User

from admin.services import VALID_ROLES, effective_company_dashboards, is_pending

_BACK_LINK = (
    '<a class="admin-section-back" href="/admin">'
    '<span aria-hidden="true">&larr;</span> Back'
    "</a>"
)

MD_EMPTY = '<div class="md-empty">Select an item from the list to manage it.</div>'


def admin_page(title: str, body: str):
    return page(title, body, user=current_user(), page_class="admin-shell")


def section_title(title: str, *, include_back: bool = False) -> str:
    back = _BACK_LINK if include_back else ""
    return (
        '<div class="admin-section-head">'
        f"<h2>{escape(title)}</h2>"
        f"{back}"
        "</div>"
    )


def pill_list(slugs: list[str], titles: dict[str, str], *, prefix: str = "") -> str:
    return "".join(
        f'<span class="pill">{escape(prefix)}{escape(titles.get(slug, slug))}</span>'
        for slug in slugs
    )


def checklist(name: str, options: list[tuple[str, str]], selected: set[str]) -> str:
    """Stacked, scrollable checkbox list instead of a <select multiple>
    listbox. Lives inside a detail panel with room to breathe, so unlike the
    old inline-in-a-table-cell picker it doesn't need to collapse - the
    panel itself doesn't change size when you check something."""
    if not options:
        return '<span class="muted">none available</span>'
    items = "".join(
        f'<label class="checklist-item">'
        f'<input type="checkbox" name="{escape(name)}" value="{escape(value)}"'
        f'{" checked" if value in selected else ""}> {escape(label)}</label>'
        for value, label in options
    )
    return f'<div class="checklist">{items}</div>'


def md_row(href: str, active: bool, title_html: str, meta_html: str = "") -> str:
    """One row in a master-detail list panel - a plain link, so selecting a
    different row never changes this row's own height (no inline editor
    lives here; that's all in the detail panel)."""
    cls = "md-row active" if active else "md-row"
    meta = f'<span class="md-row-meta">{meta_html}</span>' if meta_html else ""
    return f'<a class="{cls}" href="{href}"><span class="md-row-title">{title_html}</span>{meta}</a>'


def md_layout(list_html: str, detail_html: str) -> str:
    """Master-detail shell: a compact, fixed-row-height list on the left and
    one stable detail panel on the right - editing never reflows the list,
    and the list never grows/shrinks the detail area."""
    return (
        '<div class="md-layout">'
        f'<div class="md-list">{list_html}</div>'
        f'<div class="md-detail">{detail_html}</div>'
        "</div>"
    )


def user_detail(u: User, clients: dict[str, Client], titles: dict[str, str], me: User | None) -> str:
    client_opts = '<option value="">- none -</option>' + "".join(
        f'<option value="{escape(cid)}"{" selected" if u.client_id == cid else ""}>{escape(c.name)}</option>'
        for cid, c in clients.items()
    )
    company_field = f"<select name='client_id'>{client_opts}</select>"

    effective = effective_company_dashboards(u, clients)
    effective_html = pill_list(effective, titles) or '<span class="muted">none</span>'
    if u.legacy_dashboard_slugs:
        legacy = pill_list(u.legacy_dashboard_slugs, titles, prefix="legacy ")
        effective_html += f"<div class='muted'>Legacy direct grants pending review: {legacy or 'present'}</div>"

    client = clients.get(u.client_id)
    company = list(client.dashboard_slugs) if client else []
    if not company:
        access_field = '<span class="muted">Assign a company first.</span>'
    else:
        restricted = set(u.restricted_dashboard_slugs)
        selected_slugs = {slug for slug in company if slug not in restricted}
        options = [(slug, titles.get(slug, slug)) for slug in company]
        access_field = checklist("slugs", options, selected_slugs)

    form_id = f"user-save-{escape(u.uid)}"
    save_form = (
        f"<form id='{form_id}' class='detail-form' method='post' action='/admin/users/{escape(u.uid)}/save'>"
        f"{csrf_input()}"
        f"<div class='detail-field'><label>Company</label>{company_field}</div>"
        f"<div class='detail-field'><label>Access</label>{access_field}</div>"
        "</form>"
    )

    actions = [f"<button form='{form_id}'>Save</button>"]
    is_self = me is not None and u.uid == me.uid
    pending = is_pending(u.uid)
    if pending:
        actions.append(
            f"<form method='post' action='/admin/users/{escape(u.uid)}/resend-invite'>"
            f"{csrf_input()}<button class='secondary'>Resend invite</button></form>"
        )
    if not (u.disabled or is_self):
        actions.append(f"<a class='btn' href='/dev/as/{escape(u.uid)}'><button class='secondary'>View as</button></a>")
    if not is_self:
        label = "Reactivate" if u.disabled else "Suspend"
        confirm = "" if u.disabled else f" onsubmit=\"return confirm('Suspend {escape(u.email)}?')\""
        actions.append(
            f"<form method='post' action='/admin/users/{escape(u.uid)}/disable'{confirm}>"
            f"{csrf_input()}<button class='secondary'>{label}</button></form>"
        )
    actions.append(
        f"<form method='post' action='/admin/users/{escape(u.uid)}/delete' "
        f"onsubmit=\"return confirm('Delete {escape(u.email)}?')\">"
        f"{csrf_input()}<button class='secondary'>Delete</button></form>"
    )

    suspended_pill = ' <span class="pill">suspended</span>' if u.disabled else ""
    suspended_pill += ' <span class="pill">invite pending</span>' if pending else ""
    return (
        f"<div class='detail-head'><h3>{escape(u.email)}{suspended_pill}</h3>"
        f"<span class='muted'>{escape(u.uid)}</span></div>"
        f"<div class='detail-field'><label>Accessible dashboards</label>{effective_html}</div>"
        f"{save_form}"
        f"<div class='detail-actions'>{''.join(actions)}</div>"
    )


def operator_detail(u: User, clients: dict[str, Client], titles: dict[str, str], me: User | None) -> str:
    is_self = me is not None and u.uid == me.uid
    form_id = f"operator-save-{escape(u.uid)}"
    save_button = ""

    if u.is_admin:
        if is_self:
            type_html = f"<span class='muted' title=\"Can't change your own role\">{escape(u.role)}</span>"
        else:
            opts = "".join(
                f'<option value="{role}"{" selected" if u.role == role else ""}>{escape(role)}</option>'
                for role in sorted(VALID_ROLES)
            )
            type_html = (
                f"<form id='{form_id}' class='inline' method='post' action='/admin/users/{escape(u.uid)}/role'>"
                f"{csrf_input()}<select name='role'>{opts}</select>"
                "</form>"
            )
            save_button = f"<button form='{form_id}'>Save</button>"
        access_html = '<span class="muted">all (admin)</span>'
        effective_html = '<span class="muted">all (admin)</span>'
    else:
        type_html = "<span class='pill'>operator</span>"
        client_opts = [(c.id, c.name) for c in clients.values()]
        selected_ids = set(u.allowed_client_ids)
        access_html = (
            f"<form id='{form_id}' method='post' action='/admin/operators/{escape(u.uid)}/access'>"
            f"{csrf_input()}{checklist('client_ids', client_opts, selected_ids)}"
            "</form>"
        )
        save_button = f"<button form='{form_id}'>Save access</button>"
        effective: set[str] = set()
        for cid in u.allowed_client_ids:
            client = clients.get(cid)
            if client:
                effective.update(client.dashboard_slugs)
        effective_html = pill_list(sorted(effective), titles) or '<span class="muted">none</span>'

    pending = is_pending(u.uid)
    actions = [save_button] if save_button else []
    if pending:
        actions.append(
            f"<form method='post' action='/admin/operators/{escape(u.uid)}/resend-invite'>"
            f"{csrf_input()}<button class='secondary'>Resend invite</button></form>"
        )
    if not (u.disabled or is_self):
        actions.append(f"<a class='btn' href='/dev/as/{escape(u.uid)}'><button class='secondary'>View as</button></a>")
    if not is_self:
        label = "Reactivate" if u.disabled else "Suspend"
        confirm = "" if u.disabled else f" onsubmit=\"return confirm('Suspend {escape(u.email)}?')\""
        actions.append(
            f"<form method='post' action='/admin/operators/{escape(u.uid)}/disable'{confirm}>"
            f"{csrf_input()}<button class='secondary'>{label}</button></form>"
        )
    actions.append(
        f"<form method='post' action='/admin/operators/{escape(u.uid)}/delete' "
        f"onsubmit=\"return confirm('Delete {escape(u.email)}?')\">"
        f"{csrf_input()}<button class='secondary'>Delete</button></form>"
    )

    suspended_pill = ' <span class="pill">suspended</span>' if u.disabled else ""
    suspended_pill += ' <span class="pill">invite pending</span>' if pending else ""
    return (
        f"<div class='detail-head'><h3>{escape(u.email)}{suspended_pill}</h3>"
        f"<span class='muted'>{escape(u.uid)}</span></div>"
        f"<div class='detail-field'><label>Type</label>{type_html}</div>"
        f"<div class='detail-field'><label>Client access</label>{access_html}</div>"
        f"<div class='detail-field'><label>Accessible dashboards</label>{effective_html}</div>"
        f"<div class='detail-actions'>{''.join(actions)}</div>"
    )


def client_detail(client: Client, dash_opts: list[tuple[str, str]]) -> str:
    logo_preview = (
        f"<img src='{escape(client.logo_data_uri)}' alt='' "
        "style='height:48px;width:48px;object-fit:contain;border-radius:8px;"
        "background:rgba(255,255,255,0.04)'>"
        if client.logo_data_uri
        else "<span class='muted'>no logo</span>"
    )
    remove_checkbox = (
        "<label style='flex-direction:row;gap:6px'>"
        "<input type='checkbox' name='remove_logo' value='1'> Remove logo</label>"
        if client.logo_data_uri
        else ""
    )
    selected = set(client.dashboard_slugs)
    form_id = f"client-save-{escape(client.id)}"
    save_form = (
        f"<form id='{form_id}' class='detail-form' method='post' action='/admin/clients/{escape(client.id)}/save' "
        "enctype='multipart/form-data'>"
        f"{csrf_input()}"
        f"<label>Name<input name='name' value='{escape(client.name)}' required></label>"
        f"<label>BQ dataset<input name='bq_dataset' value='{escape(client.bq_dataset)}' "
        "placeholder='(convention)'></label>"
        f"<label>Logo {logo_preview}<input name='logo' type='file' accept='image/*'></label>"
        f"{remove_checkbox}"
        f"<div class='detail-field'><label>Dashboards</label>{checklist('slugs', dash_opts, selected)}</div>"
        "</form>"
    )
    delete_form = (
        f"<form method='post' action='/admin/clients/{escape(client.id)}/delete' "
        f"onsubmit=\"return confirm('Delete {escape(client.name)}? Users still assigned to it must be "
        "reassigned first.')\">"
        f"{csrf_input()}<button class='secondary'>Delete</button></form>"
    )

    return (
        f"<div class='detail-head'><h3>{escape(client.name)}</h3>"
        f"<span class='muted'>{escape(client.id)}</span></div>"
        f"{save_form}"
        f"<div class='detail-actions'><button form='{form_id}'>Save</button>{delete_form}</div>"
    )


def dashboard_detail(
    slug: str,
    title: str,
    owner_id: str,
    clients: dict[str, Client],
    users: list[User],
    operators: list[User],
) -> str:
    owner_opts = '<option value="">- unassigned -</option>' + "".join(
        f'<option value="{escape(cid)}"{" selected" if owner_id == cid else ""}>{escape(client.name)}</option>'
        for cid, client in clients.items()
    )
    owner_field = f"<select name='client_id'>{owner_opts}</select>"

    if not owner_id:
        access_field = '<span class="muted">Assign an owner company first.</span>'
        operators_html = '<span class="muted">Assign an owner company first.</span>'
    else:
        company_users = [u for u in users if u.is_company_user and u.client_id == owner_id]
        if not company_users:
            access_field = '<span class="muted">No company users yet.</span>'
        else:
            # Checked = has access (the default); unchecking someone here is
            # what adds them to their restricted_dashboard_slugs.
            selected = {u.uid for u in company_users if slug not in u.restricted_dashboard_slugs}
            options = [(u.uid, u.email) for u in company_users]
            access_field = checklist("uids", options, selected)

        granted = [u for u in operators if owner_id in u.allowed_client_ids]
        operators_html = (
            pill_list([u.uid for u in granted], {u.uid: u.email for u in granted})
            if granted
            else '<span class="muted">none</span>'
        )

    form_id = f"dashboard-save-{escape(slug)}"
    save_form = (
        f"<form id='{form_id}' class='detail-form' method='post' action='/admin/dashboards/{escape(slug)}/save'>"
        f"{csrf_input()}"
        f"<div class='detail-field'><label>Owner company</label>{owner_field}</div>"
        f"<div class='detail-field'><label>Company-user access</label>{access_field}</div>"
        "</form>"
    )

    return (
        f"<div class='detail-head'><h3>{escape(title)}</h3>"
        f"<span class='muted'>{escape(slug)}</span></div>"
        f"{save_form}"
        f"<div class='detail-field'><label>Operators with access</label>{operators_html}</div>"
        f"<div class='detail-actions'><button form='{form_id}'>Save</button></div>"
    )
