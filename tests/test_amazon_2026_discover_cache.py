import threading
import time

import pandas as pd

import dashboards.amazon_2026.charts_discover as discover_mod


class _FakeNode:
    def __init__(self, calls: list[int], block: threading.Event | None = None):
        self._calls = calls
        self._block = block

    def load(self) -> pd.DataFrame:
        self._calls.append(1)
        if self._block is not None:
            self._block.wait(timeout=2)
        return pd.DataFrame()


def _reset_cache(monkeypatch, calls: list[int]):
    monkeypatch.setattr(discover_mod, "_server_cache", None)
    monkeypatch.setattr(discover_mod, "_server_cache_at", 0.0)
    monkeypatch.setattr(discover_mod, "data_manager", {discover_mod.DISCOVER_ITEMS_KEY: _FakeNode(calls)})


def test_server_discover_data_reuses_warm_cache(monkeypatch):
    calls: list[int] = []
    _reset_cache(monkeypatch, calls)

    discover_mod._server_discover_data()
    discover_mod._server_discover_data()

    assert len(calls) == 1


def test_server_discover_data_refreshes_after_ttl_expires(monkeypatch):
    calls: list[int] = []
    block = threading.Event()
    monkeypatch.setattr(discover_mod, "_server_cache", None)
    monkeypatch.setattr(discover_mod, "_server_cache_at", 0.0)
    monkeypatch.setattr(discover_mod, "data_manager", {discover_mod.DISCOVER_ITEMS_KEY: _FakeNode(calls)})

    discover_mod._server_discover_data()
    assert len(calls) == 1

    stale_at = time.monotonic() - discover_mod._SERVER_CACHE_TTL_SECONDS - 1
    monkeypatch.setattr(discover_mod, "_server_cache_at", stale_at)
    monkeypatch.setattr(discover_mod, "data_manager", {discover_mod.DISCOVER_ITEMS_KEY: _FakeNode(calls, block)})

    # Expiry triggers a background refresh and returns the stale cache
    # immediately — no request should block on the reload.
    discover_mod._server_discover_data()
    for _ in range(100):
        if len(calls) > 1:
            break
        time.sleep(0.01)
    assert len(calls) == 2  # refresh started...
    assert discover_mod._server_cache_refreshing  # ...but hasn't finished yet, blocked on `block`

    block.set()
    for _ in range(100):
        if not discover_mod._server_cache_refreshing:
            break
        time.sleep(0.01)
    assert not discover_mod._server_cache_refreshing
