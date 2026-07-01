import time

import pandas as pd
import pytest

import dashboards.amazon_2026.charts_discover as discover_mod
from dashboards.amazon_2026.charts_discover import filter_discover_records


def _record(**overrides):
    base = {
        "_id": 0,
        "_stable_id": "Trad:r1",
        "Date": "2026-01-01",
        "Source": "Trad",
        "Sentiment": "Neutral",
        "Publisher": "Reuters",
        "Topic_Area": "",
        "Narrative": "",
        "Media_Type": "News",
        "Title": "Quarterly roundup",
        "Summary": "Nothing relevant here.",
        "URL": "",
        "Reach": 0,
        "Journalist": "",
        "Full_Text": "",
        "_date_index": 0,
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _reset_semantic_cache(monkeypatch):
    monkeypatch.setattr(discover_mod, "_semantic_cache", {})


def test_semantic_candidates_skipped_without_api_key(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "")
    assert discover_mod.semantic_discover_candidates("antitrust concerns") == {}


def test_semantic_candidates_skipped_for_very_short_query(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")
    calls = []
    monkeypatch.setattr(discover_mod.requests, "post", lambda *a, **k: calls.append(1))
    assert discover_mod.semantic_discover_candidates("ai") == {}
    assert not calls


def test_semantic_candidates_falls_back_gracefully_on_embedding_failure(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")

    def _raise(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(discover_mod.requests, "post", _raise)
    assert discover_mod.semantic_discover_candidates("antitrust concerns") == {}


def test_semantic_candidates_falls_back_gracefully_on_vector_search_failure(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")
    monkeypatch.setattr(discover_mod, "_embed_query", lambda text: [0.1, 0.2, 0.3])

    def _raise(*args, **kwargs):
        raise RuntimeError("bigquery unavailable")

    monkeypatch.setattr(discover_mod, "run_query_params", _raise)
    assert discover_mod.semantic_discover_candidates("antitrust concerns") == {}


def test_semantic_candidates_returns_similarity_scores(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")
    monkeypatch.setattr(discover_mod, "_embed_query", lambda text: [0.1, 0.2, 0.3])
    fake_df = pd.DataFrame({"stable_id": ["Trad:r1", "SoMe:r2"], "distance": [0.0, 0.2]})
    monkeypatch.setattr(discover_mod, "run_query_params", lambda sql, params: fake_df)

    scores = discover_mod.semantic_discover_candidates("antitrust concerns")

    assert scores == {"Trad:r1": 1.0, "SoMe:r2": pytest.approx(0.8)}


def test_semantic_candidates_are_cached_within_ttl(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")
    monkeypatch.setattr(discover_mod, "_embed_query", lambda text: [0.1, 0.2, 0.3])
    fake_df = pd.DataFrame({"stable_id": ["Trad:r1"], "distance": [0.0]})
    calls = []

    def _run_query_params(sql, params):
        calls.append(1)
        return fake_df

    monkeypatch.setattr(discover_mod, "run_query_params", _run_query_params)

    discover_mod.semantic_discover_candidates("antitrust concerns")
    discover_mod.semantic_discover_candidates("antitrust concerns")

    assert len(calls) == 1


def test_semantic_candidates_recomputed_after_ttl_expires(monkeypatch):
    monkeypatch.setattr(discover_mod.settings, "openai_api_key", "fake-key")
    monkeypatch.setattr(discover_mod, "_embed_query", lambda text: [0.1, 0.2, 0.3])
    fake_df = pd.DataFrame({"stable_id": ["Trad:r1"], "distance": [0.0]})
    calls = []

    def _run_query_params(sql, params):
        calls.append(1)
        return fake_df

    monkeypatch.setattr(discover_mod, "run_query_params", _run_query_params)

    discover_mod.semantic_discover_candidates("antitrust concerns")
    stale_at = time.monotonic() - discover_mod._SEMANTIC_CACHE_TTL_SECONDS - 1
    discover_mod._semantic_cache["antitrust concerns"] = (stale_at, discover_mod._semantic_cache["antitrust concerns"][1])
    discover_mod.semantic_discover_candidates("antitrust concerns")

    assert len(calls) == 2


def test_hybrid_ranking_places_semantic_only_match_below_lexical_tiers():
    lexical_hit = _record(_id=1, _stable_id="Trad:r1", Title="Amazon antitrust probe widens")
    semantic_only = _record(_id=2, _stable_id="Trad:r2", Title="Roundup", Summary="Nothing relevant here.")
    no_match = _record(_id=3, _stable_id="Trad:r3", Title="Roundup", Summary="Nothing relevant here.")

    filtered = filter_discover_records(
        [semantic_only, lexical_hit, no_match],
        source_filter=None,
        sentiment_filter=None,
        publisher_filter=None,
        topic_area_filter=None,
        narrative_filter=None,
        date_range=None,
        search_text="antitrust probe",
        search_fulltext=False,
        semantic_scores={"Trad:r2": 0.9},
    )

    # the lexical hit ranks first; the semantic-only match is included but lower;
    # the record with neither a lexical nor a semantic hit is excluded entirely
    assert [r["_id"] for r in filtered] == [1, 2]


def test_hybrid_ranking_still_respects_hard_filters():
    semantic_only_wrong_source = _record(_id=1, _stable_id="SoMe:r1", Source="SoMe", Title="Roundup", Summary="x")

    filtered = filter_discover_records(
        [semantic_only_wrong_source],
        source_filter=["Trad"],
        sentiment_filter=None,
        publisher_filter=None,
        topic_area_filter=None,
        narrative_filter=None,
        date_range=None,
        search_text="antitrust probe",
        search_fulltext=False,
        semantic_scores={"SoMe:r1": 0.99},
    )

    assert filtered == []


def test_hybrid_ranking_without_semantic_scores_keeps_lexical_only_behavior():
    lexical_hit = _record(_id=1, _stable_id="Trad:r1", Title="Amazon antitrust probe widens")
    no_match = _record(_id=2, _stable_id="Trad:r2", Title="Roundup", Summary="Nothing relevant here.")

    filtered = filter_discover_records(
        [lexical_hit, no_match],
        source_filter=None,
        sentiment_filter=None,
        publisher_filter=None,
        topic_area_filter=None,
        narrative_filter=None,
        date_range=None,
        search_text="antitrust probe",
        search_fulltext=False,
        semantic_scores=None,
    )

    assert [r["_id"] for r in filtered] == [1]
