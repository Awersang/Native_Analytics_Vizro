"""
Native Analytics — multi-tenant Vizro dashboard platform.

Architecture (see also the project README):

  * ONE Vizro app holds every dashboard's pages (multiple Vizro apps cannot
    coexist in a single process — the Dash page registry is process-global).
    Vizro is mounted under ``settings.vizro_mount_prefix`` (default ``/app/``)
    so that ``/`` stays free for our own pages.
  * Dashboards are plugins auto-discovered from ``dashboards/<slug>/``.
  * The Flask server created by Vizro also serves our client-hub/login/admin
    blueprints, and a ``before_request`` gate enforces authentication and
    per-dashboard access grants.

Run locally:  python app.py   →  http://127.0.0.1:8050
"""

from __future__ import annotations
import logging
from pathlib import Path

import dash
from dash import _callback as dash_callback
import dash._callback as _dc
import vizro.models as vm
from dash import html
from flask import Response, jsonify, redirect, request
from flask_caching import Cache
from vizro import Vizro
from vizro.managers import data_manager as _data_manager

from auth.middleware import current_user
from config import settings
from dashboards import get_registry
from dashboards._base import BuildContext
from logging_setup import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

_ASSETS_FOLDER = str(Path(__file__).resolve().parent / "assets")

# ---------------------------------------------------------------------------
# Workaround for Vizro 0.1.56 / Dash 4.x behaviour where Dashboard.build()
# pre-calls page.build() for each page (to register RangeSlider callbacks),
# AND Dash's lazy page routing calls page.build() again on first navigation.
# Graph.build() registers hidden clientside callbacks both times, producing
# duplicate output entries in GLOBAL_CALLBACK_LIST that the browser rejects.
# Making insert_callback idempotent (skip if callback_id already registered)
# lets the first registration win and silently drops the redundant second one.
# ---------------------------------------------------------------------------
_orig_insert_callback = _dc.insert_callback


def _idempotent_insert_callback(callback_list, callback_map, *args, **kwargs):
    from dash._utils import create_callback_id

    output = args[0] if args else kwargs.get("output")
    inputs = args[2] if len(args) > 2 else kwargs.get("inputs", [])
    no_output = kwargs.get("no_output", False)
    try:
        cb_id = create_callback_id(output, inputs, no_output)
        if cb_id in callback_map:
            return cb_id
    except Exception:
        pass
    return _orig_insert_callback(callback_list, callback_map, *args, **kwargs)


_dc.insert_callback = _idempotent_insert_callback

# Discovered once (cached); shared with the client-hub + admin blueprints, which
# import it from `dashboards` (NOT from `app`) to avoid re-executing this module.
DASHBOARD_REGISTRY = get_registry()


def _build_home_page() -> vm.Page:
    """Vizro forces the first page to path '/', so we reserve it for a small
    platform page that points users back to the Client Hub at the site root."""
    return vm.Page(
        id="overview",
        title="Client Hub",
        path="/overview",  # Vizro overrides the *first* page's path to '/'
        components=[
            vm.Card(
                text=(
                    "### Native Analytics\n\n"
                    "Use the [Client Hub](/) to open the dashboards you have "
                    "access to."
                )
            )
        ],
    )


class _PanelDashboard(vm.Dashboard):
    """Vizro dashboard with a persistent 'Back to Client Hub' link in the header.

    The standard Vizro left navigation rail remains available, while the
    in-dashboard header also offers a direct way back to the Client Hub."""

    def custom_header(self):
        return [
            html.A(
                [
                    html.Span("arrow_back", className="material-symbols-outlined"),
                    html.Span("Client Hub", className="back-to-panel-text"),
                ],
                href="/",
                className="back-to-panel",
                title="Back to Client Hub",
            )
        ]


def _build_navigation() -> vm.Navigation:
    """One NavBar entry per page.

    Dashboard switching stays in the Client Hub while the left icon rail is
    used for page-to-page navigation inside the active dashboard.
    """
    items: list[vm.NavLink] = []
    for entry in DASHBOARD_REGISTRY:
        dashboard_pages = _PAGES_BY_SLUG.get(entry.manifest.slug, [])
        if not dashboard_pages:
            continue
        page_icons = entry.page_icons or {}
        for page in dashboard_pages:
            items.append(
                vm.NavLink(
                    label=page.title,
                    icon=page_icons.get(page.id, entry.manifest.icon),
                    pages=[page.id],
                )
            )
    return vm.Navigation(nav_selector=vm.NavBar(items=items))


# slug -> pages contributed by that dashboard (filled in _build_dashboard).
_PAGES_BY_SLUG: dict[str, list[vm.Page]] = {}


def _build_dashboard() -> vm.Dashboard:
    ctx = BuildContext(is_dev=settings.is_dev)
    pages: list[vm.Page] = [_build_home_page()]
    _PAGES_BY_SLUG.clear()
    for entry in DASHBOARD_REGISTRY:
        dashboard_pages = entry.build_pages(ctx)
        _PAGES_BY_SLUG[entry.manifest.slug] = dashboard_pages
        pages.extend(dashboard_pages)
    return _PanelDashboard(
        title="Native Analytics",
        pages=pages,
        navigation=_build_navigation(),
    )


def _slug_for_path(path: str) -> str | None:
    """Map a request path under the mount prefix to a dashboard slug.

    e.g. '/app/d/timeline' → 'timeline'. Returns None for non-dashboard paths
    (Vizro assets, callbacks, the Client Hub page, ...).
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
        # Only guard the Vizro-mounted area; client-hub/login/admin manage their own.
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
    # In dev, Dash/Vizro rebuild can happen inside the same process while files
    # change. Clear process-global Dash registries first to avoid duplicate page
    # paths, duplicate model ids, and duplicate callback outputs on hot reload.
    if settings.is_dev:
        Vizro._reset()
        dash.page_registry.clear()
        dash_callback.GLOBAL_CALLBACK_LIST.clear()
        dash_callback.GLOBAL_CALLBACK_MAP.clear()

    viz = Vizro(
        routes_pathname_prefix=settings.vizro_mount_prefix,
        requests_pathname_prefix=settings.vizro_mount_prefix,
        assets_folder=_ASSETS_FOLDER,
    )
    viz.build(_build_dashboard())

    server = viz.dash.server
    server.secret_key = settings.session_secret

    # Cache BQ results for 10 minutes so repeated filter interactions don't
    # hit BigQuery on every callback.  Full-table queries are preserved.
    _cache = Cache(config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 600})
    _cache.init_app(server)
    _data_manager.cache = _cache

    # Our own pages live at the site root, outside the Vizro mount.
    from admin.routes import bp as admin_bp
    from pages_landing.routes import bp as landing_bp

    server.register_blueprint(landing_bp)
    server.register_blueprint(admin_bp)

    @server.route("/healthz")
    def _healthz():
        """Liveness probe for Cloud Run / load balancers."""
        return jsonify(status="ok", env=settings.env)

    # Optional, detachable feature add-ons (chat-with-data, ...). Delete the
    # `extensions/` package + the matching `assets/ext_*` files to remove them.
    from extensions import install_extensions

    install_extensions(server, dash_app=viz.dash)

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
    # Auto-reload in dev; keep production behavior deterministic.
    dev_reload = settings.is_dev
    app.dash.run(
        host="127.0.0.1",
        port=8050,
        debug=True,
        use_reloader=dev_reload,
        dev_tools_hot_reload=dev_reload,
        dev_tools_ui=False,
    )
