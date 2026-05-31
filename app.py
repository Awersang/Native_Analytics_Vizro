"""
Native Analytics — multi-tenant Vizro dashboard platform.

Architecture (see also the project README):

  * ONE Vizro app holds every dashboard's pages (multiple Vizro apps cannot
    coexist in a single process — the Dash page registry is process-global).
    Vizro is mounted under ``settings.vizro_mount_prefix`` (default ``/app/``)
    so that ``/`` stays free for our own pages.
  * Dashboards are plugins auto-discovered from ``dashboards/<slug>/``.
  * The Flask server created by Vizro also serves our landing/login/admin
    blueprints, and a ``before_request`` gate enforces authentication and
    per-dashboard access grants.

Run locally:  python app.py   →  http://127.0.0.1:8050
"""

from __future__ import annotations

import logging
from pathlib import Path

import vizro.models as vm
from dash import html
from flask import Response, jsonify, redirect, request
from vizro import Vizro

from auth.middleware import current_user
from config import settings
from dashboards import get_registry
from dashboards._base import BuildContext
from logging_setup import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

_ASSETS_FOLDER = str(Path(__file__).resolve().parent / "assets")

# Discovered once (cached); shared with the landing + admin blueprints, which
# import it from `dashboards` (NOT from `app`) to avoid re-executing this module.
DASHBOARD_REGISTRY = get_registry()


def _build_home_page() -> vm.Page:
    """Vizro forces the first page to path '/', so we reserve it for a small
    overview that points users back to the curated panel at the site root."""
    return vm.Page(
        id="overview",
        title="Overview",
        path="/overview",  # Vizro overrides the *first* page's path to '/'
        components=[
            vm.Card(
                text=(
                    "### Native Analytics\n\n"
                    "Use the [dashboard panel](/) to open the dashboards you have "
                    "access to."
                )
            )
        ],
    )


class _PanelDashboard(vm.Dashboard):
    """Vizro dashboard with a persistent 'Back to panel' link in the header.

    Switching between dashboards happens only via the user panel at '/', so the
    in-dashboard chrome offers a way back there but never a cross-dashboard
    switcher (the dashboard nav-bar icon rail is hidden via assets CSS)."""

    def custom_header(self):
        return [
            html.A(
                [
                    html.Span("arrow_back", className="material-symbols-outlined"),
                    html.Span("Panel", className="back-to-panel-text"),
                ],
                href="/",
                className="back-to-panel",
                title="Back to your dashboard panel",
            )
        ]


def _build_navigation() -> vm.Navigation:
    """One NavBar entry per dashboard. Vizro only renders the *active* entry's
    page accordion, so within a dashboard users see just that dashboard's pages
    (enabling multi-page dashboards) and never other dashboards' pages."""
    items: list[vm.NavLink] = []
    for entry in DASHBOARD_REGISTRY:
        page_ids = _PAGE_IDS_BY_SLUG.get(entry.manifest.slug, [])
        if not page_ids:
            continue
        items.append(
            vm.NavLink(
                label=entry.manifest.title,
                icon=entry.manifest.icon,
                pages=page_ids,
            )
        )
    return vm.Navigation(nav_selector=vm.NavBar(items=items))


# slug -> list of page ids contributed by that dashboard (filled in _build_dashboard).
_PAGE_IDS_BY_SLUG: dict[str, list[str]] = {}


def _build_dashboard() -> vm.Dashboard:
    ctx = BuildContext(is_dev=settings.is_dev)
    pages: list[vm.Page] = [_build_home_page()]
    _PAGE_IDS_BY_SLUG.clear()
    for entry in DASHBOARD_REGISTRY:
        dashboard_pages = entry.build_pages(ctx)
        _PAGE_IDS_BY_SLUG[entry.manifest.slug] = [p.id for p in dashboard_pages]
        pages.extend(dashboard_pages)
    return _PanelDashboard(
        title="Native Analytics",
        pages=pages,
        navigation=_build_navigation(),
    )


def _slug_for_path(path: str) -> str | None:
    """Map a request path under the mount prefix to a dashboard slug.

    e.g. '/app/d/timeline' → 'timeline'. Returns None for non-dashboard paths
    (Vizro assets, callbacks, the overview page, ...).
    """
    prefix = settings.vizro_mount_prefix.rstrip("/")
    if not path.startswith(prefix):
        return None
    rest = path[len(prefix):]            # '/d/timeline'
    if not rest.startswith("/d/"):
        return None
    return rest[len("/d/"):].split("/", 1)[0]


def _install_access_gate(server) -> None:
    mount = settings.vizro_mount_prefix.rstrip("/")

    @server.before_request
    def _gate():
        path = request.path
        # Only guard the Vizro-mounted area; landing/login/admin manage their own.
        if not path.startswith(mount):
            return None

        user = current_user()
        if user is None:
            return redirect(f"/login?next={path}")

        slug = _slug_for_path(path)
        if slug is not None and not user.is_admin:
            from tenancy.access import can_access

            if not can_access(user, slug):
                return Response("403 — you do not have access to this dashboard", status=403)

        # Usage analytics: count a dashboard "open" only on real HTML page loads
        # (full navigations), not Vizro's JSON callbacks or static assets.
        if (
            slug is not None
            and request.method == "GET"
            and "text/html" in request.headers.get("Accept", "")
        ):
            from tenancy.events import record_usage

            record_usage(user, slug)
        return None


def create_app() -> Vizro:
    viz = Vizro(
        routes_pathname_prefix=settings.vizro_mount_prefix,
        requests_pathname_prefix=settings.vizro_mount_prefix,
        assets_folder=_ASSETS_FOLDER,
    )
    viz.build(_build_dashboard())

    server = viz.dash.server
    server.secret_key = settings.session_secret

    # Our own pages live at the site root, outside the Vizro mount.
    from admin.routes import bp as admin_bp
    from pages_landing.routes import bp as landing_bp

    server.register_blueprint(landing_bp)
    server.register_blueprint(admin_bp)

    @server.route("/healthz")
    def _healthz():
        """Liveness probe for Cloud Run / load balancers."""
        return jsonify(status="ok", env=settings.env)

    _install_access_gate(server)
    logger.info(
        "App ready: env=%s auth_enabled=%s dashboards=%d",
        settings.env,
        settings.auth_enabled,
        len(DASHBOARD_REGISTRY),
    )
    return viz


app = create_app()
server = app.dash.server  # WSGI entry point for gunicorn: `app:server`


if __name__ == "__main__":
    # Hot-reload is disabled: Vizro registers pages in Dash's process-global
    # page registry at build time, so re-building on file change raises
    # "Path ... cannot be used by more than one page". Restart manually to
    # pick up code changes.
    app.dash.run(
        host="127.0.0.1",
        port=8050,
        debug=True,
        use_reloader=False,
        dev_tools_hot_reload=False,
    )
