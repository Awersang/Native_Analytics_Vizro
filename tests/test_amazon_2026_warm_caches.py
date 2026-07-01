"""amazon_2026 cache warmup wiring (IMPROVEMENT_PLAN.md §5.13/§5.14).

warm_caches() must preload exactly the keys _register_data_sources()
registers -- both are driven by the same _LOADERS dict, so a newly added
data source can't be silently left un-warmed (the bug §5.14 found: Discover
and Archive's keys were registered but never preloaded).
"""

import dashboards.amazon_2026 as amazon_2026


def test_preload_all_covers_every_registered_key(monkeypatch):
    """_preload_all() is the synchronous core warm_caches() runs in a thread --
    test it directly so no real BigQuery calls or background threads are involved."""
    amazon_2026._register_data_sources()

    loaded_keys = []
    for key in amazon_2026._LOADERS:
        monkeypatch.setattr(amazon_2026.data_manager[key], "load", lambda k=key: loaded_keys.append(k))

    amazon_2026._preload_all()

    assert set(loaded_keys) == set(amazon_2026._LOADERS.keys())


def test_previously_unwarmed_keys_are_now_covered():
    """Discover/Archive's keys used to be registered but absent from every
    hand-typed preload list. They must be in _LOADERS (and therefore warmed)."""
    assert amazon_2026.DISCOVER_ITEMS_KEY in amazon_2026._LOADERS
    assert amazon_2026.ARCHIVE_SCATTER_KEY in amazon_2026._LOADERS

