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
import json
import logging
import secrets
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import _callback as dash_callback
import dash._callback as _dc
import vizro.models as vm
from dash import dcc, html, clientside_callback, Input, Output
from flask import Response, jsonify, redirect, request
from flask_caching import Cache
from flask_compress import Compress
from vizro import Vizro
from vizro.managers import data_manager as _data_manager

from auth.middleware import current_user
from config import DEFAULT_SESSION_SECRET, settings
from dashboards import get_registry
from dashboards._base import BuildContext
from logging_setup import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

_ASSETS_FOLDER = str(Path(__file__).resolve().parent / "assets")

# Dashboard slug to display title for the header wordmark.
# Built at startup from the registry so new dashboards appear automatically.
def _build_dashboard_titles() -> dict[str, str]:
    return {entry.manifest.slug: entry.manifest.title for entry in get_registry()}

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
            dcc.Store(id="na-page-title-store", data=""),
            html.Span(id="na-dashboard-title", className="na-dashboard-title"),
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


# slug -> pages contributed by that dashboard (filled in _build_dashboard).
_PAGES_BY_SLUG: dict[str, list[vm.Page]] = {}
# page id -> owning dashboard slug (the reverse index ScopedNavBar filters by).
_SLUG_FOR_PAGE_ID: dict[str, str] = {}


class ScopedNavBar(vm.NavBar):
    """A NavBar whose rendered icons are restricted to the *active*
    dashboard's own pages.

    Vizro builds one ``Navigation`` for the whole process and isn't aware of
    "dashboards" as a concept — out of the box, a NavBar with one NavLink per
    page would render every page of every dashboard at once, on the very
    first request, before any click (this was the original bug: the nav rail
    only narrowed down to the right pages *after* the user had already
    clicked one — too late, and only client-side). That can't be fixed by
    hiding things after the fact; it has to never render them in the first
    place.

    Vizro itself calls ``self.nav_selector.build(active_page_id=page.id)``
    fresh, server-side, on *every single page render* — see
    ``vizro.models.Dashboard._make_page_layout``, which is the function Dash
    registers as every page's ``layout`` callable and therefore runs on every
    navigation, full reload or client-routed. So by the time this method
    runs, we already know exactly which page — and therefore which
    dashboard — is being opened, and can render only that dashboard's icons
    from the very first response. No client-side filtering, no CSS, no
    DOM-mutation hack.

    Safety property, deliberately: if the active dashboard can't be
    determined (``active_page_id`` not in any dashboard's page set — e.g. the
    Client-Hub-redirect placeholder page), this renders an *empty* rail, never
    a fallback to "show every page". That fallback is exactly how the
    original bug looked, so it must never be the default here.

    Implementation note: this duplicates (rather than calls) the body of the
    upstream ``NavBar.build()``, operating on a filtered item list instead of
    ``self.items``. It relies on two of Vizro 0.1.56's internal rendering
    details that aren't public API — a Dash "find component by id" lookup
    (``built_items[item.id]``) and an ``"nav-panel" in built_items`` presence
    check — so re-verify this method against ``vizro.models.NavBar.build``
    after any Vizro version bump (the same discipline IMPROVEMENT_PLAN.md §5.6
    already calls for around the other Vizro/Dash internals this app depends
    on). ``tests/test_navigation.py`` will fail loudly if that shape changes
    rather than silently rendering the wrong icons.

    Thread-safety: reads only ``self.items`` (never mutated after startup)
    and the module-level, build-once-at-startup ``_SLUG_FOR_PAGE_ID``/
    ``_PAGES_BY_SLUG`` maps — no shared state is written at request time, so
    this is safe under ``gunicorn --threads 8`` with no locking needed.
    """

    def build(self, *, active_page_id=None):
        slug = _SLUG_FOR_PAGE_ID.get(active_page_id)
        page_ids = {page.id for page in _PAGES_BY_SLUG.get(slug, [])} if slug else set()
        # Filter by `item.pages` (the page ids this NavLink covers) — *not*
        # `item.id`, which is NavLink's own opaque, auto-generated model id,
        # unrelated to which page(s) it links to.
        visible_items = [item for item in self.items if set(item.pages) & page_ids]

        built_items = html.Div([item.build(active_page_id=active_page_id) for item in visible_items])
        nav_links = [built_items[item.id] for item in visible_items]
        if "nav-panel" in built_items:
            nav_panel = built_items["nav-panel"]
        else:
            nav_panel = dbc.Nav(id="nav-panel", className="d-none invisible")

        navbar_class = "flex-column" if self.position == "left" else "navbar-top"
        return html.Div(
            children=[dbc.Navbar(id="nav-bar", children=nav_links, className=navbar_class), nav_panel]
        )


def _build_navigation() -> vm.Navigation:
    """One NavLink per *page* (not per dashboard) — the icon rail is a direct
    page switcher within the active dashboard. Dashboard switching itself
    happens only through the Client Hub (`/`), never through this rail.

    ``ScopedNavBar`` (above) does the actual per-dashboard scoping; this just
    builds the flat, full list of page-links it filters from.
    """
    items: list[vm.NavLink] = []
    for entry in DASHBOARD_REGISTRY:
        dashboard_pages = _PAGES_BY_SLUG.get(entry.manifest.slug, [])
        page_icons = entry.page_icons or {}
        for page in dashboard_pages:
            items.append(
                vm.NavLink(
                    label=page.title,
                    icon=page_icons.get(page.id, entry.manifest.icon),
                    pages=[page.id],
                )
            )
    return vm.Navigation(nav_selector=ScopedNavBar(items=items))


def _build_dashboard() -> vm.Dashboard:
    ctx = BuildContext(is_dev=settings.is_dev)
    pages: list[vm.Page] = [_build_home_page()]
    _PAGES_BY_SLUG.clear()
    _SLUG_FOR_PAGE_ID.clear()
    for entry in DASHBOARD_REGISTRY:
        dashboard_pages = entry.build_pages(ctx)
        _PAGES_BY_SLUG[entry.manifest.slug] = dashboard_pages
        for page in dashboard_pages:
            _SLUG_FOR_PAGE_ID[page.id] = entry.manifest.slug
        pages.extend(dashboard_pages)
    # Cache warmup is separate from page construction (IMPROVEMENT_PLAN.md
    # §5.13/§5.14): build_pages() is pure, warm_caches() does the network I/O.
    # Each gunicorn worker imports/builds the app fresh after fork (no
    # --preload), so this still runs exactly once per process.
    for entry in DASHBOARD_REGISTRY:
        if entry.warm_caches is not None:
            entry.warm_caches()
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
        # Static assets (incl. native_analytics_shell.css, used by the login
        # page itself) must load without auth, or an unauthenticated visitor
        # can never even render a styled /login page.
        if path.startswith(f"{mount}/assets/"):
            return None

        user = current_user()
        if user is None:
            return redirect(f"/login?next={path}")

        slug = _slug_for_path(path)
        if slug is not None and not user.is_admin:
            from tenancy.access import can_access

            if not can_access(user, slug):
                from tenancy.events import record_audit

                record_audit("access.denied_dashboard", target=slug)
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

            # Operators are the only non-admin identities allowed to cross
            # company boundaries intentionally, so we track each dashboard open
            # for that account type explicitly.
            if user.is_operator:
                from tenancy.access import company_slugs
                from tenancy.events import record_audit

                if slug not in company_slugs(user):
                    record_audit("dashboard.cross_client_open", target=slug)
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
        # native_analytics_shell.css is for the plain-Flask Client Hub/admin
        # pages only (served on-demand via a tag in pages_landing/shell.py),
        # not a Vizro dashboard page — exclude it from Dash's automatic
        # every-page asset injection so it doesn't add dead weight there.
        assets_ignore=r"native_analytics_shell\.css",
    )
    # Dash only auto-detects a favicon named exactly "favicon.ico" in the
    # assets folder; swap {%favicon%} for our svg logo instead (rel=icon
    # type=image/svg+xml is supported by all modern browsers).
    viz.dash.index_string = viz.dash.index_string.replace(
        "{%favicon%}",
        f'<link rel="icon" type="image/svg+xml" href="{viz.dash.get_asset_url("logo/logo_sygnet.svg")}">',
    )

    viz.build(_build_dashboard())

    # Register clientside callback to show the active dashboard's name in the
    # header next to the logo. Extracts the slug from /d/<slug>/... in the URL.
    dashboard_titles_json = json.dumps(_build_dashboard_titles())
    clientside_callback(
        f"""
        function(pathname) {{
            var titles = {dashboard_titles_json};
            var match = pathname.match(/\\/d\\/([^/]+)/);
            var title = match ? (titles[match[1]] || '') : '';
            var el = document.getElementById('na-dashboard-title');
            if (el) {{ el.textContent = title; }}
            return title;
        }}
        """,
        Output("na-page-title-store", "data"),
        Input("_pages_location", "pathname"),
        prevent_initial_call=False,
    )

    server = viz.dash.server
    if settings.env == "prod" and settings.session_secret == DEFAULT_SESSION_SECRET:
        raise RuntimeError(
            "SESSION_SECRET is unset (still the dev default) in a prod environment — "
            "set it via Secret Manager before deploying."
        )
    server.secret_key = settings.session_secret

    # Gzip every response (figure/table JSON on each navigation is large and
    # highly compressible; Cloud Run doesn't compress dynamic responses for us).
    Compress(server)

    # Cache BQ results so repeated filter interactions don't hit BigQuery on
    # every callback. The daily load job clears the cache via
    # /internal/cache/refresh the moment fresh data lands (see below); this
    # TTL is just the fallback if that call is ever missed, so it's set to the
    # load cadence rather than something tighter.
    # SimpleCache is process-local; once `cache_redis_url` is set (Memorystore),
    # every worker/instance shares one cache instead of each refreshing BigQuery
    # on its own clock.
    _cache_config = (
        {
            "CACHE_TYPE": "RedisCache",
            "CACHE_REDIS_URL": settings.cache_redis_url,
            "CACHE_DEFAULT_TIMEOUT": 86400,
        }
        if settings.cache_redis_url
        else {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 86400}
    )
    _cache = Cache(config=_cache_config)
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

    @server.route("/internal/cache/refresh", methods=["POST"])
    def _cache_refresh():
        """Called by the daily BigQuery load job once it finishes, so the
        dashboard reflects new data immediately instead of waiting out
        CACHE_DEFAULT_TIMEOUT. Disabled (404) until cache_refresh_secret is set.

        ponytail: SimpleCache is process-local, so on multi-instance Cloud Run
        this only clears whichever instance handles the request — fine for
        --min-instances=1/--max-instances=1; set cache_redis_url first if that
        ever changes.
        """
        if not settings.cache_refresh_secret:
            return Response(status=404)
        if not secrets.compare_digest(
            request.headers.get("X-Cache-Refresh-Secret", ""), settings.cache_refresh_secret
        ):
            return Response(status=403)
        _cache.clear()
        logger.info("Cache cleared via /internal/cache/refresh")
        return jsonify(status="ok")

    @server.errorhandler(500)
    def _handle_server_error(exc):
        """Friendly fallback for an unhandled exception in any route.

        Deliberately static/dependency-free (no template, no auth lookup) so
        the error page itself can't also fail mid-outage.
        """
        logger.exception("Unhandled exception in request: %s", request.path)
        return Response(
            "<h1>Something went wrong</h1>"
            "<p>We hit an unexpected error. Please try again, or contact support if it persists.</p>",
            status=500,
            mimetype="text/html",
        )

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
