"""Discover page components — unified Trad/SoMe item browser with filters and search."""
from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import requests
from dash import dcc, html
from vizro.managers import data_manager

from config import settings
from dashboards.amazon_2026.charts_archive import _archive_figure, _build_color_map
from dashboards.amazon_2026.theme import (
    DONUT_COLORS,
    THEME_BORDER,
    THEME_GRID,
    THEME_SURFACE,
    THEME_TEXT,
    media_label_color,
    topic_area_color_map,
)
from dashboards.amazon_2026.timeline_charts import _filter_trad_some
from dashboards.amazon_2026.ui_components import (
    SENTIMENT_OPTIONS,
    TOP_POSTS_STYLE_DATA_CONDITIONAL,
    TOP_PUBLICATIONS_STYLE_DATA_CONDITIONAL,
    TRAD_SOME_OPTIONS,
    build_top_posts_table,
    build_top_publications_table,
    donut_figure,
    donut_panel,
    empty_donut_panel,
    json_safe,
    kpi_card,
    na_panel,
    num,
    sentiment_donut_slices,
)
from dashboards.amazon_2026.data_common import DISCOVER_ITEMS_KEY, DISCOVER_VECTORS_TABLE, _table
from dashboards.amazon_2026.dev_ids import ref_label
from data_sources.bq import run_query_params

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Record preparation
# ---------------------------------------------------------------------------


def discover_records(data_frame: pd.DataFrame) -> list[dict[str, Any]]:
    if data_frame.empty:
        return []
    frame = data_frame.copy().reset_index(drop=True)
    dates = pd.to_datetime(frame["Date"], errors="coerce")
    min_date = dates.min()
    frame["_date_index"] = (dates - min_date).dt.days.fillna(0).astype(int)
    frame["_id"] = frame.index
    if "umap_x" in frame.columns:
        frame["umap_x"] = pd.to_numeric(frame["umap_x"], errors="coerce")
    if "umap_y" in frame.columns:
        frame["umap_y"] = pd.to_numeric(frame["umap_y"], errors="coerce")
    records = [json_safe(row) for row in frame.to_dict("records")]
    for record in records:
        record["_search_index"] = _build_search_index(record)
        record_id = record.get("Record_ID")
        record["_stable_id"] = f"{record.get('Source')}:{record_id}" if record_id else None
    return records


_server_cache: tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]] | None = None
_server_cache_at: float = 0.0
_server_cache_lock = threading.Lock()
_server_cache_refreshing = False

# Matches app.py's flask_caching CACHE_DEFAULT_TIMEOUT, so Discover's freshness
# guarantee doesn't silently diverge from every other page's.
_SERVER_CACHE_TTL_SECONDS = 3600


def _server_cache_expired() -> bool:
    return _server_cache is None or time.monotonic() - _server_cache_at >= _SERVER_CACHE_TTL_SECONDS


def _populate_server_cache() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    global _server_cache, _server_cache_at
    started = time.monotonic()
    df = data_manager[DISCOVER_ITEMS_KEY].load()
    records = discover_records(df)
    cluster_records = discover_cluster_records(records)
    color_map = _build_color_map(pd.DataFrame(cluster_records)) if cluster_records else {}
    _server_cache = (records, cluster_records, color_map)
    _server_cache_at = time.monotonic()
    logger.info("Discover server-side cache populated in %.2fs", _server_cache_at - started)
    return _server_cache


def _server_discover_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Return (records, cluster_records, color_map) from a server-side cache.

    Called by both @capture panels and callbacks — records stay in server memory
    instead of being serialised into a browser dcc.Store and round-tripped on
    every filter interaction. Populated via data_manager on first call (or by
    warm_caches() at process start). Once _SERVER_CACHE_TTL_SECONDS has elapsed,
    stale data is served immediately while a background thread refreshes it —
    no request should ever block on the tokenization/clustering pass.
    """
    global _server_cache_refreshing
    if _server_cache is None:
        with _server_cache_lock:
            if _server_cache is None:
                return _populate_server_cache()
        return _server_cache
    if _server_cache_expired():
        with _server_cache_lock:
            if _server_cache_expired() and not _server_cache_refreshing:
                _server_cache_refreshing = True

                def _refresh() -> None:
                    global _server_cache_refreshing
                    try:
                        _populate_server_cache()
                    finally:
                        _server_cache_refreshing = False

                threading.Thread(target=_refresh, daemon=True).start()
    return _server_cache


def discover_date_bounds(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"min_date": "", "max_date": "", "max_index": 0}
    dates = sorted(record.get("Date", "") for record in records if record.get("Date"))
    max_index = max(int(record.get("_date_index", 0)) for record in records)
    return {"min_date": dates[0], "max_date": dates[-1], "max_index": max_index}


def discover_date_marks(date_bounds: dict[str, Any]) -> dict[int, str]:
    min_date = pd.to_datetime(date_bounds.get("min_date") or None, errors="coerce")
    max_date = pd.to_datetime(date_bounds.get("max_date") or None, errors="coerce")
    if pd.isna(min_date) or pd.isna(max_date):
        return {0: ""}

    max_index = int((max_date - min_date).days)
    marks: dict[int, str] = {0: min_date.strftime("%d %b %Y")}
    for month_start in pd.date_range(min_date.to_period("M").to_timestamp(), max_date, freq="MS"):
        if month_start <= min_date:
            continue
        index = int((month_start - min_date).days)
        if 0 < index < max_index:
            marks[index] = month_start.strftime("%b %Y")
    marks[max_index] = max_date.strftime("%d %b %Y")
    return marks


def _sorted_unique(records: list[dict[str, Any]], field: str) -> list[str]:
    values = {str(record.get(field, "")).strip() for record in records}
    values.discard("")
    return sorted(values)


def discover_filter_options(records: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    return {
        "publisher": [{"label": v, "value": v} for v in _sorted_unique(records, "Publisher")],
        "topic_area": [{"label": v, "value": v} for v in _sorted_unique(records, "Topic_Area")],
        "narrative": [{"label": v, "value": v} for v in _sorted_unique(records, "Narrative")],
    }


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Keyword search: normalization, field weighting, ranking, typo tolerance
# ---------------------------------------------------------------------------

# Field weights: title/summary hits rank above metadata, which ranks above
# full-text-only hits. Searched but not the highest tier — matches the
# placeholder copy ("author, publisher, title, or text").
_METADATA_SEARCH_FIELDS = ("Publisher", "Journalist", "Topic_Area", "Narrative", "Media_Type", "Source")

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")

# Typo tolerance only — short tokens are excluded so fuzzy matching can't
# silently broaden common short search terms (e.g. "us" matching anything).
_FUZZY_MIN_TOKEN_LEN = 4
_FUZZY_THRESHOLD = 0.82


def _normalize_text(text: Any) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _PUNCT_RE.sub(" ", text.casefold())
    return _WS_RE.sub(" ", text).strip()


def _stem_token(token: str) -> str:
    """Strip common English plural suffixes only — no verb stemming, to avoid false matches."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es") and not token.endswith(("ses", "xes", "ches", "shes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _stemmed_tokens(text: Any) -> frozenset[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return frozenset()
    return frozenset(_stem_token(tok) for tok in normalized.split())


def _build_search_index(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "title_norm": _normalize_text(record.get("Title", "")),
        "title_tokens": _stemmed_tokens(record.get("Title", "")),
        "summary_tokens": _stemmed_tokens(record.get("Summary", "")),
        "metadata_tokens": frozenset().union(
            *(_stemmed_tokens(record.get(field, "")) for field in _METADATA_SEARCH_FIELDS)
        ),
        "fulltext_tokens": _stemmed_tokens(record.get("Full_Text", "")),
    }


def _fuzzy_token_match(token: str, haystack: frozenset[str]) -> bool:
    if len(token) < _FUZZY_MIN_TOKEN_LEN:
        return False
    return any(
        abs(len(word) - len(token)) <= 2 and SequenceMatcher(None, token, word).ratio() >= _FUZZY_THRESHOLD
        for word in haystack
    )


def _all_tokens_present(tokens: frozenset[str], haystack: frozenset[str]) -> bool:
    return all(token in haystack for token in tokens)


def _all_tokens_fuzzy_present(tokens: frozenset[str], haystack: frozenset[str]) -> bool:
    return all(token in haystack or _fuzzy_token_match(token, haystack) for token in tokens)


def _phrase_in(haystack: str, phrase: str) -> bool:
    """Word-boundary substring check — a plain `in` would let a short query match inside an
    unrelated longer word (e.g. "pro" inside "probe")."""
    return f" {phrase} " in f" {haystack} "


def _search_rank(index: dict[str, Any], query_tokens: frozenset[str], query_phrase: str, fulltext: bool) -> int | None:
    """Lower is better; None means no match. Tiers match §5.26's ranking order."""
    if query_phrase and _phrase_in(index["title_norm"], query_phrase):
        return 0
    title_summary = index["title_tokens"] | index["summary_tokens"]
    if _all_tokens_present(query_tokens, title_summary):
        return 1
    title_summary_meta = title_summary | index["metadata_tokens"]
    if _all_tokens_present(query_tokens, title_summary_meta):
        return 2
    everything = title_summary_meta | index["fulltext_tokens"] if fulltext else title_summary_meta
    if fulltext and _all_tokens_present(query_tokens, everything):
        return 3
    if _all_tokens_fuzzy_present(query_tokens, everything):
        return 4
    return None


def discover_search_rank(record: dict[str, Any], search_text: str, fulltext: bool = False) -> int | None:
    """Public wrapper used by tests and any caller without a pre-filtered record list."""
    query_tokens = _stemmed_tokens(search_text)
    if not query_tokens:
        return 0
    index = record.get("_search_index") or _build_search_index(record)
    query_phrase = _normalize_text(search_text)
    return _search_rank(index, query_tokens, query_phrase, fulltext)


# ---------------------------------------------------------------------------
# Semantic search (§5.27): hybrid lexical + BigQuery VECTOR_SEARCH over the
# pipeline's stored OpenAI embeddings. Embeddings never leave BigQuery /
# load into the Dash records cache — only (stable_id, similarity) pairs do.
# ---------------------------------------------------------------------------

_OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
_EMBEDDING_MODEL = "text-embedding-3-small"
_SEMANTIC_TOP_K = 50
_SEMANTIC_MIN_QUERY_LEN = 3

_semantic_cache: dict[str, tuple[float, list[float], dict[str, float]]] = {}
_semantic_cache_lock = threading.Lock()
_SEMANTIC_CACHE_TTL_SECONDS = 3600


def _embed_query(text: str) -> list[float] | None:
    if not settings.openai_api_key:
        return None
    try:
        response = requests.post(
            _OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"model": _EMBEDDING_MODEL, "input": text},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception:
        logger.exception("Discover semantic search: query embedding failed")
        return None


def _vector_search(embedding: list[float]) -> dict[str, float]:
    from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter

    sql = f"""
    SELECT base.stable_id AS stable_id, distance
    FROM VECTOR_SEARCH(
      TABLE {_table(DISCOVER_VECTORS_TABLE)},
      'embedding_vector',
      (SELECT @qvec AS embedding_vector),
      top_k => @top_k,
      distance_type => 'COSINE'
    )
    """
    params = [
        ArrayQueryParameter("qvec", "FLOAT64", embedding),
        ScalarQueryParameter("top_k", "INT64", _SEMANTIC_TOP_K),
    ]
    df = run_query_params(sql, params)
    # COSINE distance is in [0, 2]; fold to a 0-1 similarity score for ranking.
    return {row.stable_id: max(0.0, 1.0 - float(row.distance)) for row in df.itertuples()}


def _cached_query_embedding(text: str) -> tuple[list[float] | None, dict[str, float] | None]:
    """Return the cached (embedding, scores) pair for *text* if still fresh, else (None, None)."""
    now = time.monotonic()
    with _semantic_cache_lock:
        cached = _semantic_cache.get(text)
        if cached and now - cached[0] < _SEMANTIC_CACHE_TTL_SECONDS:
            return cached[1], cached[2]
    return None, None


def semantic_discover_candidates(query_text: str) -> dict[str, float]:
    """Return {stable_id: similarity} for *query_text*, or {} if semantic search
    is unavailable (no API key, network/BigQuery failure, or a too-short query).

    Keyword search always still works when this returns {} — see §5.27's
    fallback guardrail. Cached per normalized query text (TTL'd) so repeated
    filter-only changes on an unchanged search box don't re-call OpenAI/BigQuery.
    """
    text = _normalize_text(query_text)
    if len(text) < _SEMANTIC_MIN_QUERY_LEN:
        return {}
    embedding, scores = _cached_query_embedding(text)
    if scores is not None:
        return scores
    if embedding is None:
        embedding = _embed_query(query_text)
    if embedding is None:
        return {}
    try:
        scores = _vector_search(embedding)
    except Exception:
        logger.exception("Discover semantic search: BigQuery VECTOR_SEARCH failed")
        return {}
    with _semantic_cache_lock:
        _semantic_cache[text] = (time.monotonic(), embedding, scores)
    return scores


def _item_similarity(stable_id: str, embedding: list[float]) -> float | None:
    """Cosine similarity between *embedding* and one specific item's stored embedding.

    A direct point lookup (not VECTOR_SEARCH's top_k), since the clicked item may not
    be among the top-k nearest neighbours returned by semantic_discover_candidates().
    """
    from google.cloud.bigquery import ArrayQueryParameter, ScalarQueryParameter

    sql = f"""
    SELECT 1 - COSINE_DISTANCE(embedding_vector, @qvec) AS similarity
    FROM {_table(DISCOVER_VECTORS_TABLE)}
    WHERE stable_id = @stable_id
    """
    params = [
        ArrayQueryParameter("qvec", "FLOAT64", embedding),
        ScalarQueryParameter("stable_id", "STRING", stable_id),
    ]
    df = run_query_params(sql, params)
    if df.empty:
        return None
    return max(0.0, min(1.0, float(df.iloc[0]["similarity"])))


def discover_item_similarity(record: dict[str, Any], search_text: str) -> float | None:
    """Similarity between *search_text*'s embedding and *record*'s stored embedding.

    None when semantic search is unavailable (no API key, no stable id, query too
    short, or any BigQuery/network failure) — the keyword-search detail view simply
    omits the "Similarity to search" KPI in that case.
    """
    stable_id = record.get("_stable_id")
    text = _normalize_text(search_text)
    if not stable_id or len(text) < _SEMANTIC_MIN_QUERY_LEN:
        return None
    embedding, _scores = _cached_query_embedding(text)
    if embedding is None:
        embedding = _embed_query(search_text)
    if embedding is None:
        return None
    try:
        return _item_similarity(stable_id, embedding)
    except Exception:
        logger.exception("Discover semantic search: item similarity lookup failed")
        return None


def filter_discover_records(
    records: list[dict[str, Any]],
    *,
    source_filter: list[str] | str | None,
    sentiment_filter: list[str] | str | None,
    publisher_filter: list[str] | str | None,
    topic_area_filter: list[str] | str | None,
    narrative_filter: list[str] | str | None,
    date_range: list[int] | None,
    search_text: str | None,
    search_fulltext: bool = False,
    selected_ids: list[Any] | set[Any] | None = None,
    reference_record: dict[str, Any] | None = None,
    similarity_radius: float | None = None,
    semantic_scores: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """``semantic_scores`` (optional): {stable_id: similarity} from
    ``semantic_discover_candidates()``. Semantic-only matches (no lexical hit)
    rank below every lexical tier — see §5.27's "hybrid, not a replacement" rule.
    Pass ``None``/``{}`` to skip semantic ranking entirely (e.g. no API key).
    """
    sources = set(_filter_trad_some(source_filter))
    sentiments = set(sentiment_filter or [])
    publishers = set(publisher_filter or [])
    topic_areas = set(topic_area_filter or [])
    narratives = set(narrative_filter or [])
    selected_id_set = set(selected_ids) if selected_ids else None
    query_tokens = _stemmed_tokens(search_text or "")
    query_phrase = _normalize_text(search_text or "") if query_tokens else ""

    if date_range and len(date_range) == 2:
        date_lo, date_hi = int(date_range[0]), int(date_range[1])
    else:
        date_lo, date_hi = None, None

    ref_point = _umap_point(reference_record) if reference_record else None
    use_similarity = ref_point is not None and similarity_radius is not None and similarity_radius > 0

    ranked: list[tuple[tuple[int, float], dict[str, Any]]] = []
    for record in records:
        if sources and record.get("Source") not in sources:
            continue
        if sentiments and record.get("Sentiment") not in sentiments:
            continue
        if publishers and record.get("Publisher") not in publishers:
            continue
        if topic_areas and record.get("Topic_Area") not in topic_areas:
            continue
        if narratives and record.get("Narrative") not in narratives:
            continue
        if date_lo is not None:
            index = int(record.get("_date_index", 0))
            if index < date_lo or index > date_hi:
                continue
        rank_key = (0, 0.0)
        if query_tokens:
            index_ = record.get("_search_index")
            if index_ is None:
                index_ = _build_search_index(record)
                record["_search_index"] = index_
            tier = _search_rank(index_, query_tokens, query_phrase, search_fulltext)
            if tier is None:
                similarity = (semantic_scores or {}).get(record.get("_stable_id"))
                if similarity is None:
                    continue
                rank_key = (5, -similarity)  # below every lexical tier; highest similarity first
            else:
                rank_key = (tier, 0.0)
        if selected_id_set is not None and record.get("_id") not in selected_id_set:
            continue
        if use_similarity:
            pt = _umap_point(record)
            if pt is None:
                continue
            x0, y0 = ref_point
            x, y = pt
            if ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5 > similarity_radius:
                continue
        ranked.append((rank_key, record))

    if query_tokens:
        ranked.sort(key=lambda pair: pair[0])
    return [record for _, record in ranked]


# ---------------------------------------------------------------------------
# Table data mapping
# ---------------------------------------------------------------------------


def discover_split_table_data(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (trad_data, some_data) in a single pass — avoids two O(n) scans."""
    trad_data: list[dict[str, Any]] = []
    some_data: list[dict[str, Any]] = []
    for record in records:
        source = record.get("Source")
        if source == "Trad":
            trad_data.append({
                "_id": record.get("_id"),
                "Date": record.get("Date", ""),
                "Media_Type": record.get("Media_Type", ""),
                "Publication": record.get("Publisher", ""),
                "Title": record.get("Title", ""),
                "Summary": record.get("Summary", ""),
                "URL": f"[Open]({record['URL']})" if record.get("URL") else "",
                "Sentiment": record.get("Sentiment", ""),
                "Reach": record.get("Reach", 0),
            })
        elif source == "SoMe":
            some_data.append({
                "_id": record.get("_id"),
                "Date": record.get("Date", ""),
                "Platform": record.get("Media_Type", ""),
                "Author": record.get("Publisher", ""),
                "Post_Content": record.get("Title", ""),
                "URL": f"[Open]({record['URL']})" if record.get("URL") else "",
                "Sentiment": record.get("Sentiment", ""),
                "Reach": record.get("Reach", 0),
                "Engagement": record.get("Engagement", 0),
            })
    return trad_data, some_data


# ---------------------------------------------------------------------------
# UI builders
# ---------------------------------------------------------------------------


def _control(label: str, dropdown_id: str, options: list[dict[str, str]]) -> html.Div:
    return html.Div(
        className="amazon-publishers-control",
        children=[
            html.Div(label, className="amazon-publishers-control-label"),
            dcc.Dropdown(
                id=dropdown_id,
                options=options,
                value=[],
                multi=True,
                searchable=True,
                placeholder="All",
                className="amazon-publishers-dropdown",
            ),
        ],
    )


def build_discover_filters_panel(
    records: list[dict[str, Any]],
    date_bounds: dict[str, Any],
    options: dict[str, list[dict[str, str]]],
) -> html.Div:
    max_index = int(date_bounds.get("max_index", 0))
    marks = discover_date_marks(date_bounds)
    clear_filters_btn = html.Button(
        [html.Span("filter_alt_off", className="material-symbols-outlined"), "Clear filters"],
        id="amazon-2026-discover-clear-filters-btn",
        className="amazon-discover-clear-filters-btn",
        n_clicks=0,
        type="button",
    )
    return na_panel(
        "",
        [
            html.Div(
                className="amazon-discover-mode-tabs",
                children=[
                    html.Button(
                        "Keyword Search",
                        id="amazon-2026-discover-mode-keyword-tab",
                        className="amazon-discover-mode-tab is-active",
                        n_clicks=0,
                        type="button",
                    ),
                    html.Button(
                        "Reference Similarity",
                        id="amazon-2026-discover-mode-reference-tab",
                        className="amazon-discover-mode-tab",
                        n_clicks=0,
                        type="button",
                    ),
                ],
            ),
            html.Div(
                className="amazon-discover-search-row",
                children=[
                    html.Div(
                        id="amazon-2026-discover-search-col-wrap",
                        className="amazon-discover-search-col",
                        children=[
                            html.Div("Search", className="amazon-publishers-control-label"),
                            html.Div(
                                className="amazon-discover-search-input-wrap",
                                children=[
                                    dcc.Input(
                                        id="amazon-2026-discover-search",
                                        type="text",
                                        placeholder="Search author, publisher, title, or text...",
                                        debounce=True,
                                        className="amazon-discover-search",
                                    ),
                                    html.Button(
                                        html.Span("close", className="material-symbols-outlined"),
                                        id="amazon-2026-discover-search-clear",
                                        className="amazon-discover-search-clear",
                                        n_clicks=0,
                                        type="button",
                                        title="Clear search",
                                    ),
                                ],
                            ),
                            dcc.Checklist(
                                id="amazon-2026-discover-search-fulltext",
                                options=[{"label": "Search full text", "value": "fulltext"}],
                                value=[],
                                className="amazon-discover-search-fulltext",
                            ),
                        ],
                    ),
                    html.Div(
                        id="amazon-2026-discover-reference-col-wrap",
                        className="amazon-discover-reference-col",
                        style={"display": "none"},
                        children=[
                            html.Div("Reference Publication", className="amazon-publishers-control-label"),
                            html.Div(
                                id="amazon-2026-discover-reference-box",
                                className="amazon-discover-reference-box",
                                children=[
                                    html.Div(
                                        id="amazon-2026-discover-reference-content",
                                        className="amazon-discover-reference-content",
                                        children=discover_reference_placeholder(),
                                    ),
                                    html.Button(
                                        html.Span("close", className="material-symbols-outlined"),
                                        id="amazon-2026-discover-reference-clear",
                                        className="amazon-discover-reference-clear",
                                        n_clicks=0,
                                        type="button",
                                        title="Clear reference",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="amazon-discover-similarity-row",
                                children=[
                                    html.Div("Similarity", className="amazon-publishers-control-label"),
                                    dcc.Slider(
                                        id="amazon-2026-discover-similarity-slider",
                                        min=0,
                                        max=10,
                                        step=0.1,
                                        value=5,
                                        marks={0: "Close", 10: "Far"},
                                        tooltip=None,
                                        className="amazon-discover-similarity-slider",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                className="amazon-discover-controls-header",
                children=[
                    html.Div(ref_label("Filters", "P8S1"), className="amazon-publishers-control-label"),
                    clear_filters_btn,
                ],
            ),
            html.Div(
                className="amazon-discover-controls",
                children=[
                    _control("Source", "amazon-2026-discover-source-filter", TRAD_SOME_OPTIONS),
                    _control("Sentiment", "amazon-2026-discover-sentiment-filter", SENTIMENT_OPTIONS),
                    _control("Publisher", "amazon-2026-discover-publisher-filter", options["publisher"]),
                    _control("Topic Area", "amazon-2026-discover-topicarea-filter", options["topic_area"]),
                    _control("Narrative", "amazon-2026-discover-narrative-filter", options["narrative"]),
                ],
            ),
            html.Div(
                className="amazon-discover-date-row",
                children=[
                    html.Div("Date Range", className="amazon-publishers-control-label"),
                    html.Div(id="amazon-2026-discover-date-label", className="amazon-discover-date-label"),
                    dcc.RangeSlider(
                        id="amazon-2026-discover-date-range",
                        min=0,
                        max=max_index,
                        step=1,
                        value=[0, max_index],
                        marks=marks,
                        allowCross=False,
                        className="amazon-discover-rangeslider",
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Reference article (UMAP similarity anchor)
# ---------------------------------------------------------------------------


def discover_reference_placeholder() -> html.Div:
    return html.Div(
        "Pick a result below and click \"Use as reference\" to search by similarity.",
        className="amazon-discover-reference-empty",
    )


def discover_short_date(date_value: Any) -> str:
    parsed = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(parsed):
        return str(date_value or "")
    return parsed.strftime("%d %b %Y")


def build_discover_reference_content(record: dict[str, Any] | None) -> html.Div:
    if not record:
        return discover_reference_placeholder()
    return html.Div(
        className="amazon-discover-reference-item",
        children=[
            html.Span(discover_short_date(record.get("Date")), className="amazon-discover-reference-date"),
            html.Span(record.get("Publisher") or "Unknown", className="amazon-discover-reference-publisher"),
            html.Span(record.get("Title") or "(untitled)", className="amazon-discover-reference-title"),
        ],
    )


# ---------------------------------------------------------------------------
# Narrative clusters (UMAP)
# ---------------------------------------------------------------------------


def discover_cluster_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for record in records:
        x, y = record.get("umap_x"), record.get("umap_y")
        if x in (None, "") or y in (None, ""):
            continue
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError):
            continue
        out.append(
            {
                "_id": record.get("_id"),
                "umap_x": x,
                "umap_y": y,
                "narrative_label": record.get("Narrative") or "",
                "source": record.get("Source") or "",
                "_date_index": record.get("_date_index") or 0,
            }
        )
    return out


def build_discover_stores_section(
    date_bounds: dict[str, Any],
    color_map: dict[str, str],
) -> html.Div:
    """Hidden panel holding all dcc.Stores for the Discover page.

    Records are NOT stored here — they live in _server_discover_data() so
    callbacks read from server memory rather than round-tripping the full
    dataset through the browser on every filter change.
    """
    return html.Div(
        style={"display": "none"},
        children=[
            dcc.Store(id="amazon-2026-discover-bounds", data=date_bounds),
            dcc.Store(id="amazon-2026-discover-detail-id", data=None),
            dcc.Store(id="amazon-2026-discover-search-mode", data="keyword"),
            dcc.Store(id="amazon-2026-discover-reference-data", data=None),
            dcc.Store(id="amazon-2026-discover-selected-ids", data=None),
            dcc.Store(id="amazon-2026-discover-clusters-selections", data=None),
            dcc.Store(id="amazon-2026-discover-clusters-colormap", data=color_map),
            dcc.Store(id="amazon-2026-discover-umap-open", data=False),
            dcc.Store(id="amazon-2026-discover-stats-open", data=False),
        ],
    )


def build_discover_clusters_section() -> html.Div:
    """Build the collapsed UMAP panel shell.

    The figure itself is built lazily by _update_discover_clusters on first
    open (gated on amazon-2026-discover-umap-open) rather than eagerly here,
    since computing it for a panel the user may never expand wastes the
    page-load budget on every visit.
    """
    initial_fig = go.Figure()
    toggle_btn = html.Button(
        "Show",
        id="amazon-2026-discover-umap-toggle",
        n_clicks=0,
        className="amazon-discover-umap-toggle",
    )
    return na_panel(
        ref_label("Narrative Clusters (UMAP)", "P8S2G1"),
        [
            html.Div(
                id="amazon-2026-discover-umap-container",
                style={"display": "none"},
                children=[
                    html.Div(
                        className="amazon-publishers-chart-controls",
                        children=[
                            dcc.Checklist(
                                id="amazon-2026-discover-clusters-color-toggle",
                                options=[{"label": "Color by narrative", "value": "color"}],
                                value=["color"],
                                inline=True,
                                className="amazon-publishers-radio",
                            ),
                            dcc.Checklist(
                                id="amazon-2026-discover-clusters-kde-toggle",
                                options=[{"label": "KDE", "value": "kde"}],
                                value=[],
                                inline=True,
                                className="amazon-publishers-radio",
                            ),
                            dcc.Checklist(
                                id="amazon-2026-discover-clusters-time-toggle",
                                options=[{"label": "Color by time", "value": "time"}],
                                value=[],
                                inline=True,
                                className="amazon-publishers-radio",
                            ),
                            dcc.Checklist(
                                id="amazon-2026-discover-clusters-relative-toggle",
                                options=[{"label": "Relative to selected range", "value": "relative"}],
                                value=[],
                                inline=True,
                                className="amazon-publishers-radio",
                                style={"display": "none"},
                            ),
                            html.Div(
                                id="amazon-2026-discover-time-legend",
                                className="amazon-discover-time-legend",
                                style={"display": "none"},
                                children=[
                                    html.Span("Older"),
                                    html.Div(className="amazon-discover-time-legend-bar"),
                                    html.Span("Newer"),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        id="amazon-2026-discover-selection-banner",
                        className="amazon-discover-selection-banner",
                        style={"display": "none"},
                        children=[
                            html.Span(id="amazon-2026-discover-selection-text"),
                            html.Button(
                                [html.Span("close", className="material-symbols-outlined"), "Clear selection"],
                                id="amazon-2026-discover-selection-clear",
                                className="amazon-discover-selection-clear",
                                n_clicks=0,
                            ),
                        ],
                    ),
                    html.Div(
                        "Tip: use the lasso or box-select tool in the chart toolbar above to pick points and "
                        "filter the results table to that selection.",
                        className="amazon-discover-selection-hint",
                    ),
                    dcc.Graph(
                        id="amazon-2026-discover-clusters-graph",
                        figure=initial_fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "responsive": True,
                            "toImageButtonOptions": {"format": "svg", "filename": "amazon_2026_discover_umap"},
                        },
                        style={"height": "800px"},
                    ),
                ],
            ),
        ],
        controls=toggle_btn,
    )


def build_discover_results_panel(trad_table_data: list[dict[str, Any]], some_table_data: list[dict[str, Any]]) -> html.Div:
    has_trad = bool(trad_table_data)
    has_some = bool(some_table_data)
    available_sources = (["Trad"] if has_trad else []) + (["SoMe"] if has_some else [])
    default_source = available_sources[0] if available_sources else "Trad"
    options = [
        {"label": opt["label"], "value": opt["value"], "disabled": opt["value"] not in available_sources}
        for opt in TRAD_SOME_OPTIONS
    ]
    controls = html.Div(
        id="amazon-2026-discover-source-controls",
        className="amazon-publishers-chart-controls",
        style={"display": "none"} if len(available_sources) <= 1 else None,
        children=[
            dcc.RadioItems(
                id="amazon-2026-discover-top-items-source",
                options=options,
                value=default_source,
                inline=True,
                className="amazon-publishers-radio",
            )
        ],
    )
    # Both tables are always in the DOM; visibility is toggled by wrappers.
    # This avoids remounting the DataTable on filter changes, which would
    # reset active_cell and lose row selection.
    trad_visible = default_source == "Trad"
    trad_table = build_top_publications_table(
        "amazon-2026-discover-top-publications", trad_table_data, show_publication_col=True
    )
    some_table = build_top_posts_table(
        "amazon-2026-discover-top-posts", some_table_data, show_author_col=True
    )
    return na_panel(
        ref_label("Results", "P8S3"),
        [
            html.Div(id="amazon-2026-discover-results-count", className="amazon-discover-results-count"),
            html.Div(
                id="amazon-2026-discover-trad-table-wrapper",
                style=None if trad_visible else {"display": "none"},
                children=trad_table,
            ),
            html.Div(
                id="amazon-2026-discover-some-table-wrapper",
                style={"display": "none"} if trad_visible else None,
                children=some_table,
            ),
        ],
        controls=controls,
    )


def discover_results_count_label(trad_table_data: list[dict[str, Any]], some_table_data: list[dict[str, Any]]) -> str:
    total = len(trad_table_data) + len(some_table_data)
    if total == 0:
        return "No items match the current filters."
    if total == 1:
        return "1 item matches the current filters."
    return f"{total} items match the current filters ({len(trad_table_data)} Trad, {len(some_table_data)} SoMe)."


def discover_trad_tooltip_data(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"Summary": {"value": str(row.get("Summary", "")), "type": "text"}} for row in table_data]


def discover_some_tooltip_data(table_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"Post_Content": {"value": str(row.get("Post_Content", "")), "type": "text"}} for row in table_data]


# ---------------------------------------------------------------------------
# Result stats (collapsible section below the Results table)
# ---------------------------------------------------------------------------

_STATS_DONUT_HEIGHT = 160
_STATS_BAR_HEIGHT = 320
_STATS_BAR_TOP_N = 10


def _stats_category_donut(
    records: list[dict[str, Any]], field: str, title: str, source: str | None = None
) -> html.Div:
    counts = Counter(str(r.get(field) or "").strip() or "Unknown" for r in records)
    if not counts:
        return empty_donut_panel(f"No {title.lower()} data")
    labels = [label for label, _ in counts.most_common()]
    values = [counts[label] for label in labels]
    colors = [media_label_color(label, source) for label in labels]
    figure = donut_figure(
        labels, values, colors, hovertemplate="%{label}: %{value:,.0f} (%{percent:.1%})<extra></extra>"
    )
    return donut_panel(title, figure, graph_height=_STATS_DONUT_HEIGHT)


def _stats_sentiment_donut(records: list[dict[str, Any]], title: str) -> html.Div:
    counts = Counter(r.get("Sentiment") for r in records if r.get("Sentiment"))
    labels, values, colors = sentiment_donut_slices(
        counts.get("Positive", 0), counts.get("Neutral", 0), counts.get("Negative", 0)
    )
    if not labels:
        return empty_donut_panel(f"No {title.lower()} data")
    figure = donut_figure(
        labels, values, colors, hovertemplate="%{label}: %{value:,.0f} (%{percent:.1%})<extra></extra>"
    )
    return donut_panel(title, figure, graph_height=_STATS_DONUT_HEIGHT)


def _stats_engagement_sentiment_donut(some_records: list[dict[str, Any]]) -> html.Div:
    pos = sum(num(r, "Engagement_Positive") for r in some_records)
    neg = sum(num(r, "Engagement_Negative") for r in some_records)
    neu = sum(num(r, "Engagement_Neutral") for r in some_records)
    labels, values, colors = sentiment_donut_slices(pos, neu, neg)
    if not labels:
        return empty_donut_panel("No engagement sentiment data")
    figure = donut_figure(
        labels, values, colors, hovertemplate="%{label}: %{value:,.0f} (%{percent:.1%})<extra></extra>"
    )
    return donut_panel("Engagement sentiment", figure, graph_height=_STATS_DONUT_HEIGHT)


def _stats_topic_area_treemap(records: list[dict[str, Any]], title: str) -> html.Div:
    counts = Counter(str(r.get("Topic_Area") or "").strip() for r in records)
    counts.pop("", None)
    if not counts:
        return empty_donut_panel(f"No {title.lower()} data")
    labels = sorted(counts, key=lambda k: -counts[k])
    values = [counts[label] for label in labels]
    color_map = topic_area_color_map(labels)
    figure = go.Figure(
        go.Treemap(
            ids=labels,
            labels=labels,
            parents=[""] * len(labels),
            values=values,
            branchvalues="total",
            marker={
                "colors": [color_map[label] for label in labels],
                "line": {"color": "rgba(255,255,255,0.55)", "width": 1},
            },
            texttemplate="<b>%{label}</b><br>%{value:,.0f}",
            textfont={"color": THEME_TEXT, "size": 13},
            hovertemplate="%{label}: %{value:,.0f}<br>Share: %{percentRoot:.1%}<extra></extra>",
            tiling={"packing": "squarify", "pad": 3},
            pathbar={"visible": False},
        )
    )
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_TEXT},
        margin={"l": 0, "r": 0, "t": 4, "b": 0},
        uniformtext={"minsize": 11, "mode": "hide"},
        hoverlabel={"bgcolor": THEME_SURFACE, "bordercolor": THEME_BORDER, "font": {"color": THEME_TEXT}},
    )
    return donut_panel(title, figure, graph_height=_STATS_BAR_HEIGHT)


def _stats_category_bar(records: list[dict[str, Any]], field: str, title: str) -> html.Div:
    counts = Counter(str(r.get(field) or "").strip() for r in records)
    counts.pop("", None)
    if not counts:
        return empty_donut_panel(f"No {title.lower()} data")
    top = list(reversed(counts.most_common(_STATS_BAR_TOP_N)))
    labels = [label for label, _ in top]
    values = [value for _, value in top]
    colors = [DONUT_COLORS[i % len(DONUT_COLORS)] for i in range(len(labels))]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={"color": colors},
            text=[f"{v:,.0f}" for v in values],
            textposition="outside",
            textfont={"color": THEME_TEXT},
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": THEME_TEXT},
        margin={"l": 8, "r": 36, "t": 8, "b": 8},
        xaxis={"gridcolor": THEME_GRID, "zeroline": False},
        yaxis={"automargin": True},
        showlegend=False,
        height=_STATS_BAR_HEIGHT,
        hoverlabel={"bgcolor": THEME_SURFACE, "bordercolor": THEME_BORDER, "font": {"color": THEME_TEXT}},
    )
    return donut_panel(title, figure, graph_height=_STATS_BAR_HEIGHT)


def build_discover_stats_content(records: list[dict[str, Any]]) -> html.Div:
    trad = [r for r in records if r.get("Source") == "Trad"]
    some = [r for r in records if r.get("Source") == "SoMe"]
    total_reach = sum(num(r, "Reach") for r in records)
    total_engagement = sum(num(r, "Engagement") for r in some)

    kpis = html.Div(
        [
            kpi_card("Total Items", f"{len(records):,}", compact=True),
            kpi_card("Trad Publications", f"{len(trad):,}", compact=True),
            kpi_card("SoMe Posts", f"{len(some):,}", compact=True),
            kpi_card("Total Reach", f"{total_reach:,.0f}", compact=True),
            kpi_card("Total Engagement", f"{total_engagement:,.0f}", compact=True),
        ],
        className="amazon-discover-stats-kpis",
    )

    donuts = html.Div(
        [
            _stats_category_donut(trad, "Media_Type", "Media Type (Trad)", source="Trad"),
            _stats_category_donut(some, "Media_Type", "Platform (SoMe)", source="SoMe"),
            _stats_sentiment_donut(trad, "Publication sentiment"),
            _stats_sentiment_donut(some, "Post sentiment"),
            _stats_engagement_sentiment_donut(some),
        ],
        className="amazon-discover-stats-donuts",
    )

    bars = html.Div(
        [
            _stats_topic_area_treemap(records, "Topic Areas"),
            _stats_category_bar(records, "Narrative", "Narratives"),
        ],
        className="amazon-discover-stats-bars",
    )

    return html.Div([kpis, donuts, bars], id="amazon-2026-discover-stats-content")


def build_discover_stats_section() -> html.Div:
    """Build the collapsed stats panel shell.

    Content is built lazily by _update_discover_stats on first open (gated on
    amazon-2026-discover-stats-open) rather than eagerly here — see
    build_discover_clusters_section for the same reasoning.
    """
    toggle_btn = html.Button(
        "Show",
        id="amazon-2026-discover-stats-toggle",
        n_clicks=0,
        className="amazon-discover-umap-toggle",
    )
    return na_panel(
        ref_label("Result Stats", "P8S3N1"),
        [
            html.Div(
                id="amazon-2026-discover-stats-container",
                style={"display": "none"},
                children=[html.Div(id="amazon-2026-discover-stats-content")],
            ),
        ],
        controls=toggle_btn,
    )


# ---------------------------------------------------------------------------
# Publication details panel
# ---------------------------------------------------------------------------


def discover_detail_placeholder() -> html.Div:
    return html.Div(
        "Click a row in the results table above to see publication details.",
        className="amazon-publishers-empty",
    )


def find_discover_record(records: list[dict[str, Any]], record_id: Any) -> dict[str, Any] | None:
    if record_id is None or not records:
        return None
    # _id equals the original DataFrame row index — try O(1) direct access first
    if isinstance(record_id, int) and 0 <= record_id < len(records):
        candidate = records[record_id]
        if candidate.get("_id") == record_id:
            return candidate
    for record in records:
        if record.get("_id") == record_id:
            return record
    return None


def _umap_point(record: dict[str, Any]) -> tuple[float, float] | None:
    x, y = record.get("umap_x"), record.get("umap_y")
    if x in (None, "") or y in (None, ""):
        return None
    try:
        return float(x), float(y)
    except (TypeError, ValueError):
        return None


_DONUT_GRAPH_HEIGHT = 160


def _discover_engagement_sentiment_donut(record: dict[str, Any]) -> html.Div | None:
    pos = num(record, "Engagement_Positive")
    neg = num(record, "Engagement_Negative")
    neu = num(record, "Engagement_Neutral")
    labels, values, colors = sentiment_donut_slices(pos, neu, neg)
    if not labels:
        return None
    figure = donut_figure(
        labels, values, colors, hovertemplate="%{label}: %{value:,.0f} (%{percent:.1%})<extra></extra>"
    )
    return donut_panel("Engagement by sentiment", figure, graph_height=_DONUT_GRAPH_HEIGHT)


def _discover_detail_kpis(record: dict[str, Any], similarity: float | None = None) -> list[html.Div]:
    source = record.get("Source", "")
    cards = [kpi_card("Platform" if source == "SoMe" else "Media Type", record.get("Media_Type") or "Unknown")]
    cards.append(kpi_card("Sentiment", record.get("Sentiment") or "Neutral"))
    cards.append(kpi_card("Reach", f"{num(record, 'Reach'):,.0f}"))
    if source == "SoMe":
        cards.append(kpi_card("Engagement", f"{num(record, 'Engagement'):,.0f}"))
    if similarity is not None:
        cards.append(kpi_card("Similarity to search", f"{similarity:.0%}"))
    return cards


def build_discover_detail_content(record: dict[str, Any] | None, similarity: float | None = None) -> html.Div:
    if not record:
        return discover_detail_placeholder()

    source = record.get("Source", "")
    title = record.get("Title") or "(untitled)"
    url = record.get("URL") or ""

    if source == "SoMe":
        body_children = _build_some_post_body(record, url)
    else:
        body_children = _build_trad_body(record, url)

    kpi_left_children: list[Any] = [
        html.Div(_discover_detail_kpis(record, similarity), className="amazon-discover-detail-kpis-cards"),
    ]
    if source == "SoMe":
        donut = _discover_engagement_sentiment_donut(record)
        if donut is not None:
            kpi_left_children.append(donut)

    children: list[Any] = [
        html.Div(
            className="amazon-discover-detail-grid",
            children=[
                html.Div(kpi_left_children, className="amazon-discover-detail-kpis"),
                html.Div(body_children, className="amazon-discover-detail-body"),
            ],
        )
    ]

    if source == "Trad":
        full_text = (record.get("Full_Text") or "").strip()
        summary = (record.get("Summary") or "").strip()
        if full_text and full_text != summary and full_text != title:
            children.append(
                html.Details(
                    className="amazon-discover-detail-fulltext",
                    children=[
                        html.Summary("Show full text"),
                        html.P(full_text),
                    ],
                )
            )

    return html.Div(children)


def _build_some_post_body(record: dict[str, Any], url: str) -> list[Any]:
    author = record.get("Publisher") or "Unknown"
    platform = record.get("Media_Type") or "Unknown"
    date = record.get("Date") or "—"
    followers = int(num(record, "Followers"))
    title = record.get("Title") or "(no content)"

    tag_items = []
    if record.get("Topic_Area"):
        tag_items.append(
            html.Div(
                className="amazon-discover-some-post-tag",
                children=[
                    html.Span("Topic Area", className="amazon-publishers-kpi-label"),
                    html.Div(record["Topic_Area"], className="amazon-publishers-type"),
                ],
            )
        )
    if record.get("Narrative"):
        tag_items.append(
            html.Div(
                className="amazon-discover-some-post-tag",
                children=[
                    html.Span("Narrative", className="amazon-publishers-kpi-label"),
                    html.Div(record["Narrative"], className="amazon-publishers-type"),
                ],
            )
        )

    header = html.Div(
        className="amazon-discover-some-post-header",
        children=[
            html.Div(
                className="amazon-discover-some-post-author-block",
                children=[
                    html.Div(
                        children=[
                            html.Span(author, className="amazon-discover-some-post-author"),
                            html.Span(platform, className="amazon-publishers-type amazon-discover-some-post-platform"),
                        ],
                        className="amazon-discover-some-post-author-row",
                    ),
                    html.Div(
                        children=[
                            html.Span(date, className="amazon-discover-some-post-date"),
                            *(
                                [html.Span(f"{followers:,.0f} followers", className="amazon-discover-some-post-followers")]
                                if followers > 0
                                else []
                            ),
                        ],
                        className="amazon-discover-some-post-meta-row",
                    ),
                ],
            ),
        ],
    )

    body: list[Any] = [
        header,
        html.Div(title, className="amazon-discover-some-post-content"),
    ]
    if tag_items:
        body.append(html.Div(tag_items, className="amazon-discover-some-post-tags"))
    if url:
        body.append(
            html.A(
                "Open post",
                href=url,
                target="_blank",
                rel="noopener noreferrer",
                className="amazon-discover-some-post-link",
            )
        )
    return body


def _build_trad_body(record: dict[str, Any], url: str) -> list[Any]:
    title = record.get("Title") or "(untitled)"
    summary = (record.get("Summary") or "").strip() or "No summary available."
    publisher_label = "Publisher"

    meta_items = [
        ("Date", record.get("Date") or "—"),
        (publisher_label, record.get("Publisher") or "Unknown"),
    ]
    journalist = str(record.get("Journalist") or "").strip()
    if journalist:
        meta_items.append(("Journalist", journalist))
    if record.get("Topic_Area"):
        meta_items.append(("Topic Area", record["Topic_Area"]))
    if record.get("Narrative"):
        meta_items.append(("Narrative", record["Narrative"]))

    badges = [
        html.Div("Trad", className="amazon-publishers-type"),
        html.Div(record.get("Media_Type") or "Unknown", className="amazon-publishers-type"),
    ]

    children: list[Any] = [
        html.Div(badges, className="amazon-publishers-badge-row"),
        html.H3(title),
        html.Div(html.P(summary), className="amazon-publishers-profile-summary"),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(label, className="amazon-publishers-kpi-label"),
                        html.Div(str(value), className="amazon-discover-detail-meta-value"),
                    ],
                    className="amazon-discover-detail-meta-item",
                )
                for label, value in meta_items
            ],
            className="amazon-discover-detail-meta",
        ),
    ]
    if url:
        children.append(
            html.Div(
                className="amazon-publishers-links",
                children=[
                    html.Div("Source", className="amazon-publishers-links-title"),
                    html.Div(
                        className="amazon-publishers-link-list",
                        children=[html.A("Open original", href=url, target="_blank", rel="noopener noreferrer")],
                    ),
                ],
            )
        )
    return children


def build_discover_detail_section() -> html.Div:
    return na_panel(
        ref_label("Publication Details", "P8S4"),
        [html.Div(id="amazon-2026-discover-detail-content", children=discover_detail_placeholder())],
        controls=html.Button(
            [html.Span("bookmark_add", className="material-symbols-outlined"), "Use as reference"],
            id="amazon-2026-discover-use-as-reference-btn",
            className="amazon-discover-reference-btn",
            n_clicks=0,
            type="button",
        ),
    )
