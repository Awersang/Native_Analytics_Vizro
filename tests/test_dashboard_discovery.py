"""Dashboard plugin auto-discovery."""

from dashboards import discover_dashboards


def test_discovers_the_three_dummy_dashboards():
    slugs = {d.manifest.slug for d in discover_dashboards()}
    assert {"timeline", "breakdown", "bq_sample", "amazon_2026"} <= slugs


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


def test_amazon_2026_exposes_warm_caches_hook():
    """amazon_2026 separates page construction from cache warmup
    (IMPROVEMENT_PLAN.md §5.13) -- discovery must pick up the optional hook."""
    entries = {d.manifest.slug: d for d in discover_dashboards()}
    assert callable(entries["amazon_2026"].warm_caches)


def test_internal_dashboards_excluded_outside_dev(monkeypatch):
    """The bq_sample/breakdown/timeline demo dashboards are dev/test-only —
    discovery must drop them once the app isn't running in dev."""
    from config import settings

    monkeypatch.setattr(settings, "env", "prod")
    slugs = {d.manifest.slug for d in discover_dashboards()}
    assert "amazon_2026" in slugs
    assert not ({"timeline", "breakdown", "bq_sample"} & slugs)
