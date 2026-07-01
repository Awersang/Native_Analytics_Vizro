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
  <link rel="icon" type="image/svg+xml" href="{{ asset_base }}/logo/logo_sygnet.svg">
  <link rel="stylesheet" href="{{ asset_base }}/native_analytics_shell.css">
  {% if accent %}<style>:root{ --accent:{{ accent }}; --accent-hover:{{ accent }}; }</style>{% endif %}
</head>
<body>
  <div class="app-shell {{ page_class }}">
  {% if show_banner %}
  <div class="dev-banner">
    <span>{% if dev_mode %}<strong>DEV</strong> · {% endif %}viewing as
      <strong>{{ user.email if user else 'nobody' }}</strong>
      ({{ 'admin' if user and user.is_admin else 'user' }})</span>
    <a href="/dev">Switch user</a>
    <a href="/dev/exit">Reset to admin</a>
  </div>
  {% endif %}
  <header class="shell-header">
    <a class="shell-brand" href="/" aria-label="Native Analytics Client Hub">
      <img class="shell-logo" src="{{ asset_base }}/logo/logo_dark.svg" alt="Native Analytics">
      {% if brand %}<span class="shell-brand-copy">
        <span class="shell-brand-name">{{ brand }}</span>
      </span>{% endif %}
    </a>
    <nav class="shell-nav">
      {% if header_actions %}{{ header_actions|safe }}{% endif %}
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
    header_actions_html: str = "",
) -> str:
    from auth.middleware import real_user

    dev_mode = not settings.auth_enabled
    ru = real_user()
    impersonating = ru is not None and user is not None and ru.uid != user.uid
    return render_template_string(
        _BASE,
        title=title,
        body=body_html,
        user=user,
        accent=accent,
        brand=brand,
        page_class=page_class,
        header_actions=header_actions_html,
        asset_base=_ASSET_BASE,
        dev_mode=dev_mode,
        show_banner=dev_mode or impersonating,
    )
