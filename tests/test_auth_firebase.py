"""auth.firebase._claims_cache must not grow unbounded for users who never return."""

import auth.firebase as fb


def test_sweep_drops_entries_older_than_session_cookie_ttl():
    fb._claims_cache.clear()
    fb._inserts_since_sweep = 0
    now = 1_000_000.0
    max_age = fb.SESSION_COOKIE_TTL.total_seconds()

    fb._claims_cache["stale"] = ({"uid": "old"}, now - max_age - 1, now - max_age - 1)
    fb._claims_cache["fresh"] = ({"uid": "new"}, now, now)

    for _ in range(fb._CACHE_SWEEP_EVERY):
        fb._maybe_sweep_claims_cache(now)

    assert "stale" not in fb._claims_cache
    assert "fresh" in fb._claims_cache
