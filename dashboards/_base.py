"""
Dashboard plugin contract.

Every dashboard is a self-contained Python package under ``dashboards/<slug>/``
that exposes, at package level:

    MANIFEST: DashboardManifest        # metadata (slug, title, role, ...)
    def build_pages(ctx) -> list[vm.Page]

``app.py`` discovers all such packages, collects their pages into a single
Vizro ``Dashboard`` (see SPIKE FINDINGS: multiple Vizro apps cannot coexist in
one process), and uses the manifest for the Client Hub and the admin grant UI.

Page paths MUST be namespaced as ``/d/<slug>`` (and ``/d/<slug>/...`` for extra
pages) so the request gate in app.py can map any URL back to a dashboard slug.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Role = Literal["admin", "user"]


@dataclass(frozen=True)
class DashboardManifest:
    slug: str
    title: str
    description: str = ""
    # Minimum role required even to be granted this dashboard. "user" means any
    # granted user; "admin" hides it from the grant UI for normal users.
    required_role: Role = "user"
    # Optional Bootstrap icon name shown on the Client Hub card.
    icon: str = "bar_chart"
    # Grouping label for the Client Hub (cards are grouped under this heading).
    category: str = "General"
    # Free-form list of data dependencies for documentation/admin display, e.g.
    # ["bigquery:london_bicycles.cycle_hire"].
    data_requirements: list[str] = field(default_factory=list)

    @property
    def base_path(self) -> str:
        """The canonical in-app path for this dashboard's Client Hub entry page."""
        return f"/d/{self.slug}"


@dataclass(frozen=True)
class DataSourceHealth:
    """A snapshot of one data source's health for the admin health page."""

    name: str
    status: Literal["ok", "degraded", "error"] = "ok"
    detail: str = ""
    rows: int | None = None
    as_of: str = ""



@dataclass
class BuildContext:
    """Context passed to ``build_pages`` at startup.

    Pages are built once for the whole process, so this carries process-level
    info rather than a specific user. Per-user data scoping (the dataset a
    client sees) is resolved at request time inside dynamic-data loaders, which
    can read the logged-in user from the Flask request context.
    """

    is_dev: bool = True


def export_button(text: str = "Download data (CSV)", file_format: str = "csv"):
    """A Vizro Button that downloads the page's chart data.

    Uses Vizro's native ``export_data`` action. With no explicit targets it
    exports every figure on the page. Place it in a page's ``components``.
    """
    import vizro.actions as va
    import vizro.models as vm

    return vm.Button(
        text=text,
        icon="download",
        variant="outlined",
        actions=[va.export_data(file_format=file_format)],
    )


def freshness_note(latest) -> str:
    """A short markdown 'data as of' line for a page description/footer.

    ``latest`` may be a date/datetime/str or None (unknown / live source).
    """
    if latest is None:
        return "Data source: live."
    try:
        stamp = latest.strftime("%-d %b %Y")
    except (AttributeError, ValueError):
        try:
            stamp = latest.strftime("%d %b %Y")
        except AttributeError:
            stamp = str(latest)
    return f"Data as of {stamp}."
