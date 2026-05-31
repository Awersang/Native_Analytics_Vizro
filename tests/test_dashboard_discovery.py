"""Dashboard plugin auto-discovery."""

from dashboards import discover_dashboards


def test_discovers_the_three_dummy_dashboards():
    slugs = {d.manifest.slug for d in discover_dashboards()}
    assert {"timeline", "breakdown", "bq_sample"} <= slugs


def test_manifest_paths_are_namespaced():
    for d in discover_dashboards():
        assert d.manifest.base_path == f"/d/{d.manifest.slug}"


def test_build_pages_returns_vizro_pages():
    """The app builds every dashboard's pages once at import; assert each
    registered dashboard contributed a page at its namespaced path."""
    import app  # noqa: F401  (importing builds the dashboard)
    import dash

    built_paths = {v["path"] for v in dash.page_registry.values()}
    for d in discover_dashboards():
        assert d.manifest.base_path in built_paths
