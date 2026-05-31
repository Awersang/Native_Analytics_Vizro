"""Shared minimal HTML shell so landing + admin pages share one look."""

from __future__ import annotations

from flask import render_template_string

from config import settings

_BASE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · Native Analytics</title>
  <style>
    :root { color-scheme: dark; --accent:#4a6cf7; --accent-hover:#3a5ce0; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: Arial, Helvetica, sans-serif; background:#181820; color:#e8e8f0; }
    header { display:flex; align-items:center; justify-content:space-between;
             padding:16px 28px; background:#23232e; border-bottom:1px solid #2a2a3e; }
    header h1 { font-size:18px; margin:0; font-weight:600; }
    header h1 .brand-accent { color:var(--accent); }
    header nav a { color:#aab; text-decoration:none; margin-left:18px; font-size:14px; }
    header nav a:hover { color:#fff; }
    main { max-width:1080px; margin:0 auto; padding:32px 28px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:18px; align-items:stretch; }
    .card { background:#23232e; border:1px solid #2a2a3e; border-radius:12px; padding:20px;
            text-decoration:none; color:inherit; transition:border-color .15s, transform .15s;
            display:flex; flex-direction:column; min-height:128px; }
    .card:hover { border-color:var(--accent); transform:translateY(-2px); }
    .card h3 { margin:0 0 8px; font-size:16px; padding-right:28px; line-height:1.35; }
    .card p { margin:0; font-size:13px; color:#9a9ab0; line-height:1.5;
              display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
    .muted { color:#8a8aa0; font-size:13px; }
    table { width:100%; border-collapse:collapse; margin-top:12px; font-size:14px; }
    th, td { text-align:left; padding:10px 12px; border-bottom:1px solid #2a2a3e; }
    th { color:#9a9ab0; font-weight:600; }
    input, select, button { font:inherit; padding:8px 10px; border-radius:8px;
            border:1px solid #2a2a3e; background:#181820; color:#e8e8f0; }
    button { background:var(--accent); border-color:var(--accent); cursor:pointer; }
    button:hover { background:var(--accent-hover); border-color:var(--accent-hover); }
    button.secondary { background:transparent; border-color:#444; }
    form.inline { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px;
            background:#2a2a3e; margin:2px 4px 2px 0; }
    .status-ok { color:#3ddc84; }
    .status-degraded { color:#e6b800; }
    .status-error { color:#f55; }
    .section { margin-bottom:36px; }
    a.btn { display:inline-block; text-decoration:none; }
    label { font-size:13px; color:#9a9ab0; display:flex; flex-direction:column; gap:4px; }
    .dev-banner { background:#3a2e12; color:#f0d890; border-bottom:1px solid #5a4a1e;
                  padding:7px 28px; font-size:13px; display:flex; gap:14px; align-items:center; }
    .dev-banner a { color:#ffe9a8; text-decoration:underline; }
  </style>
  {% if accent %}<style>:root{ --accent:{{ accent }}; --accent-hover:{{ accent }}; }</style>{% endif %}
</head>
<body>
  {% if dev_mode %}
  <div class="dev-banner">
    <span><strong>DEV</strong> · viewing as
      <strong>{{ user.email if user else 'nobody' }}</strong>
      ({{ 'admin' if user and user.is_admin else 'user' }})</span>
    <a href="/dev">Switch user</a>
    <a href="/dev/exit">Reset to admin</a>
  </div>
  {% endif %}
  <header>
    <h1>{% if brand %}<span class="brand-accent">{{ brand }}</span>{% else %}Native Analytics{% endif %}</h1>
    <nav>
      {% if user %}<span class="muted">{{ user.email }}</span>{% endif %}
      {% if user and user.is_admin %}<a href="/admin">Admin</a>{% endif %}
      <a href="/">Dashboards</a>
      {% if user %}<a href="/account">My account</a>{% endif %}
      {% if user %}<a href="/logout">Sign out</a>{% endif %}
    </nav>
  </header>
  <main>{{ body|safe }}</main>
</body>
</html>
"""


def page(title: str, body_html: str, user=None, accent: str = "", brand: str = "") -> str:
    return render_template_string(
        _BASE, title=title, body=body_html, user=user, accent=accent, brand=brand,
        dev_mode=not settings.auth_enabled,
    )
