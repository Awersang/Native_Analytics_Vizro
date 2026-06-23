"""Shared minimal HTML shell so the Client Hub and admin pages share one look."""

from __future__ import annotations

from flask import render_template_string

from config import settings

_ASSET_BASE = f"{settings.vizro_mount_prefix.rstrip('/')}/assets"

_BASE = """
<!doctype html>
<html lang="en" data-bs-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }} · Native Analytics</title>
  <style>
    :root {
      color-scheme: dark;
      --accent: #4a6cf7;
      --accent-hover: #3a5ce0;
      --na-text: rgba(235, 241, 250, 0.92);
      --na-text-muted: rgba(235, 241, 250, 0.72);
      --na-text-soft: rgba(235, 241, 250, 0.58);
      --na-border: rgba(247, 249, 252, 0.12);
      --na-surface: #111827;
      --na-surface-alt: #1b212b;
      --na-surface-hover: #202631;
      --na-grid: rgba(247, 249, 252, 0.1);
      --na-link: #9fd1ff;
      --na-logo-height: 42px;
      --na-shell-glow: rgba(74, 108, 247, 0.16);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top left, var(--na-shell-glow), transparent 34%),
        radial-gradient(circle at top right, rgba(159, 209, 255, 0.08), transparent 24%),
        linear-gradient(180deg, #0f1722 0%, #111827 52%, #0f1722 100%);
      color: var(--na-text);
    }

    a { color: inherit; }

    .app-shell {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .shell-header {
      position: sticky;
      top: 0;
      z-index: 20;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 18px 28px;
      background: rgba(17, 24, 39, 0.84);
      border-bottom: 1px solid var(--na-border);
      backdrop-filter: blur(16px);
    }

    .shell-brand {
      display: inline-flex;
      align-items: center;
      gap: 16px;
      min-width: 0;
      text-decoration: none;
    }

    .shell-logo {
      height: var(--na-logo-height);
      width: auto;
      display: block;
      flex: 0 0 auto;
    }

    .shell-brand-copy {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }

    .shell-brand-name {
      color: var(--na-text);
      font-size: 14px;
      font-weight: 600;
      line-height: 1.2;
      letter-spacing: 0.01em;
    }

    .shell-brand-meta {
      color: var(--na-text-soft);
      font-size: 12px;
      line-height: 1.2;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .shell-brand-accent {
      color: var(--accent);
    }

    .shell-nav {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      flex-wrap: wrap;
      gap: 10px;
    }

    .shell-nav-user {
      color: var(--na-text-soft);
      font-size: 13px;
      margin-right: 4px;
    }

    .shell-nav a {
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 0 14px;
      border: 1px solid var(--na-border);
      border-radius: 999px;
      color: var(--na-text-muted);
      text-decoration: none;
      font-size: 14px;
      transition: border-color .16s ease, color .16s ease, background .16s ease, transform .16s ease;
      background: rgba(255, 255, 255, 0.01);
    }

    .shell-nav a:hover,
    .shell-nav a.active {
      color: var(--na-text);
      border-color: rgba(74, 108, 247, 0.48);
      background: rgba(74, 108, 247, 0.12);
      transform: translateY(-1px);
    }

    .shell-main {
      width: min(1200px, calc(100% - 48px));
      margin: 0 auto;
      padding: 34px 0 48px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 18px;
      align-items: stretch;
    }

    .card {
      position: relative;
      display: flex;
      flex-direction: column;
      min-height: 168px;
      gap: 10px;
      padding: 22px 22px 20px;
      border: 1px solid var(--na-border);
      border-radius: 14px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.025) 0%, rgba(255, 255, 255, 0.01) 100%),
        var(--na-surface-alt);
      text-decoration: none;
      color: inherit;
      transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease, background .18s ease;
      box-shadow: 0 18px 48px rgba(0, 0, 0, 0.16);
    }

    .card:hover {
      border-color: rgba(74, 108, 247, 0.45);
      background:
        linear-gradient(180deg, rgba(74, 108, 247, 0.09) 0%, rgba(255, 255, 255, 0.02) 100%),
        var(--na-surface-hover);
      transform: translateY(-3px);
      box-shadow: 0 22px 58px rgba(0, 0, 0, 0.24);
    }

    .card h3 {
      margin: 0;
      padding-right: 34px;
      color: var(--na-text);
      font-size: 17px;
      font-weight: 600;
      line-height: 1.35;
    }

    .card p {
      margin: 0;
      font-size: 13px;
      color: var(--na-text-muted);
      line-height: 1.55;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .muted {
      color: var(--na-text-muted);
      font-size: 13px;
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin-top: 12px;
      font-size: 14px;
      overflow: hidden;
      border: 1px solid var(--na-border);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.015);
    }

    th,
    td {
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--na-border);
    }

    th {
      color: var(--na-text-muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: rgba(255, 255, 255, 0.03);
    }

    tbody tr:last-child td {
      border-bottom: none;
    }

    tbody tr:nth-child(even) td {
      background: rgba(255, 255, 255, 0.015);
    }

    input,
    select,
    button {
      font: inherit;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--na-border);
      background: rgba(255, 255, 255, 0.02);
      color: var(--na-text);
    }

    input:focus,
    select:focus {
      outline: none;
      border-color: rgba(74, 108, 247, 0.48);
      box-shadow: 0 0 0 4px rgba(74, 108, 247, 0.14);
    }

    input::placeholder {
      color: var(--na-text-soft);
    }

    button {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      cursor: pointer;
      transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background .16s ease;
      box-shadow: 0 10px 24px rgba(74, 108, 247, 0.22);
    }

    button:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
      transform: translateY(-1px);
    }

    button.secondary {
      background: transparent;
      border-color: var(--na-border);
      box-shadow: none;
      color: var(--na-text);
    }

    form.inline {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }

    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      color: var(--na-text-muted);
      background: rgba(255, 255, 255, 0.045);
      border: 1px solid var(--na-border);
      margin: 2px 6px 2px 0;
    }

    .status-ok { color: #3ddc84; }
    .status-degraded { color: #e6b800; }
    .status-error { color: #f55; }

    .section {
      margin-bottom: 24px;
      padding: 22px;
      border: 1px solid var(--na-border);
      border-radius: 18px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.028) 0%, rgba(255, 255, 255, 0.012) 100%),
        rgba(17, 24, 39, 0.72);
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.14);
      backdrop-filter: blur(10px);
    }

    .section h2 {
      margin: 0 0 8px;
      color: var(--na-text);
      font-size: 24px;
      font-weight: 700;
      line-height: 1.2;
    }

    .section h3 {
      color: var(--na-text);
    }

    a.btn {
      display: inline-block;
      text-decoration: none;
    }

    label {
      font-size: 13px;
      color: var(--na-text-muted);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .dev-banner {
      background: #3a2e12;
      color: #f0d890;
      border-bottom: 1px solid #5a4a1e;
      padding: 7px 28px;
      font-size: 13px;
      display: flex;
      gap: 14px;
      align-items: center;
    }

    .dev-banner a {
      color: #ffe9a8;
      text-decoration: underline;
    }

    @media (max-width: 900px) {
      .shell-header {
        flex-direction: column;
        align-items: stretch;
        padding: 16px 18px;
      }

      .shell-main {
        width: min(100% - 24px, 1200px);
        padding-top: 22px;
      }

      .shell-nav {
        justify-content: flex-start;
      }
    }

    @media (max-width: 640px) {
      .shell-brand {
        align-items: flex-start;
      }

      .shell-brand-copy {
        gap: 4px;
      }

      .shell-nav a {
        min-height: 34px;
        padding: 0 12px;
        font-size: 13px;
      }

      .section {
        padding: 18px;
      }
    }
  </style>
  {% if accent %}<style>:root{ --accent:{{ accent }}; --accent-hover:{{ accent }}; }</style>{% endif %}
</head>
<body>
  <div class="app-shell {{ page_class }}">
  {% if dev_mode %}
  <div class="dev-banner">
    <span><strong>DEV</strong> · viewing as
      <strong>{{ user.email if user else 'nobody' }}</strong>
      ({{ 'admin' if user and user.is_admin else 'user' }})</span>
    <a href="/dev">Switch user</a>
    <a href="/dev/exit">Reset to admin</a>
  </div>
  {% endif %}
  <header class="shell-header">
    <a class="shell-brand" href="/" aria-label="Native Analytics Client Hub">
      <img class="shell-logo" src="{{ asset_base }}/logo/logo_full.svg" alt="Native Analytics">
      <span class="shell-brand-copy">
        <span class="shell-brand-name">Client Hub{% if brand %} <span class="shell-brand-accent">for {{ brand }}</span>{% endif %}</span>
        <span class="shell-brand-meta">Native Analytics workspace</span>
      </span>
    </a>
    <nav class="shell-nav">
      {% if user %}<span class="shell-nav-user">{{ user.email }}</span>{% endif %}
      {% if user and user.is_admin %}<a href="/admin">Admin</a>{% endif %}
      <a href="/" {% if title == "Client Hub" %}class="active"{% endif %}>Client Hub</a>
      {% if user %}<a href="/account">My account</a>{% endif %}
      {% if user %}<a href="/logout">Sign out</a>{% endif %}
    </nav>
  </header>
  <main class="shell-main">{{ body|safe }}</main>
  </div>
</body>
</html>
"""


def page(
    title: str,
    body_html: str,
    user=None,
    accent: str = "",
    brand: str = "",
    page_class: str = "",
) -> str:
    return render_template_string(
        _BASE,
        title=title,
        body=body_html,
        user=user,
        accent=accent,
        brand=brand,
        page_class=page_class,
        asset_base=_ASSET_BASE,
        dev_mode=not settings.auth_enabled,
    )
