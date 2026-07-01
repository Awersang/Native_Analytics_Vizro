"""
Public-facing routes: the Client Hub, login and logout.

The Client Hub is the curated home page: it lists exactly the dashboards the
current user may open. Login uses Firebase when ``AUTH_ENABLED=true`` and is a
no-op redirect in dev.
"""

from __future__ import annotations

import random
import re
from types import SimpleNamespace

from flask import Blueprint, Response, redirect, request
from markupsafe import escape

from auth.middleware import current_user, login_required, real_admin_required, real_user
from config import settings
from pages_landing.shell import page
from security import csrf_protect, csrf_token
from tenancy.access import accessible_slugs
from tenancy.events import record_audit

bp = Blueprint("landing", __name__)

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_ASSET_BASE = f"{settings.vizro_mount_prefix.rstrip('/')}/assets"

_WELCOME_MESSAGES = [
    "See what's shaping the conversation.",
    "Everything important, one level deeper.",
    "What's moving the narrative today?",
    "Every signal. Every source. One place.",
    "The narrative is already forming. Want in?",
    "What shaped today's conversation?",
    "What's underneath the headlines today?",
]


def _branding(user) -> tuple[str, str, str]:
    """Resolve (brand_name, accent_color, logo_data_uri) for a user's tenant.

    The accent is validated against a strict hex pattern so a malformed/hostile
    client record can never inject arbitrary CSS into the shell.
    """
    try:
        if user is None or not getattr(user, "client_id", ""):
            return "", "", ""
        client = _store().get_client(user.client_id)
        if client is None:
            return "", "", ""
        accent = client.accent_color if _HEX_COLOR.match(client.accent_color or "") else ""
        return client.brand_name or "", accent, client.logo_data_uri or ""
    except Exception:
        return "", "", ""


def _registry():
    # Import the cached registry from the dashboards package (NOT from `app`),
    # so a request never re-executes app.py and rebuilds Vizro.
    from dashboards import get_registry

    return get_registry()


@bp.route("/")
@login_required
def index():
    user = current_user()
    brand, accent, logo = _branding(user)
    hero_logo = logo or f"{_ASSET_BASE}/logo/logo_sygnet.svg"
    registry = _registry()
    all_slugs = [d.manifest.slug for d in registry]
    visible = set(accessible_slugs(user, all_slugs))
    visible_dashboards = [d for d in registry if d.manifest.slug in visible]

    category_names: list[str] = []
    for dashboard in visible_dashboards:
        category = dashboard.manifest.category or "General"
        if category not in category_names:
            category_names.append(category)

    def _card_html(manifest) -> str:
        href = f"{settings.vizro_mount_prefix.rstrip('/')}{manifest.base_path}"
        return (
            f'<a class="card" data-slug="{escape(manifest.slug)}" data-title="{escape(manifest.title)}" '
            f'data-category="{escape(manifest.category)}" '
            f'href="{escape(href)}" onclick="naRecordRecent(\'{escape(manifest.slug)}\')">'
            f'<button type="button" class="fav-star" data-slug="{escape(manifest.slug)}" '
            f'onclick="naToggleFav(event, \'{escape(manifest.slug)}\')" title="Toggle favourite">&#9734;</button>'
            f"<h3>{escape(manifest.title)}</h3><p>{escape(manifest.description)}</p></a>"
        )

    categories: dict[str, list[str]] = {}
    for dashboard in visible_dashboards:
        categories.setdefault(dashboard.manifest.category or "General", []).append(_card_html(dashboard.manifest))

    summary_pills = [
        f'<span class="hub-stat-pill">{len(visible_dashboards)} dashboards</span>',
        f'<span class="hub-stat-pill">{len(category_names)} categories</span>',
    ]

    sections = [
        (
            '<section class="hub-hero section">'
            '<div class="hub-hero-copy">'
            '<p class="hub-eyebrow">Client Hub</p>'
            f'<h1>{escape(random.choice(_WELCOME_MESSAGES))}</h1>'
            f'<div class="hub-stat-row">{"".join(summary_pills)}</div>'
            '</div>'
            '<div class="hub-hero-mark">'
            f'<img src="{escape(hero_logo)}" alt="{escape(brand or "Native Analytics")}">'
            '</div>'
            '</section>'
        )
    ]

    if categories:
        search = (
            '<div class="hub-search-row">'
            '<input id="dash-search" type="search" placeholder="Search dashboards..." '
            'oninput="naFilterCards(this.value)">'
            '<a class="hub-secondary-link" href="/account">Review access</a>'
            '</div>'
        )
        cat_blocks = "".join(
            f'<div class="cat-section"><h3 class="muted cat-heading">{escape(cat)}</h3>'
            f'<div class="grid">{"".join(cat_cards)}</div></div>'
            for cat, cat_cards in categories.items()
        )
        sections.append(
            '<section class="section"><h2>Your dashboards</h2>'
            '<p class="muted">Choose a dashboard to open. Click the star to keep your most-used workspaces close.</p>'
            f"{search}"
            '<div id="fav-section" class="section" style="display:none">'
            '<h3 class="muted">Favourites</h3><div class="grid" id="fav-grid"></div></div>'
            '<div id="recent-section" class="section" style="display:none">'
            '<h3 class="muted">Recently opened</h3><div class="grid" id="recent-grid"></div></div>'
            f'<div id="dash-all">{cat_blocks}</div>'
            '<p class="muted" id="no-results" style="display:none">No dashboards match your search.</p>'
            "</section>"
        )
    else:
        sections.append(
            '<section class="section"><h2>No dashboards yet</h2>'
            '<p class="muted">You have not been granted access to any dashboard.</p></section>'
        )

    body = "".join(sections) + _PANEL_JS
    return page("Client Hub", body, user=user, accent=accent, brand=brand, page_class="client-hub-shell")


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
    if user.is_admin:
        role_label = "Administrator"
    elif user.is_operator:
        role_label = "Operator"
    else:
        role_label = "User"
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
    brand, accent, _logo = _branding(user)
    return page("My account", body, user=user, accent=accent, brand=brand, page_class="client-hub-shell")


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
"""


_LOGIN_HTML = """
<div class="auth-page">
<div class="section auth-card">
<h2>Sign in</h2>
<p class="muted">Sign in with your account to continue.</p>
<div id="firebaseui" class="auth-providers"></div>
<div class="auth-divider"><span>or</span></div>
<form id="email-link-form" class="auth-email-form">
  <label>Email<input id="email-link-input" type="email" placeholder="you@company.com" required></label>
  <button type="submit">Email me a sign-in link</button>
</form>
<label class="auth-remember"><input type="checkbox" id="remember-me" checked> Stay signed in on this device</label>
<p id="email-link-status" class="muted"></p>
</div>
</div>
<script type="module">
  import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
  import {{
    getAuth, GoogleAuthProvider, OAuthProvider, signInWithPopup,
    isSignInWithEmailLink, signInWithEmailLink,
  }} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";
  const app = initializeApp({{ apiKey: "{api_key}", authDomain: "{auth_domain}" }});
  const auth = getAuth(app);
  const root = document.getElementById("firebaseui");
  const statusEl = document.getElementById("email-link-status");
  const EMAIL_KEY = "na_email_link_address";

  async function finishSessionLogin(cred) {{
    const idToken = await cred.user.getIdToken();
    const remember = document.getElementById("remember-me").checked;
    const r = await fetch("/sessionLogin", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ idToken, remember }}),
    }});
    if (r.ok) window.location = "{next}";
    else root.insertAdjacentHTML("beforeend", "<p style='color:#f55'>Sign-in failed. Please try again.</p>");
  }}

  const btn = document.createElement("button");
  btn.textContent = "Sign in with Google";
  btn.onclick = async () => {{
    try {{
      const cred = await signInWithPopup(auth, new GoogleAuthProvider());
      await finishSessionLogin(cred);
    }} catch (err) {{
      root.insertAdjacentHTML("beforeend", "<p style='color:#f55'>Error: " + err.message + "</p>");
    }}
  }};
  root.appendChild(btn);

  const msBtn = document.createElement("button");
  msBtn.type = "button";
  msBtn.id = "ms-signin-btn";
  msBtn.className = "secondary";
  msBtn.textContent = "Sign in with Microsoft";
  msBtn.onclick = async () => {{
    try {{
      const cred = await signInWithPopup(auth, new OAuthProvider("microsoft.com"));
      await finishSessionLogin(cred);
    }} catch (err) {{
      root.insertAdjacentHTML("beforeend", "<p style='color:#f55'>Error: " + err.message + "</p>");
    }}
  }};
  root.appendChild(msBtn);

  // Completing a sign-in that arrived via an emailed magic link.
  if (isSignInWithEmailLink(auth, window.location.href)) {{
    let email = window.localStorage.getItem(EMAIL_KEY);
    if (!email) email = window.prompt("Confirm your email to finish signing in:");
    if (email) {{
      signInWithEmailLink(auth, email, window.location.href)
        .then((cred) => {{
          window.localStorage.removeItem(EMAIL_KEY);
          return finishSessionLogin(cred);
        }})
        .catch((err) => {{
          statusEl.textContent = "Sign-in link error: " + err.message;
        }});
    }}
  }}

  document.getElementById("email-link-form").addEventListener("submit", async (e) => {{
    e.preventDefault();
    const email = document.getElementById("email-link-input").value.trim();
    statusEl.textContent = "Sending...";
    try {{
      const r = await fetch("/login/email", {{
        method: "POST",
        headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
        body: new URLSearchParams({{ email, _csrf_token: "{csrf_token}" }}),
      }});
      if (r.ok) {{
        window.localStorage.setItem(EMAIL_KEY, email);
        statusEl.textContent = "Check your inbox for a sign-in link.";
      }} else {{
        statusEl.textContent = "Could not send the link. Please try again.";
      }}
    }} catch (err) {{
      statusEl.textContent = "Error: " + err.message;
    }}
  }});
</script>
"""


def _sanitize_next(nxt: str) -> str:
    """The access gate sends ``next`` as the raw path a visitor was denied,
    which for a bookmark/typed URL at the bare Vizro mount (e.g. "/app/") is
    the empty Dash container, not a real dashboard - land there on Client Hub
    instead."""
    mount = settings.vizro_mount_prefix.rstrip("/")
    if not nxt or nxt in (mount, f"{mount}/"):
        return "/"
    return nxt


@bp.route("/login")
def login():
    if not settings.auth_enabled:
        return redirect(_sanitize_next(request.args.get("next", "/")))
    nxt = _sanitize_next(request.args.get("next", "/"))
    body = _LOGIN_HTML.format(
        api_key=settings.firebase_api_key,
        auth_domain=settings.firebase_auth_domain,
        next=nxt,
        csrf_token=csrf_token(),
    )
    resp = Response(page("Sign in", body, page_class="client-hub-shell"), mimetype="text/html")
    # Allow Firebase popup to communicate back across origins.
    resp.headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
    return resp


@bp.route("/login/email", methods=["POST"])
@csrf_protect
def login_email():
    if not settings.auth_enabled:
        return Response(status=204)
    email = (request.form.get("email") or "").strip().lower()
    if not email:
        return Response("Email required", status=400)
    try:
        from auth.firebase import send_signin_link_email

        send_signin_link_email(email, continue_url=f"{request.url_root}login")
    except Exception:
        return Response("Could not send sign-in link", status=502)
    return Response(status=204)


@bp.route("/sessionLogin", methods=["POST"])
def session_login():
    if not settings.auth_enabled:
        return Response(status=204)
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken", "")
    remember = bool(data.get("remember", True))
    try:
        from auth.firebase import create_session_cookie, verify_id_token

        claims = verify_id_token(id_token)  # validate before minting a session cookie
        cookie, ttl = create_session_cookie(id_token)
    except Exception:
        return Response("Invalid token", status=401)

    record_audit(
        "auth.login",
        target=claims.get("uid") or claims.get("sub", ""),
        actor=SimpleNamespace(uid=claims.get("uid") or claims.get("sub", ""), email=claims.get("email", "")),
    )

    resp = Response(status=200)
    resp.set_cookie(
        settings.session_cookie_name,
        cookie,
        # "Stay signed in" unchecked -> omit max_age so the browser treats it as
        # a session cookie (gone when the browser closes); the underlying
        # Firebase cookie still expires server-side after `ttl` either way.
        max_age=int(ttl.total_seconds()) if remember else None,
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


_DEV_COOKIE = "na_dev_as"


@bp.route("/dev")
@real_admin_required
def dev_switch():
    """Pick a user to impersonate ("view as") so an admin can see exactly what
    that user sees. Always available to the fixture admin in dev; in prod,
    restricted to real admins (see ``admin_required``)."""
    store = _store()
    cur = current_user()
    people = sorted(store.list_users(), key=lambda u: (not u.is_admin, u.email))
    rows = []
    for u in people:
        is_cur = cur is not None and cur.uid == u.uid
        if u.is_admin:
            role = "admin"
        elif u.is_operator:
            role = "operator"
        else:
            role = u.client_id or "user"
        if is_cur:
            action = '<span class="pill">current</span>'
        elif u.is_admin:
            action = '<span class="muted" title="Impersonating another admin is not allowed">n/a</span>'
        else:
            action = f'<a class="btn" href="/dev/as/{escape(u.uid)}"><button>View as</button></a>'
        suspended_note = ' <span class="muted">(suspended)</span>' if u.disabled else ""
        rows.append(
            f"<tr><td>{escape(u.email)}{suspended_note}"
            f"<br><span class='muted'>{escape(u.uid)}</span></td>"
            f"<td>{escape(role)}</td><td>{action}</td></tr>"
        )
    helper = (
        "Development helper — auth is disabled, so this lists fixture users."
        if not settings.auth_enabled
        else "Impersonate any non-admin user to see their exact dashboard experience. "
        "Each switch is recorded in the audit log."
    )
    body = (
        '<div class="section"><h2>View as user</h2>'
        f'<p class="muted">{helper}</p>'
        "<table><tr><th>User</th><th>Role / company</th><th></th></tr>"
        f"{''.join(rows)}</table>"
        '<p style="margin-top:16px"><a class="btn" href="/dev/exit">'
        '<button class="secondary">Reset to admin</button></a></p></div>'
    )
    return page("View as", body, user=cur, page_class="client-hub-shell")


@bp.route("/dev/as/<uid>")
@real_admin_required
def dev_become(uid: str):
    resp = redirect("/")
    target = _store().get_user(uid)
    if target is not None and not target.disabled and not target.is_admin:
        resp.set_cookie(_DEV_COOKIE, uid, httponly=True, secure=not settings.is_dev, samesite="Lax")
        record_audit("user.impersonate_start", target=uid, actor=real_user())
    return resp


@bp.route("/dev/exit")
@real_admin_required
def dev_exit():
    resp = redirect("/")
    resp.delete_cookie(_DEV_COOKIE)
    return resp
