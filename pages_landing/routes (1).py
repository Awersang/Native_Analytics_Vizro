"""
Public-facing routes: the user panel (landing), login and logout.

The landing page is the curated "user panel": it lists exactly the dashboards
the current user may open. Login uses Firebase when ``AUTH_ENABLED=true`` and is
a no-op redirect in dev.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from flask import Blueprint, Response, abort, redirect, request
from markupsafe import escape

from auth.middleware import current_user, login_required
from config import settings
from pages_landing.shell import page
from security import csrf_input, csrf_protect
from tenancy.access import accessible_slugs

bp = Blueprint("landing", __name__)

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")


def _branding(user) -> tuple[str, str]:
    """Resolve (brand_name, accent_color) for a user's tenant.

    The accent is validated against a strict hex pattern so a malformed/hostile
    client record can never inject arbitrary CSS into the shell.
    """
    try:
        if user is None or not getattr(user, "client_id", ""):
            return "", ""
        client = _store().get_client(user.client_id)
        if client is None:
            return "", ""
        accent = client.accent_color if _HEX_COLOR.match(client.accent_color or "") else ""
        return client.brand_name or "", accent
    except Exception:
        return "", ""


def _registry():
    # Import the cached registry from the dashboards package (NOT from `app`),
    # so a request never re-executes app.py and rebuilds Vizro.
    from dashboards import get_registry

    return get_registry()


@bp.route("/")
@login_required
def index():
    user = current_user()
    registry = _registry()
    all_slugs = [d.manifest.slug for d in registry]
    visible = set(accessible_slugs(user, all_slugs))

    cards = []
    def _card_html(m):
        href = f"{settings.vizro_mount_prefix.rstrip('/')}{m.base_path}"
        return (
            f'<a class="card" data-slug="{escape(m.slug)}" data-title="{escape(m.title)}" '
            f'data-category="{escape(m.category)}" '
            f'href="{escape(href)}" onclick="naRecordRecent(\'{escape(m.slug)}\')">'
            f'<button type="button" class="fav-star" data-slug="{escape(m.slug)}" '
            f'onclick="naToggleFav(event, \'{escape(m.slug)}\')" title="Toggle favourite">&#9734;</button>'
            f"<h3>{escape(m.title)}</h3><p>{escape(m.description)}</p></a>"
        )

    # Group visible dashboards by category, preserving registry (title) order.
    categories: dict[str, list[str]] = {}
    for d in registry:
        if d.manifest.slug not in visible:
            continue
        categories.setdefault(d.manifest.category or "General", []).append(_card_html(d.manifest))

    sections = []
    if categories:
        search = (
            '<input id="dash-search" type="search" placeholder="Search dashboards…" '
            'oninput="naFilterCards(this.value)" style="width:100%;max-width:360px;margin-bottom:18px;">'
        )
        cat_blocks = "".join(
            f'<div class="cat-section"><h3 class="muted cat-heading">{escape(cat)}</h3>'
            f'<div class="grid">{"".join(cat_cards)}</div></div>'
            for cat, cat_cards in categories.items()
        )
        sections.append(
            '<div class="section"><h2>Your dashboards</h2>'
            '<p class="muted">Choose a dashboard to open. Click the star to favourite one.</p>'
            f"{search}"
            '<div id="fav-section" class="section" style="display:none">'
            '<h3 class="muted">Favourites</h3><div class="grid" id="fav-grid"></div></div>'
            '<div id="recent-section" class="section" style="display:none">'
            '<h3 class="muted">Recently opened</h3><div class="grid" id="recent-grid"></div></div>'
            f'<div id="dash-all">{cat_blocks}</div>'
            '<p class="muted" id="no-results" style="display:none">No dashboards match your search.</p>'
            "</div>"
        )
    else:
        sections.append(
            '<div class="section"><h2>No dashboards yet</h2>'
            '<p class="muted">You have not been granted access to any dashboard.</p></div>'
        )

    # Self-service access requests: dashboards the user cannot yet open.
    if not user.is_admin:
        store = _store()
        pending = {r.slug for r in store.list_access_requests("pending") if r.uid == user.uid}
        request_rows = []
        for d in registry:
            m = d.manifest
            if m.slug in visible:
                continue
            if m.slug in pending:
                state = '<span class="pill">Requested · pending</span>'
            else:
                state = (
                    f'<form class="inline" method="post" action="/request-access">'
                    f"{csrf_input()}"
                    f'<input type="hidden" name="slug" value="{escape(m.slug)}">'
                    f'<button type="submit" class="secondary">Request access</button></form>'
                )
            request_rows.append(
                f"<tr><td>{escape(m.title)}</td>"
                f'<td class="muted">{escape(m.description)}</td>'
                f"<td>{state}</td></tr>"
            )
        if request_rows:
            sections.append(
                '<div class="section"><h2>Request access</h2>'
                '<p class="muted">Ask an administrator to grant you these dashboards.</p>'
                "<table><thead><tr><th>Dashboard</th><th>Description</th><th></th></tr></thead>"
                f'<tbody>{"".join(request_rows)}</tbody></table></div>'
            )

    body = "".join(sections) + _PANEL_JS
    brand, accent = _branding(user)
    return page("Dashboards", body, user=user, accent=accent, brand=brand)


@bp.route("/account")
@login_required
def account():
    user = current_user()
    registry = _registry()
    all_slugs = [d.manifest.slug for d in registry]
    titles = {d.manifest.slug: d.manifest.title for d in registry}
    visible = accessible_slugs(user, all_slugs)

    grants = (
        "".join(f'<span class="pill">{escape(titles.get(s, s))}</span>' for s in visible)
        or '<span class="muted">None</span>'
    )
    role_label = "Administrator" if user.is_admin else "User"
    rows = [
        ("Email", escape(user.email or "—")),
        ("Name", escape(user.display_name or "—")),
        ("Role", escape(role_label)),
        ("Client / tenant", escape(user.client_id or "—")),
        ("Dashboards", grants),
    ]
    table = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    body = (
        '<div class="section"><h2>My account</h2>'
        '<p class="muted">Your profile and the dashboards you can access.</p>'
        f"<table>{table}</table></div>"
    )
    brand, accent = _branding(user)
    return page("My account", body, user=user, accent=accent, brand=brand)


@bp.route("/request-access", methods=["POST"])
@login_required
@csrf_protect
def request_access():
    user = current_user()
    slug = request.form.get("slug", "").strip()
    registry = _registry()
    all_slugs = {d.manifest.slug for d in registry}
    visible = set(accessible_slugs(user, list(all_slugs)))
    # Only allow requesting a real dashboard the user cannot already open.
    if slug in all_slugs and slug not in visible and not user.is_admin:
        from tenancy.models import AccessRequest

        store = _store()
        store.add_access_request(
            AccessRequest(
                uid=user.uid,
                email=user.email,
                slug=slug,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    return redirect("/")


def _store():
    from tenancy.users import get_user_store

    return get_user_store()


_PANEL_JS = """
<script>
(function () {
  const FAVS = "na_favs", RECENT = "na_recent";
  function read(key) { try { return JSON.parse(localStorage.getItem(key)) || []; } catch (e) { return []; } }
  function write(key, v) { localStorage.setItem(key, JSON.stringify(v)); }

  window.naToggleFav = function (ev, slug) {
    ev.preventDefault(); ev.stopPropagation();
    let favs = read(FAVS);
    favs = favs.includes(slug) ? favs.filter(s => s !== slug) : favs.concat([slug]);
    write(FAVS, favs);
    render();
  };
  window.naRecordRecent = function (slug) {
    let recent = read(RECENT).filter(s => s !== slug);
    recent.unshift(slug);
    write(RECENT, recent.slice(0, 4));
  };
  window.naFilterCards = function (q) {
    q = (q || "").toLowerCase();
    let shown = 0;
    document.querySelectorAll("#dash-all .card").forEach(c => {
      const t = (c.dataset.title + " " + c.dataset.category + " " + c.textContent).toLowerCase();
      const match = t.includes(q);
      c.style.display = match ? "" : "none";
      if (match) shown++;
    });
    // Hide category headings whose cards are all filtered out.
    document.querySelectorAll("#dash-all .cat-section").forEach(sec => {
      const anyVisible = Array.from(sec.querySelectorAll(".card"))
        .some(c => c.style.display !== "none");
      sec.style.display = anyVisible ? "" : "none";
    });
    const nr = document.getElementById("no-results");
    if (nr) nr.style.display = shown === 0 ? "" : "none";
  };

  function cloneInto(gridId, slugs) {
    const grid = document.getElementById(gridId);
    if (!grid) return 0;
    grid.innerHTML = "";
    let n = 0;
    slugs.forEach(slug => {
      const src = document.querySelector('#dash-all .card[data-slug="' + CSS.escape(slug) + '"]');
      if (src) { grid.appendChild(src.cloneNode(true)); n++; }
    });
    return n;
  }
  function markStars() {
    const favs = read(FAVS);
    document.querySelectorAll(".fav-star").forEach(b => {
      const on = favs.includes(b.dataset.slug);
      b.innerHTML = on ? "\\u2605" : "\\u2606";
      b.classList.toggle("on", on);
    });
  }
  function render() {
    const favs = read(FAVS).filter(s => document.querySelector('#dash-all .card[data-slug="' + CSS.escape(s) + '"]'));
    const recent = read(RECENT).filter(s => document.querySelector('#dash-all .card[data-slug="' + CSS.escape(s) + '"]'));
    const fs = document.getElementById("fav-section");
    if (fs) { cloneInto("fav-grid", favs); fs.style.display = favs.length ? "" : "none"; }
    const rs = document.getElementById("recent-section");
    if (rs) { cloneInto("recent-grid", recent); rs.style.display = recent.length ? "" : "none"; }
    markStars();
  }
  document.addEventListener("DOMContentLoaded", render);
})();
</script>
<style>
  .card { position: relative; }
  .cat-section { margin-bottom:24px; }
  .cat-heading { margin:0 0 10px; text-transform:uppercase; letter-spacing:.04em; font-size:12px; }
  .fav-star { position:absolute; top:12px; right:12px; background:transparent; border:none;
              color:#caca40; font-size:20px; line-height:1; padding:0; cursor:pointer; }
  .fav-star:hover { color:#ffd700; background:transparent; }
  .fav-star.on { color:#ffd700; }
</style>
"""



# ── Login / logout ────────────────────────────────────────────────────────────
_LOGIN_HTML = """
<h2>Sign in</h2>
<p class="muted">Sign in with your account to continue.</p>
<div id="firebaseui"></div>
<script type="module">
  import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
  import {{ getAuth, GoogleAuthProvider, signInWithPopup }}
    from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
  const app = initializeApp({{ apiKey: "{api_key}", authDomain: "{auth_domain}" }});
  const auth = getAuth(app);
  const root = document.getElementById("firebaseui");
  const btn = document.createElement("button");
  btn.textContent = "Sign in with Google";
  btn.onclick = async () => {{
    const cred = await signInWithPopup(auth, new GoogleAuthProvider());
    const idToken = await cred.user.getIdToken();
    const r = await fetch("/sessionLogin", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ idToken }}),
    }});
    if (r.ok) window.location = "{next}";
    else root.insertAdjacentHTML("beforeend", "<p style='color:#f55'>Sign-in failed.</p>");
  }};
  root.appendChild(btn);
</script>
"""


@bp.route("/login")
def login():
    if not settings.auth_enabled:
        return redirect(request.args.get("next", "/"))
    nxt = request.args.get("next", "/")
    body = _LOGIN_HTML.format(
        api_key=settings.firebase_api_key,
        auth_domain=settings.firebase_auth_domain,
        next=nxt,
    )
    return page("Sign in", body)


@bp.route("/sessionLogin", methods=["POST"])
def session_login():
    if not settings.auth_enabled:
        return Response(status=204)
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken", "")
    try:
        from auth.firebase import create_session_cookie, verify_id_token

        verify_id_token(id_token)  # validate before minting a session cookie
        cookie, ttl = create_session_cookie(id_token)
    except Exception:
        return Response("Invalid token", status=401)

    resp = Response(status=200)
    resp.set_cookie(
        settings.session_cookie_name,
        cookie,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=not settings.is_dev,
        samesite="Lax",
    )
    return resp


@bp.route("/logout")
def logout():
    resp = redirect("/login")
    resp.delete_cookie(settings.session_cookie_name)
    return resp


# ── Dev-only "View as" switcher (active only when AUTH_ENABLED=false) ──────────
_DEV_COOKIE = "na_dev_as"


@bp.route("/dev")
def dev_switch():
    """Pick which fixture user to impersonate so both the user and admin UIs
    are reachable in local development. 404s entirely when real auth is on."""
    if settings.auth_enabled:
        abort(404)
    store = _store()
    cur = current_user()
    # Admins first, then by email, for a stable, readable list.
    people = sorted(store.list_users(), key=lambda u: (not u.is_admin, u.email))
    rows = []
    for u in people:
        is_cur = cur is not None and cur.uid == u.uid
        role = "admin" if u.is_admin else (u.client_id or "user")
        action = (
            '<span class="pill">current</span>'
            if is_cur
            else f'<a class="btn" href="/dev/as/{escape(u.uid)}"><button>View as</button></a>'
        )
        rows.append(
            f"<tr><td>{escape(u.email)}<br><span class='muted'>{escape(u.uid)}</span></td>"
            f"<td>{escape(role)}</td><td>{action}</td></tr>"
        )
    body = (
        '<div class="section"><h2>Dev: view as user</h2>'
        '<p class="muted">Development helper (AUTH_ENABLED=false). Impersonate any '
        "fixture user to see their experience, then switch back to the admin.</p>"
        "<table><tr><th>User</th><th>Role / company</th><th></th></tr>"
        f"{''.join(rows)}</table>"
        '<p style="margin-top:16px"><a class="btn" href="/dev/exit">'
        '<button class="secondary">Reset to Dev Admin</button></a></p></div>'
    )
    return page("Dev switcher", body, user=cur)


@bp.route("/dev/as/<uid>")
def dev_become(uid: str):
    if settings.auth_enabled:
        abort(404)
    resp = redirect("/")
    if _store().get_user(uid) is not None:
        resp.set_cookie(_DEV_COOKIE, uid, httponly=True, samesite="Lax")
    return resp


@bp.route("/dev/exit")
def dev_exit():
    if settings.auth_enabled:
        abort(404)
    resp = redirect("/")
    resp.delete_cookie(_DEV_COOKIE)
    return resp
