"""
Auto-discovery of dashboard plugins.

Scans the ``dashboards`` package for sub-packages that expose a ``MANIFEST`` and
``build_pages`` callable, and returns them as ``RegisteredDashboard`` records.

To add a new dashboard: create ``dashboards/<slug>/`` with an ``__init__.py``
that defines ``MANIFEST`` and ``build_pages(ctx)``. No central registration
needed — it is picked up automatically on the next start.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import vizro.models as vm

from dashboards._base import BuildContext, DashboardManifest, DataSourceHealth


@dataclass(frozen=True)
class RegisteredDashboard:
    manifest: DashboardManifest
    build_pages: Callable[[BuildContext], list[vm.Page]]
    # Optional health probe exported by the dashboard package as ``data_health``.
    data_health: Callable[[], list[DataSourceHealth]] | None = None


def discover_dashboards() -> list[RegisteredDashboard]:
    """Import every dashboard sub-package and collect valid plugins."""
    import dashboards

    found: list[RegisteredDashboard] = []
    for mod_info in pkgutil.iter_modules(dashboards.__path__):
        name = mod_info.name
        if not mod_info.ispkg or name.startswith("_"):
            continue
        module = importlib.import_module(f"dashboards.{name}")
        manifest = getattr(module, "MANIFEST", None)
        build_pages = getattr(module, "build_pages", None)
        if isinstance(manifest, DashboardManifest) and callable(build_pages):
            if manifest.slug != name:
                raise ValueError(
                    f"Dashboard package 'dashboards/{name}' declares slug "
                    f"'{manifest.slug}'. Folder name and slug must match."
                )
            data_health = getattr(module, "data_health", None)
            found.append(
                RegisteredDashboard(
                    manifest=manifest,
                    build_pages=build_pages,
                    data_health=data_health if callable(data_health) else None,
                )
            )

    found.sort(key=lambda d: d.manifest.title.lower())
    return found


@lru_cache
def get_registry() -> list[RegisteredDashboard]:
    """Cached dashboard registry.

    Use this from blueprints/views that only need the manifest metadata, so
    they do not import the ``app`` module (which would re-execute it and rebuild
    Vizro — duplicating page registrations).
    """
    return discover_dashboards()
