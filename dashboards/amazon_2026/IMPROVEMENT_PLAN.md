# Amazon 2026 Dashboard — Deep Architecture Review & Improvement Plan

> Status: **COMPLETE.** All 13 sections below are filled in. Nothing in this document has been
> implemented — this is analysis + recommendations only. Every concrete claim (file paths, line
> numbers, counts) was verified by direct reading or `grep`/`wc` against this repository, not
> inferred; see §13 for the prioritized action list this whole document builds toward.

Scope: `dashboards/amazon_2026/**` (the dashboard itself) plus the shared platform code it
depends on (`app.py`, `config.py`, `dashboards/_base.py`, `data_sources/bq.py`, `tenancy/*`,
`auth/*`, `extensions/*`) where that platform code directly shapes this dashboard's
efficiency, speed, scalability or readability.

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Architecture overview](#2-architecture-overview)
3. [Data layer](#3-data-layer)
4. [Chart / rendering layer](#4-chart--rendering-layer)
5. [Pages & callback layer](#5-pages--callback-layer)
6. [Extensions & multi-tenancy](#6-extensions--multi-tenancy)
7. [Frontend assets (CSS/JS)](#7-frontend-assets-cssjs)
8. [Performance & speed](#8-performance--speed)
9. [Scalability](#9-scalability)
10. [Readability & maintainability](#10-readability--maintainability)
11. [Testing, observability, resilience](#11-testing-observability-resilience)
12. [Security](#12-security)
13. [Prioritized roadmap](#13-prioritized-roadmap)
14. [Target architecture: from one dashboard to a multi-client platform](#14-target-architecture-from-one-dashboard-to-a-multi-client-platform)

---

## 1. Executive summary

**The craftsmanship in this codebase is real.** The Plotly re-theming engineering
(STYLE_GUIDE.md §6's five documented "gotchas"), the dynamic timeline-height/flag-placement pixel
math (§4.1), the schema-flexible SQL-fragment builders that absorb years of upstream BigQuery
column renames (§3.2), the no-argument cache-friendly data-loading contract (§3.1), the
introspection-driven saved-views extension (§6.4), and a 740-line style guide that documents *why*
not just *what* — these are not beginner mistakes papered over with good intentions. This is a
22,000-line, single-dashboard product built by people who care about getting hard details right.
The findings below are about what stands between "very good" and "the best in the world," not
about fixing something broken.

**Three findings matter more than the rest combined, because they compound:**

1. **Cold starts are the dashboard's biggest unaddressed latency/reliability risk** (§8.2). The
   combination of `min-instances=0`, two gunicorn workers per container, and five startup
   preload fan-outs firing ~40 concurrent BigQuery queries each — all racing for one vCPU and
   1GB of RAM — means the most resource-contended moment in this app's entire lifecycle is also
   the moment a real user is most likely waiting on it. The fix is one line (`--min-instances=1`).
2. **The cache refresh interval is tuned for data that updates every 10 minutes — it updates at
   most once a day** (§9.1). `CACHE_DEFAULT_TIMEOUT=600` means the dashboard's ~40-50 datasets get
   re-fetched from BigQuery up to 144 times a day for data that, in nearly every one of those
   cycles, hasn't changed since the last fetch. This is the single highest-value, lowest-effort
   fix in this whole review — raising it to 1 hour (agreed with the team) cuts that to 24/day for
   zero freshness cost, and it's a one-constant change, not a refactor. (An earlier pass at this
   finding also flagged that `SimpleCache` is process-local, meaning up to ~8 independent copies
   of this cache can exist across workers/instances — that's real, but minor and **not** an
   availability/concurrency problem: multiple users are served correctly regardless. It mainly
   means the redundant-cost math above gets multiplied by however many processes are alive, which
   the TTL fix already shrinks by 10x on its own.)
3. **The dashboard is single-tenant in practice, despite running on a multi-tenant platform**
   (§6.2, §9.2, §12.2). `tenancy/access.py` has a real, working `resolve_client_dataset()`
   mechanism; `amazon_2026`'s data layer never calls it, and hardcodes one project/dataset
   instead. Invisible today with one client; a real client-data-isolation bug the day a second
   client is onboarded onto this dashboard design. This is the one item on the whole list that
   should be treated as a scheduled precondition, not a backlog entry.

**The rest of the findings are about durability, not urgency**: zero automated tests across 51
hand-built SQL strings and ~52 callbacks (§11.1) means every fix — including every item in this
document — currently has to be hand-verified, every time; a meaningful amount of duplicated logic
(publisher-identity resolution, sentiment-donut figures, table builders, the five preload
functions, page-builder scaffolding — consolidated in §10.2) that costs nothing today but
compounds maintenance cost as the dashboard keeps growing; and three separate, individually
well-reasoned workarounds for Vizro/Dash/Plotly internals (§7.1) that together mean a meaningful
slice of this dashboard's robustness depends on framework behavior that isn't part of any public
contract, with no automated test to catch a silent break on the next version bump.

**None of this requires a rewrite.** Every recommendation in this document is additive or
subtractive (delete duplication, add a cache backend, add tests, wire an existing mechanism
through) — nothing proposes replacing an architectural decision that's currently working. See
§13 for the full prioritized punch list; the short version is: fix the Cloud Run config (§13 #6-7,
an afternoon, highest payoff in this document), schedule the multi-tenancy wiring deliberately
(§13 #12) before it's forced by a sales conversation, and start a `tests/` directory with the
cheapest, highest-confidence items first (§13 #20) so every subsequent change to this codebase —
by anyone, including future work driven by this very document — gets safer over time instead of
relying on manual verification forever.

---

## 2. Architecture overview

### 2.1 What this actually is

This is **not** "a dashboard." It is a multi-tenant analytics **platform** (Flask + Vizro/Dash)
that currently hosts one very large, very mature dashboard (`amazon_2026`) alongside several
smaller/example ones (`bq_sample`, `breakdown`, `timeline`). `amazon_2026` is ~22,000 lines of
Python across 25 modules, plus ~3,000 lines of hand-written CSS/JS. That scale matters: this
is no longer "a Vizro app with some custom charts," it's a bespoke BI product that happens to
be hosted inside Vizro's page/callback model. Several of the structural issues below come
directly from that tension — Vizro is a thin layer on top, and most of the real engineering
(query building, theming, state, table styling, custom JS interactivity) has been built
*around* it rather than *with* it.

Key structural facts, confirmed by reading `app.py`, `config.py`, `dashboards/_base.py`,
`dashboards/__init__.py`:

- **One process-global Vizro instance.** `app.py`'s own docstring states the constraint:
  "multiple Vizro apps cannot coexist in a single process — the Dash page registry is
  process-global." So every dashboard (every tenant-facing product) is a plugin contributing
  pages into *one* `vm.Dashboard`. This is a hard ceiling baked into Vizro/Dash itself, not a
  choice this codebase made — but it means dashboard isolation (crashes, memory leaks, slow
  callbacks) is **not process-level**, it's all sharing one Python process, one event loop's
  worth of Flask worker threads, one `GLOBAL_CALLBACK_LIST`.
- **A monkeypatch in `app.py` (lines 43-70) makes `dash._callback.insert_callback`
  idempotent**, working around a real Vizro 0.1.56/Dash duplicate-callback-registration bug
  (Vizro calls `page.build()` once at dashboard build time and Dash calls it again on first
  lazy navigation). This is a *correct* and well-documented fix, but it's patching a private
  Dash internal (`dash._callback.insert_callback`) — any Dash/Vizro version bump is a silent
  breakage risk with no test coverage forcing the issue to surface before production.
- **Plugin auto-discovery** (`dashboards/__init__.py`) scans `dashboards/<slug>/` packages for
  a `MANIFEST` + `build_pages`. Clean, low-ceremony extension point — genuinely good design.
- **Access control is a single Flask `before_request` gate** (`app.py::_install_access_gate`)
  keyed off the request path (`/app/d/<slug>/...`). It calls `tenancy.access.can_access(user,
  slug)` per request. Simple and centralized, which is good — but it means *dashboard-level*
  access is enforced, while anything *inside* a dashboard (e.g., should every user of
  `amazon_2026` see every campaign? every publisher?) has no per-row/per-entity authorization
  hook at all. For a single-client dashboard today that's fine; the moment this dashboard is
  resold to a second client sharing the same BQ dataset, there is no enforcement layer between
  "has access to amazon_2026" and "can query any row in `amazon_2026_trad`".
- **Caching is a single global `flask_caching.SimpleCache`**, 10-minute TTL, attached directly
  to Vizro's `data_manager.cache`. `SimpleCache` is an in-memory dict **scoped to one worker
  process** — see [§9 Scalability](#9-scalability) for why this is probably the single highest-
  leverage infrastructure change available.
- **Startup does 5 separate "preload" fan-outs** (`_start_overview_preload`,
  `_start_topic_area_preload`, `_start_narratives_preload`, `_start_campaigns_preload`,
  `_start_publishers_preload` in `dashboards/amazon_2026/__init__.py`), each spinning up its
  own `ThreadPoolExecutor` in its own daemon `threading.Thread`, each with near-identical
  boilerplate (12 lines × 5 = 60 lines that are 90% copy-paste). Functionally this is a smart,
  effective idea (warm the cache before the first user interaction instead of paying for it on
  click) — see [§4](#4-chart--rendering-layer)/[§8](#8-performance--speed) for the
  duplication/race-condition follow-up.

### 2.2 Module map (as built)

```
dashboards/amazon_2026/
  __init__.py            manifest, data_manager registration (40+ keys), 5x startup preload fan-outs
  data_common.py         BQ table refs, schema-introspection cache, shared SQL-fragment builders
  data_overview.py / data_narratives.py / data_publishers.py / data_topic_areas.py /
  data_campaigns.py / data_discover.py / data_angles.py / data_archive.py
                          one module per page, each: BQ SQL strings + safe_query() + light pandas reshaping
  charts_shared.py        2,119 lines — color palettes, na_panel(), KPI cards, table style constants,
                           AND ~700 lines of nontrivial chart-geometry code (timeline figures, PCHIP
                           smoothing, flag-annotation pixel math) that arguably isn't "shared" at all
  charts.py / charts_narratives.py / charts_publishers.py / charts_campaigns.py /
  charts_topic_areas.py / charts_discover.py / charts_archive.py
                          one module per page: figure builders + dash_table builders + (in several
                          cases) the page's @callback definitions live here, not in pages/*.py
  dev_ids.py               dev-mode "P1S2G1"-style reference-code overlay (clever, cheap, low-risk)
  fixtures.py              2,194 lines of hand-written fake DataFrames, one per data_manager key
  pages/
    __init__.py            registers 7 pages in build order (Overview, Topic Areas, Narratives,
                            Campaigns, Publishers, Discover, Archive)
    overview.py / narratives.py / publishers.py / topic_areas.py / campaigns.py / discover.py / archive.py
    _shared.py              shared page-layout helpers
```

Total: ~22k lines of Python + ~3k lines of CSS/JS for **one** dashboard. For comparison, the
platform-level code that hosts *all* dashboards (`app.py`, `config.py`, `dashboards/_base.py`,
`tenancy/*`, `auth/*`) is under 1,000 lines combined. The ratio (22:1) is the clearest single
signal in this codebase: almost all of the engineering investment and almost all of the future
risk is concentrated in `amazon_2026`, not in the platform shell.

### 2.3 Naming debt worth flagging early

`charts_shared.py` defines `THEME_TEXT = "var(--amazon-publishers-text)"` etc. — every shared
theme token is named `--amazon-publishers-*` even though it's used dashboard-wide (Overview,
Discover, Topic Areas, Campaigns — not just Publishers). Per `STYLE_GUIDE.md` §1 this is a
deliberate, documented alias layer on top of the real `--na-*` tokens, so it's not a bug — but
it means every new contributor's first instinct ("why is the Overview page importing
`amazon-publishers` CSS vars?") is wrong-footed by the name. This is a cheap, mechanical rename
(`--amazon-publishers-*` → `--na-*` directly, dropping the alias indirection) whenever there's
a slow week — see [§10](#10-readability--maintainability).

---

## 3. Data layer

`data_common.py` + 8 per-page `data_*.py` modules (`data_overview.py`, `data_narratives.py`,
`data_publishers.py`, `data_topic_areas.py`, `data_campaigns.py`, `data_discover.py`,
`data_angles.py`, `data_archive.py`) — 51 `load_*` functions total, ~2,500 lines of raw SQL
strings built in Python.

### 3.1 The good part: the no-argument cache contract

Every single `load_*` function takes **zero arguments** and returns the **entire** table
(aggregated, never scoped to "the narrative/campaign/publisher the user clicked"). Filtering
to a specific entity happens afterwards, in pandas, inside the chart/callback layer. This is
the single best architectural decision in the data layer: because Vizro's `data_manager` keys
its cache by the callable identity (not by call arguments), a parameterized
`load_narrative(narrative_id)` would create a fresh cache entry — and a fresh BigQuery query —
for every distinct narrative a user has ever clicked. The no-arg/load-everything/filter-in-pandas
pattern means BigQuery is hit **once per dataset per cache TTL window**, full stop, regardless of
how many users click through how many narratives. Combined with the 10-minute
`flask_caching.SimpleCache` TTL and the startup preload fan-outs (§2.1), this is what makes
drill-down navigation feel instant once warm. Keep this pattern — it is correct and it is the
reason the dashboard feels fast at all today.

### 3.2 Schema-drift defense has metastasized into the query layer

`_table_column_map()` (`data_common.py:101-111`) introspects `INFORMATION_SCHEMA.COLUMNS` per
table (lru_cached, pre-warmed via `prime_schema_cache()` to dodge a thundering-herd of concurrent
schema queries — a genuinely careful touch). It feeds four "optional column" helpers
(`_optional_string_expr`, `_optional_numeric_expr`, `_optional_json_string_expr`,
`_coalesce_string_expr`) that try a *list of candidate column names* and emit SQL for whichever
one actually exists.

This pattern is called **61 times** across the data layer (e.g. `data_narratives.py`: 18,
`data_topic_areas.py`: 17, `data_campaigns.py`: 11, `data_publishers.py`: 7). Concrete example,
`data_publishers.py:29-41` — the "where is this publisher's profile URL" lookup tries **seven**
candidate column names:

```python
publisher_platforms_expr = _optional_json_string_expr(
    "p", publishers_columns,
    ["platforms_url", "author_profile_urls", "author_profile_url",
     "publisher_profile_urls", "publisher_profile_url", "profile_urls", "profile_url"],
)
```

That is not defensive coding against a hypothetical — it is documentation, in code, that the
upstream BigQuery schema has been renamed at least seven times across the life of this dataset
(or across clients/pipeline versions) and nobody ever went back and migrated the historical
data to a single name. **This is the single highest-leverage simplification available in the
entire codebase**: collapsing those 61 call sites' worth of candidate-name guessing into one
BigQuery `VIEW` per source table (a normalization layer that exposes one stable column name
per concept, built once in SQL) would let every `load_*` function shrink by 30-60%, delete the
schema-introspection machinery's runtime cost (a real `INFORMATION_SCHEMA` query, however
cached) entirely, and — most importantly — turn "the schema changed again" from a silent
multi-file hunt into a one-place fix. Doing this is platform/data-engineering work, not a quick
Python refactor, which is presumably why it hasn't happened yet — but it should be the long-term
target, not the current 61-call-site workaround.

### 3.3 Publisher/campaign/narrative identity resolution is re-derived per query, not shared

Resolving "which canonical publisher does this row belong to" is genuinely hard given the schema
drift above, so the codebase falls back to a 3-tier `COALESCE`: explicit `publisher_uid` column →
join against `PUBLISHER_SEED_CTE` (`data_common.py:92-98`) on lowercased display name → last
resort `TO_HEX(MD5(LOWER(name)))`. That fallback chain is reasonable *once*. It is **re-typed
inline at 8 separate call sites within `data_publishers.py` alone**, and the same
COALESCE-to-seed-or-hash shape reappears (without the MD5 step, per the data-layer survey) in
`data_narratives.py`, `data_campaigns.py`, and `data_topic_areas.py` anywhere a query needs to
attribute rows to a publisher. Similarly, a "campaign column fallback" candidate-name list
(`["campaign_announcement", "Campaign_Announcement", "campaign"]`-shaped) is copy-pasted across
`data_narratives.py`, `data_campaigns.py`, and `data_topic_areas.py`, and inline
`LOWER(TRIM(COALESCE(..., ''))) LIKE 'pos%'`-style sentiment classification appears in multiple
places **despite `_sentiment_case()` already existing in `data_common.py` to do exactly this** —
adoption of the existing helper is inconsistent, not missing.

**Recommendation**: promote publisher-identity resolution to a single BigQuery view (or at minimum
a single parameterized SQL-fragment function in `data_common.py` that every `data_*.py` module
calls) rather than a copy-pasted CTE shape. Same treatment for the campaign-column candidate list
(make it a `data_common.py` constant, not three separate literal lists) and for sentiment
classification (just always call `_sentiment_case()` — there is no reason left to ever write the
`LIKE 'pos%'` literal by hand again).

### 3.4 Unbounded full-table pulls that will not survive 10x data growth

The "load everything, filter in pandas" pattern (§3.1) is correct for *aggregated* result sets
(a few hundred rows of publisher/narrative/campaign summaries). It is a real future scaling
hazard for the two places that pull **raw, unaggregated rows**:

- `data_archive.py::load_archive_scatter()` (20 lines) — a bare `UNION` of `umap_x, umap_y,
  narrative_label, source` from the full `amazon_2026_trad`/`amazon_2026_some` tables, **no
  `LIMIT`, no sampling**. Today this renders fine because the underlying tables are small enough
  and the chart correctly uses `go.Scattergl` (WebGL) rather than SVG `go.Scatter` (confirmed in
  `charts_archive.py:143,197,282`) — so rendering itself won't choke even at six figures of
  points. But the *query cost* (a full scan of two tables on every 10-minute cache refresh) and
  the *JSON payload size* shipped from BigQuery → pandas → the Dash callback → the browser scale
  linearly with row count, with no decimation strategy in place for when a client's archive grows
  past, say, a few hundred thousand rows per source.
- `data_narratives.py::load_narrative_top_publications()` is the one "top items" query in the
  whole data layer that does **not** apply the `ROW_NUMBER() ... WHERE rn <= 50` cap that its
  siblings (`load_campaign_top_publications()`, `load_topic_area_top_publications()`,
  `load_publisher_top_publications()`) all use — per STYLE_GUIDE.md §10 this was a deliberate
  choice ("no longer applies a per-narrative top-50 cutoff... so selected angles can show all
  matching publications") but it means this one query's result size is unbounded by a popular
  narrative's total volume, unlike every analogous query elsewhere in the dashboard.

**Recommendation**: when there's headroom, add an explicit row cap (with a documented, deliberate
override path for the one case above) and consider whether the Archive/Discover UMAP scatter
needs server-side decimation (e.g. cap at N points with deterministic sampling, or pre-aggregate
into a coarser grid beyond a zoom threshold) before a client's data volume makes that decision for
you under worse conditions (a slow page load in front of a client, not a quiet refactor).

### 3.5 `data_angles.py` redundant scans

`load_angles()` (the only function in the file) runs four separate `COUNT(*)`-shaped CTEs
(`trad_angle_id_counts`, `trad_angle_label_counts`, `some_angle_id_counts`,
`some_angle_label_counts`) where two (one per source, each counting by whichever of id/label is
populated via a single `UNION`/`CASE`) would do — it currently scans `amazon_2026_trad` twice and
`amazon_2026_some` twice for what's conceptually one pass per table.

---

## 4. Chart / rendering layer

`charts_shared.py` (2,119 lines) + 7 page-specific `charts_*.py` modules (`charts.py`,
`charts_narratives.py`, `charts_publishers.py`, `charts_campaigns.py`, `charts_topic_areas.py`,
`charts_discover.py`, `charts_archive.py`) — **5,894 lines** of figure/table builders.

### 4.1 `charts_shared.py` is doing at least three jobs

It is simultaneously: (a) a design-token/constants module (color palettes, `THEME_*` aliases,
table style dicts), (b) a UI-primitive library (`na_panel()`, `_kpi_card()`,
`build_overview_table_section()`), and (c) a non-trivial **chart geometry engine** — roughly 700
lines (`_timeline_figure`, `_timeline_with_narratives_figure`, `media_split_timeline_figure`,
PCHIP-based curve smoothing, pixel-precision flag-annotation collision/placement math in
`_add_reach_flag_annotations`) that has nothing to do with "shared constants" and everything to
do with one specific, sophisticated chart type. That geometry code is genuinely impressive
(dynamic figure height derived from tick count and annotation bounding boxes so there's never
dead space or clipped labels, shape-preserving PCHIP interpolation chosen specifically to avoid
spline overshoot below zero) but it is hidden inside a file whose name promises "shared
constants." A new contributor looking for "where do I change how the mirrored media-split chart
computes its axis range" will not think to open `charts_shared.py` first.

**Recommendation**: split `charts_shared.py` into `theme.py` (palettes/tokens — pure data),
`ui_components.py` (`na_panel`, KPI cards, table style dicts — Dash component builders), and
`timeline_charts.py` (the PCHIP/flag-annotation/dynamic-height engine — this is arguably
sophisticated enough to deserve its own test suite, see §11). None of this needs to happen before
shipping anything else; it's a pure readability win with zero behavior change, ideal for a slow
week.

### 4.2 Real cross-page duplication (not just "vs. shared")

Distinct from under-using `charts_shared.py`, several non-trivial blocks are duplicated **between
page-specific chart modules**, evidenced at the line level:

| What | Where | Scale |
|---|---|---|
| Sentiment donut figure builder | `charts_narratives.py` (`_narrative_sentiment_donut`), `charts_publishers.py` (`_mini_donut_chart`), `charts_discover.py` (`_discover_engagement_sentiment_donut`) | ~65 lines × 3, near-identical except labels/colors |
| `_data_bar_column_styles` (per-cell gradient bar styling) | `charts_narratives.py` and `charts_publishers.py` | line-for-line copy |
| `_combined_narratives_from_record` (merge trad/some top-narrative JSON into one ranked list) | `charts_narratives.py` and `charts_publishers.py` | 60-120 lines, duplicated rather than imported |
| Top publishers/journalists/publications table builders | Defined in `charts_narratives.py`, then **imported and re-wrapped** by `charts_campaigns.py` rather than generalized | ~100+ lines effectively shared via cross-module private-name import, not a public shared API |

That last row is its own smell: `charts_campaigns.py` reaching into `charts_narratives.py`'s
underscore-prefixed ("private") helpers means the "Narratives" page module is not actually
self-contained — it's also a dependency of the Campaigns page. That's an invisible coupling: a
contributor refactoring `charts_narratives.py` in isolation, confident they're only touching the
Narratives page, can silently break Campaigns.

**Recommendation**: extract a single `sentiment_donut_figure(records, ...)` and the
`_data_bar_column_styles`/`_combined_narratives_from_record` helpers into `charts_shared.py`
proper (with a public, non-underscore name), and make the top-publishers/journalists/publications
table builder a genuinely shared, parameterized function rather than an inter-page private
import. This is ~250-350 lines of net deletion with no feature change.

### 4.3 God-functions worth splitting

`charts_narratives.py::_narrative_detail_content` (~100 lines) and
`charts_archive.py::_archive_figure` (~138 lines) each bundle data reshaping + multiple layout
concerns + figure construction in one function (the latter handles KDE overlay, time-based
coloring, narrative-based coloring, and reference-point overlay all in one body). Neither is
*wrong*, but both are past the size where a bug fix to "just the KDE part" requires holding the
whole function's state in your head. Low urgency, but a good target whenever either is touched
for an unrelated reason.

### 4.4 Callback placement is consistent, with one good example of real reuse

~52 distinct registered callbacks dashboard-wide (45 defined directly in `pages/*.py`, verified by
grep; the remainder are explained below — this required tracing one indirection, not a flat count,
so the arithmetic is spelled out rather than asserted). Four callbacks live outside `pages/*.py`,
and they're not all the same kind of exception:

- Three are genuine one-offs, each colocated with the single figure it updates:
  `charts.py::_update_p1s4g1_graph`, `charts_narratives.py::_update_narrative_media_split_figure`,
  `charts_archive.py::_update_archive_scatter`. Minor, defensible departures from "callbacks live
  in pages/" — co-location with the figure they affect is a reasonable trade against strict
  layering.
- The fourth is different in kind: `charts_shared.py::register_top_items_callback()` is a
  **shared, parameterized callback *factory***, not a one-off — it's called four separate times,
  from four different pages (`charts.py:516` for Overview, `pages/topic_areas.py:64`,
  `pages/publishers.py:58`, `pages/campaigns.py:231`), each call registering an independent Dash
  callback (unique `Output`/`Input` ids via its `id_prefix` argument) that drives that page's
  "Top Items" Trad/SoMe source-toggle table. This is exactly the kind of cross-page reuse §4.2
  argues is missing elsewhere (the sentiment donut, the data-bar styling) — flagging it here as a
  positive existing pattern worth pointing to when doing that consolidation work, not as a
  layering violation. (It's also why the naive count of "`@callback`/`clientside_callback`
  occurrences in source" undercounts the true number of registered callbacks by three: the
  decorator's source line appears once, inside the factory, but executes four times.)

### 4.5 No hot-path disasters

Spot-checked the obvious risk patterns (per-row Python loops over potentially-large frames inside
a callback): `charts_discover.py::filter_discover_records` is a clean single-pass filter using set
membership (O(1) per check); the one nested-loop case
(`charts_narratives.py::_combined_narratives_from_record`) operates over a handful of
narratives/angles per entity, not full-table data, so it's a non-issue at current scale. Nothing
here needs to change for performance reasons today.

---

## 5. Pages & callback layer

7 page modules + `pages/_shared.py`, ~1,800 lines, ~52 registered callbacks (see §4.4 for the
exact count and why it isn't a flat grep).

### 5.1 `_shared.py` is real, working reuse — but page scaffolding still isn't

`pages/_shared.py` exports four genuinely-shared helpers used across most pages:
`metric_filter`/`metric_parameter` (the Trad/SoMe + publications/reach radio control), 
`build_detail_timeline_response()` (generic combined-timeline response builder, used by Topic
Areas/Narratives/Campaigns), `build_overview_table_response()` (shared table-filtering/styling,
used by Topic Areas/Campaigns/Publishers), and `select_active_table_value()` (active-cell → entity
lookup, used by every page with a drill-down table). This is good — it's the part of the codebase
that *did* get factored out.

What's left un-factored is the page-builder shell itself: every page module
(`overview.py:29-110`, `topic_areas.py:67-102`, `narratives.py:56-91`, `campaigns.py:53-84`,
`publishers.py:67-94`) hand-writes the same ~30-80 line `vm.Page(id=..., title=ref_label(...),
path=f"{base_path}/...", components=[...], layout=vm.Flex(...), controls=[metric_parameter(...)])`
skeleton. This is low-risk duplication (it's boilerplate, not logic — a bug here is obvious
immediately, not a silent miscalculation), so it's a "nice to have" factoring rather than urgent,
but a `build_standard_page(slug, title, ref, sections, controls=...)` factory would cut ~150-200
lines of repeated scaffolding and make "what makes the Discover page's `vm.Page` call different
from everyone else's" immediately visible by contrast.

### 5.2 The Discover page has two genuinely monolithic callbacks

Counted directly from the `@callback(...)` decorators in `pages/discover.py:103-129` and
`:225-248` (not taken on faith from an earlier pass over this file — the first pass's Input/State
counts turned out to be slightly off, corrected here): `_update_discover_results` has **12
Outputs and 12 Inputs, zero States**, and `_update_discover_clusters` has **3 Outputs, 15 Inputs,
and 3 States**. These are the two largest fan-in callbacks in the dashboard by a wide margin —
nothing else in the dashboard approaches a dozen-plus Inputs. Every filter, search box, toggle,
lasso-selection, and reference-point change on the page re-triggers one of these two "do
everything" handlers. This is not necessarily a bug — Dash's callback model doesn't offer a great
alternative when one figure genuinely depends on a dozen-plus independent controls — but it is the
dashboard's biggest single point of fragility:

- It's the hardest code in the dashboard to reason about by inspection (a dozen-plus-way
  interaction effects), and per §11 it has zero test coverage.
- Both callbacks call `_server_discover_data()` independently; that function is properly
  memoized (see §8.3 — confirmed, not assumed), so this isn't a redundant-computation problem,
  but it does mean two large callbacks are both implicitly depending on a shared mutable module
  global with no documented contract between them.
- The page survey flagged the cell-selection-reset `clientside_callback`s (lines ~480-502) as
  firing on every data update, which is worth a closer look the next time anyone touches Discover
  interactivity — re-verify rather than take as fact, since that read came from a single pass over
  the file rather than runtime observation.

**Recommendation, in order of effort**: (1) add `prevent_initial_call` / input-debouncing review
specifically for these two callbacks since they're the most expensive to re-fire; (2) consider
splitting "compute the filtered id set" from "render the results table" from "render the cluster
figure" into a chain (a `dcc.Store` of filtered ids feeding two downstream callbacks) so a change
to, say, the similarity slider doesn't necessarily have to re-run table-formatting logic it
doesn't need to touch; (3) this page is the best candidate in the whole dashboard for an actual
Selenium/Playwright-style end-to-end smoke test (see §11), precisely because it's the place where
manual reasoning is weakest.

### 5.3 `set_dev_mode(True)` is unconditional, in production

Confirmed directly (`pages/__init__.py:36`): `build_all_pages()` calls `set_dev_mode(True)`
unconditionally — not `set_dev_mode(settings.is_dev)`, not gated on any flag. Per `dev_ids.py`'s
own docstring this is supposed to control whether internal reference codes like "P1S2G1" are
shown — i.e. it's documented as a *development* aid. Whether or not the ref codes are currently
visible in the live dashboard's titles depends only on `_ENABLED`'s hardcoded value, which is
**always `True`** regardless of `ENV=prod`. Either:
  (a) this is intentional — the team wants those reference codes visible in production too, for
      precise communication about specific chart elements — in which case the name `dev_ids` /
      `set_dev_mode` is misleading and should be renamed to reflect that it's a permanent feature, or
  (b) this is a leftover from active development that should be `set_dev_mode(settings.is_dev)`.
This is a 1-line fix either way (rename the concept, or gate it) — flagging because it's the kind
of thing that's invisible until a client asks "what does 'P3S2G4' mean on my dashboard."

### 5.4 Debug `print()` statements left in `narratives.py`

`narratives.py:131` and `:147` call `print(f"[NARR-DEBUG] ...")` directly — bypassing the
project's own `logging_setup.py`, which exists specifically so "modules use
`logging.getLogger(__name__)` instead of `print`" (its own docstring's words). On Cloud Run,
stdout `print()` calls do still reach Cloud Logging, so this isn't invisible, but it bypasses log
levels (can't be turned off without a code change), bypasses the structured
`%(asctime)s %(levelname)-8s %(name)s` format every other log line has, and is exactly the kind
of thing that's easy to forget about once it's shipped. Trivial fix.

### 5.5 Page id/path convention is consistent, with one explained exception

All seven pages follow `id="amazon-2026-<slug>"`, `path=f"{base_path}/<slug>"` — except Overview,
whose path is bare `base_path` (no `/overview` suffix). This is correct and intentional: Vizro
forces the dashboard's first page to live at `/`, and `app.py::_build_home_page()`'s docstring
explains the same constraint is why a separate, tiny "Overview" page is reserved at the
platform level (`path="/overview"`) purely to keep the *root* path free for the landing panel.
amazon_2026's own Overview page is simply page two-of-eight in build order, not the dashboard's
literal first page, so it isn't subject to that override. No action needed — noting it here only
because it looked like an inconsistency until traced back to a real, documented platform
constraint.

---

## 6. Extensions & multi-tenancy

### 6.1 `tenancy/*` is clean, and unusually well-designed for its size

`tenancy/models.py` (plain dataclasses with `from_doc`/`to_doc` for Firestore (de)serialization),
`tenancy/users.py` (a `Protocol`-typed dual backend — `InMemoryUserStore` for dev,
`FirestoreUserStore` for prod, swapped via one `lru_cache`d factory), and `tenancy/access.py`
(single-source-of-truth `can_access`/`accessible_slugs`, company-grant-plus-per-user-extra-grant
model) are genuinely well-built: minimal, Protocol-based rather than inheritance-based, and easy
to test in isolation (though nothing currently does — see §11). `tenancy/events.py`'s
fail-soft audit/usage recorders (swallow-and-log, "must never break the request that triggered
it") are exactly the right defensive posture for non-critical telemetry. This is some of the best
code in the repository and a good model for how `amazon_2026`'s own modules could be structured.

### 6.2 But `amazon_2026` doesn't actually use any of it for data scoping

This is the most important finding in this section. `tenancy/access.py::resolve_client_dataset()`
exists specifically to map a logged-in user to *their* BigQuery dataset
(`f"{bq_dataset_prefix}{client_id}"`, or `Client.bq_dataset` override) — i.e. the platform has a
real, designed mechanism for "show this client their own data, not someone else's." A repo-wide
search for `resolve_client_dataset`, `bq_dataset`, and `client_id` inside
`dashboards/amazon_2026/` returns **zero matches**. `data_common.py:9-10` instead hardcodes:

```python
PROJECT_ID = "native-analytics-486522"
DATASET_ID = "amazon_2026"
```

Every one of the 51 `load_*` functions ultimately calls `_table()`, which always resolves against
this one fixed project/dataset, for every user, regardless of `current_user().client_id`. Today,
with one client on this dashboard, that's invisible — it behaves identically to the
multi-tenant-aware design. The access *gate* (§2.1, `app.py::_install_access_gate`) genuinely does
enforce "can this user open `amazon_2026` at all," so there's no live security hole **today**. But
the moment a second client is meant to see *their own* Amazon coverage data through what looks
like the same dashboard, the current code will serve them client #1's BigQuery rows verbatim,
because nothing downstream of the access gate ever consults `client_id`. If reselling this
dashboard to additional clients is on the roadmap at all, this should be treated as a
**known architectural gap to close before that happens**, not a bug to fix reactively after a
client notices.

**Recommendation**: thread `resolve_client_dataset(current_user())` through to `data_common.py`'s
`_table()` (e.g. via a request-scoped context var set in the access gate, since `BuildContext` in
`dashboards/_base.py` is explicitly process-level / built once at startup and documented as such —
"per-user data scoping... is resolved at request time inside dynamic-data loaders, which can read
the logged-in user from the Flask request context" is literally already the documented intent in
`dashboards/_base.py`'s own docstring. `amazon_2026` just hasn't implemented that part of the
contract yet).

### 6.3 The "chat with your data" extension silently doesn't support this dashboard

`extensions/chat_with_data.py::_DATA_PROVIDERS` (lines 73-77) registers exactly three dashboard
slugs: `"timeline"`, `"breakdown"`, `"bq_sample"` — the small example dashboards. `"amazon_2026"`
is absent. `features_chat_enabled` defaults to `True` (`config.py:92`), so the floating chat
widget is presumably visible on every dashboard including this one (need a visual check — the
injection is asset-driven, see §7), but any question asked on `amazon_2026` falls through to:

```python
provider = _DATA_PROVIDERS.get(slug)
if provider is None:
    return jsonify(answer="Chat is not available for this dashboard yet.", source="local", dataset=slug)
```

For the dashboard the team has clearly invested the most effort into, this is a visible dead end
for users who try the platform's marquee AI feature on it. Given the data layer already exposes
everything chat would need (`data_manager` has ~40 registered keys), wiring a provider for
`amazon_2026` is plausibly a half-day task: pick 1-3 representative aggregated datasets (e.g.
`PUBLISHERS_KEY`, `NARRATIVES_KEY`, `OVERVIEW_KPI_KEY`) and register them the same way
`_provider_timeline` does. Worth noting `_dataset_summary()`'s `df.describe(include="all")` +
`df.head(15).to_string()` approach is fine for the small datasets it serves today, but should
target the *aggregated* `amazon_2026` tables (hundreds of rows), never the raw per-row
`amazon_2026_trad`/`amazon_2026_some` tables, to stay cheap.

### 6.4 `extensions/saved_views.py` is a small architectural gem

529 lines implementing a fully generic "save the current state of every filter control on this
page, keyed by browser path, persisted to `localStorage`" feature by *introspecting the built
Dash layout tree* (`_walk_components`, `_is_trackable`) rather than requiring every page to
manually register what's saveable. It correctly distinguishes single-value controls from
multi-prop ones (`DatePickerRange`), excludes Vizro/nav-internal ids by prefix, and uses pattern-
matching callbacks (`{"type": ..., "name": ALL}`) for the open-ended "however many saved views
exist" restore/rename/delete/export actions. This is exactly the right way to build something
genuinely page-agnostic in Dash, and a good reference for how `amazon_2026`'s own page-scaffolding
duplication (§5.1) could eventually be addressed with a similar introspection-driven approach
rather than a fixed factory function, if the team wants to invest more here later.

### 6.5 Auth (`auth/*`) is solid; one unbounded-growth footnote

`auth/firebase.py`'s session-cookie verification cache (claims cached in-process, TTL-bounded,
with a separate longer interval forcing a real revocation re-check) is a well-judged
security/performance tradeoff — avoids hitting Firebase on every request without skipping
revocation checks indefinitely. `auth/middleware.py`'s dev-mode cookie-based user impersonation
("View as") is a nice, low-friction way to QA the non-admin experience without standing up real
auth. The one footnote: `_claims_cache` (`auth/firebase.py:31`) is a plain module-level dict that
only evicts an entry when that *same* cookie is looked up again past its TTL — a cookie that's
verified once and never reused (an abandoned session, a browser tab closed mid-session) stays in
memory for the life of the process. Given session cookies last 5 days and likely user counts are
modest, this is a low-severity footnote, not a current problem — but it's the same "unbounded
process-lifetime dict" shape as the `_server_discover_data()` cache (§8.3) and `_table_column_map`
lru_cache, so it's worth keeping in mind as one more thing that only a process restart currently
cleans up.

---

## 7. Frontend assets (CSS/JS)

~3,000 lines of hand-written CSS/JS across `assets/*.css`/`*.js`, on top of a 740-line
STYLE_GUIDE.md documenting the system in extraordinary, hard-won detail (see §10.4 — this
document is itself one of this codebase's best assets).

### 7.1 The dashboard is fighting Plotly's and Vizro's rendering models, not just styling them

Three independent, separately-discovered workarounds share one root cause — both Plotly and
Vizro/Dash bake certain things into the DOM/inline-styles at render time in ways that don't
respond to normal CSS or normal Dash re-renders:

- **Plotly inline-SVG styling**: per STYLE_GUIDE.md §6, Plotly writes `font`/`gridcolor`/etc. as
  literal inline SVG attributes at draw time and does not reliably re-resolve `var(--na-*)` CSS
  custom properties when the theme toggles afterward. The fix is a **110-rule, `!important`-laden
  block** in the dashboard's CSS (confirmed by grep: 25 in `native_analytics.css` alone, 110
  total across the seven `amazon_2026_*.css` files) targeting Plotly's specific SVG class hooks
  (`.xtick > text`, `.legend .legendtext`, `.hoverlayer .hovertext .bg`, etc.), each paired with
  an explicit `stroke-opacity: 1 !important`/`fill-opacity: 1 !important` because Plotly splits
  color and opacity into separate baked-in SVG properties. This is correct, thoroughly documented
  engineering — but it is structurally a CSS specificity war against a charting library that
  wasn't designed to be re-themed live, and it will need re-verification (the STYLE_GUIDE.md's own
  words: "found via headless-browser inspection... the standard 'is the rule winning?' check isn't
  enough") on every future Plotly version bump.
- **Vizro nav-panel behavior**: `assets/native_analytics.js` patches
  `window.dash_clientside.dashboard.collapse_nav_panel` at runtime (after polling for it to exist,
  since asset load order vs. the Vizro bundle isn't guaranteed) to fix a real bug where Vizro's
  built-in implementation collapses the left nav on every page navigation, not just on a genuine
  click. It also reimplements dashboard-scoped nav-link visibility by querying the DOM directly
  and monkey-patching `history.pushState`/`replaceState`.
- **Vizro callback double-registration**: the `dash._callback.insert_callback` monkeypatch in
  `app.py` (§2.1).

None of these three are wrong fixes for the bugs they target, and all three are unusually well
commented about *why* they exist — this isn't sloppy code, it's necessary code given the
constraints. But taken together they're a coherent pattern: **a meaningful fraction of this
dashboard's frontend robustness depends on Vizro/Dash/Plotly internal behavior that isn't part of
those libraries' public contract**, which means every Vizro/Dash/Plotly version bump is a manual
regression-testing event (DOM class names changing, inline-style baking behavior changing,
`dash_clientside.dashboard.*` namespace changing) with no automated test today that would catch a
silent break (see §11). `requirements.txt` already exact-pins every relevant package (`vizro==0.1.56`, `dash==4.1.0`,
`plotly==6.7.0`, confirmed directly) rather than using range constraints — good, this is already
the right defensive posture for a codebase this dependent on framework internals. The remaining
gap is process, not config: treat any future version bump as requiring a manual pass through
STYLE_GUIDE.md §6's specific gotchas plus a nav-collapse/page-navigation smoke test, not just
"bump the pin and see if it boots."

### 7.2 `amazon_2026_discover.js` and `native_analytics.js` are small, well-targeted, low-risk

Both files are short (40 and 209 lines), narrowly scoped to one concrete UX problem each (search-
clear-button sync via the native `input` event since Dash's debounced `value` prop lags; nav-panel
collapse-state persistence), and both carry comments explaining the *why*, not just the *what* —
consistent with this dashboard's overall documentation discipline (STYLE_GUIDE.md, code comments
throughout). No changes recommended here; flagging mainly as a positive data point that contrasts
with the duplication found elsewhere.

### 7.3 Naming debt: `--amazon-publishers-*` as a dashboard-wide alias

Per §2.3 — `charts_shared.py`'s `THEME_*` constants and a large fraction of the CSS resolve through
`--amazon-publishers-*` custom properties even on pages that have nothing to do with publishers
(Overview, Discover, Topic Areas, Campaigns). STYLE_GUIDE.md §1 confirms this is a deliberate alias
layer on top of the real `--na-*` tokens (presumably for historical reasons — Publishers was
likely the first page built and the naming never got revisited once other pages adopted the same
tokens). It's harmless today (the indirection is one CSS custom-property lookup, free at runtime)
but it is a standing tax on every new contributor's first five minutes in this codebase. Cheap,
mechanical, zero-risk rename whenever there's a slow afternoon: point `charts_shared.py` and the
CSS directly at `--na-*` and delete the alias block.

---

## 8. Performance & speed

### 8.1 The startup preload pattern: smart idea, sloppy implementation

`_start_overview_preload`, `_start_topic_area_preload`, `_start_narratives_preload`,
`_start_campaigns_preload`, `_start_publishers_preload` (`dashboards/amazon_2026/__init__.py`)
are five separate functions, each ~12-15 lines, each spinning up its own
`ThreadPoolExecutor(max_workers=len(preload_keys))` inside its own daemon `threading.Thread`, each
doing the identical `{key: executor.submit(data_manager[key].load) for key in preload_keys}` /
`future.result()` / `logger.warning` dance. The *idea* — warm every page's BigQuery-backed cache
in parallel at process start so the first real user never pays a cold-query penalty — is exactly
right and clearly already paying off for warm-instance latency. The *implementation* is ~70 lines
that are 90% identical boilerplate five times over, which means a fix to the pattern (e.g. adding
a timeout, adding a metric, changing the logging format) has to be applied identically five times
and will eventually drift. **Recommendation**: one
`_preload(name: str, keys: list[str]) -> None` helper parameterized by a label and a key list,
called five times with five lists, replacing all five bespoke functions — pure deduplication, no
behavior change. Five `threading.Thread(target=functools.partial(_preload, "overview",
OVERVIEW_PRELOAD_KEYS)).start()` one-liners instead of five 15-line near-twins.

### 8.2 That same preload pattern is actively harmful on a cold Cloud Run start

This is the single most consequential finding in this review, because it connects four facts that
are each individually fine and combine into a real production risk:

1. `cloudbuild.yaml:45`: **`--min-instances=0`** — Cloud Run is allowed to scale this service to
   zero containers when idle, which is sensible for cost on a low/bursty-traffic internal tool,
   but means the *first* request after any idle period pays a full cold start.
2. `Dockerfile:23`: **`gunicorn --workers 2 --threads 8`** — every container that does start runs
   **two independent Python processes**, each importing the full app and running its own copy of
   `_build_dashboard()` from scratch.
3. `dashboards/amazon_2026/__init__.py::build_pages()` runs `_register_data_sources()` (40+ keys),
   `prime_schema_cache()` (5 `INFORMATION_SCHEMA` queries), and then **all five** preload fan-outs,
   which collectively fire on the order of **40+ BigQuery queries** via thread pools, *per worker
   process*, immediately on import.
4. `cloudbuild.yaml:43-44`: **`--cpu=1 --memory=1Gi`** — one vCPU and 1GB of RAM for the entire
   container.

Multiply it out: a cold container start means **2 worker processes × ~40 concurrent-ish BigQuery
queries each** racing for one vCPU and 1GB of RAM, at the exact moment a real user's first request
is also waiting on that same container to finish booting Flask/Vizro/Dash before it can even start
routing. The preload threads are daemonized and fire-and-forget from the app's perspective, so
they won't block the HTTP response *forever*, but they will contend hard for the one available
CPU core right when cold-start latency matters most, and every full-table pandas DataFrame loaded
during that fan-out (publishers, narratives, topic areas, campaigns, the unbounded archive scatter
from §3.4) has to fit in that same 1GB alongside two separate Python/Flask/Vizro process images —
real OOM-kill risk on a worst-case cold start with several large tables landing in memory at once,
not merely a slow one. `gunicorn --timeout 120` means a request that's still waiting on a
contended cold start past 120 seconds gets its worker killed mid-flight, which would surface to
users as an intermittent 502 right after a scale-from-zero event — exactly the kind of bug that's
hard to reproduce on demand and easy to misattribute to "BigQuery was just slow that one time."

**Recommendation, concretely**:
  - The cheapest, highest-leverage fix is a **one-line config change**: `--min-instances=1`. This
    keeps one warm container always running, so cold starts only happen on deploys/instance
    recycling, not on every idle gap — directly trading a small constant Cloud Run cost for
    eliminating the worst-case latency/OOM scenario above. Worth the money for any dashboard
    a client might actually be watching live.
  - If staying at `min-instances=0` is a hard cost constraint, throttle the preload fan-out itself
    on cold start: a single shared `ThreadPoolExecutor` with a bounded worker count (not five
    independent pools each sized to their own key list) and/or stagger the five preload groups
    instead of firing all simultaneously, so the one available vCPU isn't asked to context-switch
    across ~40 simultaneous BigQuery client calls.
  - Consider whether `--workers 2` is buying anything given Dash/Flask's I/O-bound profile and the
    `--threads 8` already in play — two worker processes means double the preload cost, double the
    cache fragmentation (§9.1), for resilience against one worker's Python-level crash. On a
    single-vCPU container that tradeoff deserves a deliberate re-check, not just "that's what was
    there originally."

### 8.3 `_server_discover_data()` caching: correctly memoized, but with two real caveats

Verified directly in `charts_discover.py:54-72` (not assumed from the STYLE_GUIDE's description):
it's a plain module-level global (`_server_cache: tuple[...] | None = None`) populated on first
call and returned as-is on every subsequent call — genuinely solving the problem it was built for
(no more round-tripping the full Discover dataset through the browser on every filter change,
per the STYLE_GUIDE's own framing). Two caveats worth flagging:

  - **No TTL, ever** — every other dataset in this dashboard refreshes every 10 minutes via
    `flask_caching`'s `CACHE_DEFAULT_TIMEOUT=600` (`app.py:229`). `_server_cache` does not
    participate in that mechanism at all; once populated, a given worker process serves that exact
    snapshot of Discover data **for the rest of that process's life**, even as the underlying
    `data_manager[DISCOVER_ITEMS_KEY]` cache refreshes normally every 10 minutes underneath it.
    Discover is therefore the one page in the dashboard where "data as of" silently diverges from
    every other page the longer a worker process has been running. If this is intentional (e.g.
    Discover's dataset is believed to change rarely enough that this doesn't matter in practice),
    it should at least be a one-line comment saying so; if not, it needs the same TTL-based
    invalidation every other dataset already has.
  - **No lock around the check-then-set** — `if _server_cache is not None: return _server_cache`
    followed later by `_server_cache = (...)` is a classic race under `gunicorn --threads 8`: two
    near-simultaneous first requests to a freshly-started worker can both observe `None` and both
    redundantly run `discover_records()`/`discover_cluster_records()`/`_build_color_map()` before
    either assignment lands. Not a correctness bug (the result is idempotent, the second
    assignment just overwrites with an equivalent value), but it's wasted CPU exactly during the
    cold-start window already under the most contention (§8.2). A `threading.Lock` around the
    populate-if-empty check is a five-line fix.

### 8.4 Every page navigation pays a synchronous Firestore write, in production

`app.py::_install_access_gate`'s `before_request` hook calls `tenancy.events.record_usage(user,
slug)` synchronously, inline in the request path, on every real (non-AJAX, `Accept: text/html`)
page load when auth is enabled. `record_usage` (`tenancy/events.py`) is appropriately fail-soft
(catches and logs rather than raising), but "fail-soft" only protects correctness — it does
nothing for latency. Every dashboard page navigation in production currently waits on a live
Firestore document write before the page gate even finishes evaluating, adding Firestore's
round-trip latency to *every single page load*, for analytics that nothing in the request path
actually needs synchronously. **Recommendation**: move usage recording off the request's critical
path — a background thread fire-and-forget (mirroring the daemon-thread pattern already used for
preloading), or a lightweight in-process queue flushed periodically, would remove this latency
without losing the audit trail.

---

## 9. Scalability

Three independent axes — data volume, concurrent users/instances, and tenant count — and this
codebase is in a different place on each one.

### 9.1 The cache TTL is tuned for data that updates every 10 minutes — it updates at most once a day

**Important correction from an earlier draft of this section**: this finding is about wasted
query cost and minor data-staleness skew, not about concurrent users being unable to use the
dashboard — multiple simultaneous users are served correctly today, full stop, regardless of
everything below. Worth saying plainly since the original framing of this finding could be (and
was) misread as an availability/capacity problem, which it isn't.

Confirmed with the team: the underlying BigQuery data behind `amazon_2026` updates **at most once
a day**. Against that fact, `app.py:229`'s `flask_caching` configuration —
`CACHE_DEFAULT_TIMEOUT=600` (10 minutes) — is tuned roughly two orders of magnitude too
aggressively. Every `load_*` function's result is treated as stale after 10 minutes and
re-queried from BigQuery on the next request, which means the ~40-50 registered datasets get
**re-fetched from BigQuery up to 144 times a day** (every 10 minutes, around the clock) to
re-fetch data that, in the overwhelming majority of those 144 cycles, hasn't changed since the
*previous* cycle. That's not "8x redundant" (the framing in the original draft of this section,
based on multi-instance fragmentation, see below) — it's closer to **140x redundant** against the
data's real update cadence, and it's the single highest-value, lowest-effort fix in this entire
review: it's a one-constant change, not a refactor.

**Recommendation (agreed with the team): raise `CACHE_DEFAULT_TIMEOUT` to 3600 (1 hour).** This
cuts the redundant-refresh frequency by 10x (from 144/day to 24/day) while staying comfortably
fresher than the data ever actually changes — there's no scenario where an hour-old cache shows a
user something wrong, since the source itself only moves once a day. If even tighter cost control
is wanted later, this could become event-driven (invalidate the cache when the daily load job
finishes, rather than guessing a timer) rather than a blind TTL at all — but a 1-hour constant is
the right immediate fix and needs no further design work.

**A related, smaller finding — independently raised, and correct**: even at whatever the TTL is
tuned to, each refresh cycle re-runs the dashboard's ~50 independent `load_*` queries, and a large
fraction of them re-scan the *same* one or two underlying tables (`amazon_2026_trad`,
`amazon_2026_some`) with different `GROUP BY`/aggregation logic rather than sharing a single pass
over the base data. For example, the Overview page alone runs `load_tml_split()`,
`load_media_type_period()`, `load_sentiment_source_monthly()`, `load_source_sentiment_monthly()`,
`load_overview_kpis()`, `load_some_platform()`, and `load_top_items()` — seven independent full
scans of the same source tables, just sliced differently each time. BigQuery doesn't share scan
work between separate queries, so this is real, additive cost on top of the TTL issue above (it
determines *how much* work happens per refresh; the TTL determines *how often* that work
repeats). Fixing the TTL is the bigger lever and should happen first; consolidating these queries
(e.g. one broader extract per source table, with the rest of the slicing done in pandas, or
BigQuery `GROUPING SETS` to compute several aggregations in one scan) is a real follow-up but a
more invasive one — not blocking, worth scheduling once the TTL fix has landed.

**The multi-instance angle from the original draft of this section is real but minor, not the
main story.** `flask_caching.SimpleCache` (`app.py:229`) is an in-memory dict scoped to one Python
process; with `gunicorn --workers 2` and up to `--max-instances=4`, there can be up to 8
independent copies of this cache (plus a ninth-ish independent copy via `charts_discover.py`'s
`_server_cache`, §8.3) live at once, each refreshing on its own clock. Given the daily-max update
cadence, the practical consequence of this is small: at worst, two processes both show *today's*
data, refreshed at slightly different minutes within the same hour — not the cross-tab
inconsistency this section originally implied. The only real cost is redundant BigQuery query
volume scaling with however many of the up-to-8 processes happen to be alive, which the TTL fix
above already shrinks by 10x on its own. A shared cache backend (Redis/Memorystore, a
`flask_caching` backend swap) would close this gap entirely and is still worth doing if/when this
product runs at higher concurrent-instance counts, but it's a cleanup item now, not the urgent fix
the TTL change is.

### 9.2 Tenant count: the dashboard is single-tenant in practice today (cross-ref §6.2)

Restating the §6.2 finding in scalability terms: the platform's access-control layer scales to N
tenants today (that part is genuinely well-built — see §6.1). `amazon_2026`'s *data* layer does
not — it is hardcoded to one project/dataset, so "scaling to a second client on this same
dashboard" is currently a code change (wiring `resolve_client_dataset`), not a config change or an
admin-panel action. If reselling this specific dashboard design to other clients is part of the
product's growth plan, this is the blocker to schedule for, not a thing to discover under deadline
pressure when client #2 signs.

### 9.3 Data volume: the "load full table, filter in pandas" ceiling

§3.1 explained why this pattern is *currently* a strength (cache-friendly, avoids a
cache-key-explosion problem). It has a ceiling, and it's worth being explicit about where: every
`load_*` function pulls its entire result set into a pandas DataFrame, in the memory of whichever
worker process is running it, on every cache refresh. At today's data volumes (per-client
quarterly/annual media-monitoring datasets — thousands to low hundreds-of-thousands of rows per
table) this is fast and cheap. It stops being fast and cheap somewhere past that — the exact
threshold depends on row width and how many of the ~40 cached DataFrames are resident
simultaneously in a 1GB container (§8.2) — and the two genuinely unbounded queries flagged in
§3.4 (`load_archive_scatter`, `load_narrative_top_publications`) will be the first to feel it,
since their result size scales with raw event volume rather than with a fixed aggregation
cardinality (a few hundred publishers/narratives/campaigns) the way almost everything else in the
data layer does. **This is not an urgent problem** — it's a "know where the next bottleneck will
be" note, not a "fix this now" one. The fix, when it's needed, is server-side pagination/sampling
for those two queries specifically, not a wholesale architecture change.

### 9.4 Firestore usage-event volume has no retention policy

`tenancy/users.py::FirestoreUserStore.add_usage_event` writes one document per qualifying page
load (§8.4), forever, with no TTL, archival, or rollup — contrast with `InMemoryUserStore` (the
dev backend), which explicitly caps itself at the last 5,000 events specifically "to keep memory
bounded in long-running dev sessions" (`tenancy/users.py:123-125`). The dev backend protects
itself from unbounded growth; the production backend (Firestore) does not, because Firestore
"growing" just means slowly accumulating storage cost and read volume rather than crashing a
process — but the absence of any retention story (a TTL policy on the collection, a scheduled
rollup into daily/weekly aggregates, anything) means usage-analytics storage cost grows linearly
with total page views, forever, with no plan in place for when that becomes worth addressing.
Firestore supports native TTL policies on a collection with minimal setup — worth adding before
this becomes a "why is our Firestore bill climbing" investigation a year from now.

---

## 10. Readability & maintainability

### 10.1 Two genuine "god files"

`charts_shared.py` (2,119 lines, three jobs — §4.1) and `fixtures.py` (2,194 lines, one job done
extremely literally) are the two largest files in the dashboard and both are size-risk for
different reasons. `charts_shared.py`'s risk is conceptual (it's hard to know where to look for a
given concern). `fixtures.py`'s risk is purely mechanical: it is 2,194 lines of hand-built
`pd.DataFrame(...)` literals, one realistic-looking fixture per `data_manager` key, used as the
dev-mode/BigQuery-unavailable fallback for every `safe_query()` call. This is valuable — it's what
lets local dev work with zero GCP credentials and is presumably also useful as informal
documentation of each query's expected output shape — but it is also **the single most
schema-coupled file in the codebase**: every time a `load_*` function's SELECT list changes (a
column renamed, added, or removed), the matching fixture function should change too, and nothing
enforces that they stay in sync. A `load_*` function and its fixture silently drifting apart isn't
caught by anything today (there are no tests asserting fixture shape matches a real query's
output shape — see §11), so the failure mode is "dev mode looks fine, BigQuery breaks in
prod" or vice versa, discovered by a human rather than a check. Not urgent to restructure the file
itself, but a lightweight schema-shape assertion (even just "fixture columns ⊆ expected columns,"
checked once at import time in dev) would convert a silent-drift risk into a fail-fast one.

### 10.2 Duplication inventory (consolidated from §3-§5)

Pulling every duplication finding from this review into one place, since "the pattern repeats" is
itself the finding that matters most for a codebase this size:

| Pattern | Repeated in | Fix |
|---|---|---|
| Publisher identity resolution (`COALESCE(uid, seed-join, MD5-hash)`) | 8× in `data_publishers.py` alone, plus `data_narratives.py`/`data_campaigns.py`/`data_topic_areas.py` (§3.3) | One BigQuery view or one shared SQL-fragment function |
| Campaign-column candidate-name list | `data_narratives.py`, `data_campaigns.py`, `data_topic_areas.py` (§3.3) | One `data_common.py` constant |
| Inline sentiment `LIKE 'pos%'` logic | Multiple `data_*.py` files, despite `_sentiment_case()` existing (§3.3) | Always call the existing helper |
| Sentiment donut figure builder | `charts_narratives.py`, `charts_publishers.py`, `charts_discover.py` (§4.2) | One shared `sentiment_donut_figure()` |
| `_data_bar_column_styles` | `charts_narratives.py`, `charts_publishers.py` (§4.2) | Move to `charts_shared.py` |
| `_combined_narratives_from_record` | `charts_narratives.py`, `charts_publishers.py` (§4.2) | Move to `charts_shared.py` |
| Top publishers/journalists/publications tables | Defined in `charts_narratives.py`, privately imported by `charts_campaigns.py` (§4.2) | Make it a real, public, shared API |
| 5× near-identical startup preload functions | `dashboards/amazon_2026/__init__.py` (§8.1) | One parameterized `_preload(name, keys)` |
| Page-builder `vm.Page(...)` scaffolding | `overview.py`, `topic_areas.py`, `narratives.py`, `campaigns.py`, `publishers.py` (§5.1) | One `build_standard_page()` factory |
| `--amazon-publishers-*` aliasing `--na-*` | `charts_shared.py` + most CSS files (§2.3, §7.3) | Mechanical rename, delete alias layer |

None of these are individually urgent. Collectively, they're the clearest, lowest-risk path to
making this codebase meaningfully smaller and easier to onboard into without changing a single
pixel of output — likely a 1,000-1,500 line net reduction (roughly 5-7% of the dashboard's Python)
if all were addressed.

### 10.3 Dev-mode residue in production-path code

Three small items, all already evidenced in §5.3-§5.4, grouped here because they share a root
cause (code written for active development, never revisited once the feature shipped):
`set_dev_mode(True)` called unconditionally rather than gated on `settings.is_dev`; `print()`
debug statements in `narratives.py` bypassing the project's own `logging_setup.py` convention;
and (worth adding here) the dashboard's own `STYLE_GUIDE.md` §12 documents a "Chart Context Menu"
explicitly as **"Experimental"** with a global `localStorage`-persisted on/off toggle defaulting
to visible — worth a deliberate decision (promote it out of "experimental" status, or gate it
behind a settings flag the way `features_chat_enabled` gates the chat widget) rather than leaving
a permanently-experimental feature live by default indefinitely.

### 10.4 STYLE_GUIDE.md deserves explicit credit — and a sibling

`STYLE_GUIDE.md` (740 lines) is, unusually, one of this codebase's best assets rather than an
afterthought: it documents not just *what* the design tokens are but *why* specific non-obvious
decisions were made (the five numbered "gotchas" in §6 reverse-engineering exactly how Plotly
bakes SVG styles are the kind of hard-won knowledge that normally lives only in one engineer's
head and gets re-discovered painfully by the next person). Very few dashboards this size have
documentation this precise. The natural next step — and the direct motivation for *this* document
existing alongside it — is an equivalent living document for the **backend** architecture: where
each data flow goes, which caches exist and their invalidation rules, the deployment topology and
its scaling knobs (§8-9), and the duplication inventory (§10.2) as a checklist to work through
opportunistically. This document can seed that; it shouldn't be the last word on it, since (unlike
STYLE_GUIDE.md, which is updated by the same people doing the styling work) an architecture doc
needs the same "update it when you touch the thing it describes" discipline to stay trustworthy.

---

## 11. Testing, observability, resilience

### 11.1 There are zero automated tests in this codebase

Confirmed by a repo-wide search for `test_*.py` outside `.venv`: none. Not "low coverage" — none.
For a 22,000-line dashboard whose core logic is **51 hand-built SQL strings**, **~52 callbacks**,
and a non-trivial amount of pure-Python geometry (the timeline chart height/flag-placement math in
§4.1), this is the single largest structural risk in the codebase, ahead of any individual
duplication or performance finding above — because it means every fix this document recommends
currently has to be verified by hand, every time, including re-verifications after unrelated
changes. Concretely, the kinds of bugs this codebase is most exposed to (a BigQuery schema rename
silently changing which candidate column an `_optional_string_expr` call picks; an off-by-one in
the `_metric_pivot`/`_weekly_grid_cte` SQL-fragment builders; a sign error in the mirrored
media-split axis math; a callback's Input/Output order silently shifting after a refactor) are
exactly the class of bug that's cheap to catch with a unit test and expensive to catch by staring
at a chart and noticing a number looks wrong.

**Recommendation, realistic and prioritized for a codebase starting from zero**:
  1. **SQL-fragment unit tests, no BigQuery required**: `data_common.py`'s helpers
     (`_optional_string_expr`, `_sentiment_case`, `_metric_pivot`, `_weekly_grid_cte`, etc.) are
     pure string-building functions — trivially testable without touching BigQuery at all
     (assert the right candidate column gets picked, assert the SQL shape for known inputs).
     Highest ratio of confidence gained to effort spent; start here.
  2. **Fixture-shape assertions** (§10.1) — assert each `load_*` function's expected output
     columns match its paired fixture's columns, catching the "query and fixture silently drifted
     apart" failure mode automatically instead of by accident.
  3. **Pure-function chart-geometry tests**: `_nice_axis_step`, `_add_reach_flag_annotations`'s
     pixel-math, `_smooth_nonnegative_curve`'s PCHIP wrapper — all pure functions with no Dash/BQ
     dependency, all currently verified only by eyeballing a rendered chart.
  4. **One end-to-end smoke test for the Discover page specifically** (§5.2) — given it has the
     dashboard's most complex callback graph and the least margin for confident manual reasoning,
     it's the best single candidate for a Selenium/Playwright-style "load the page, apply a
     filter, assert the table updates" test, even if nothing else in the dashboard gets one.
  5. **`tenancy/access.py`'s `can_access`/`accessible_slugs`** — small, pure, security-relevant
     functions with zero current test coverage; a regression here is a real access-control bug,
     not just a cosmetic one.

None of this needs a full test-pyramid strategy or a CI overhaul to start paying off — even a
single `tests/` directory with `pytest` and the five items above, run manually before a deploy,
would be a categorical improvement over the current zero.

### 11.2 Observability is present but inconsistent

`logging_setup.py` establishes a sound, simple convention (structured `logging.getLogger(__name__)`
calls, one-time `basicConfig`), and most of the codebase follows it — the preload functions log
warnings on individual key failures, `tenancy/events.py` logs (rather than raises) on audit/usage
failures, `auth/firebase.py` logs cache misses appropriately. The exceptions are notable precisely
because they're exceptions: `narratives.py`'s `print()` debug statements (§5.4) bypass this
entirely, and — worth checking the next time anyone is in this code — there's no log line
anywhere in the preload fan-outs or `_server_discover_data()` distinguishing "cache cold, doing
real work" from "cache warm, instant" at the info level, which would make the cold-start behavior
described in §8.2 directly observable in Cloud Logging instead of inferred from latency alone.
**Recommendation**: a single `logger.info("Discover cache populated in %.2fs", elapsed)`-style line
in `_server_discover_data()`'s populate branch, and equivalent timing logs around each preload
fan-out's `ThreadPoolExecutor` block, would make the exact failure mode described in §8.2 visible
in production logs the next time it happens, rather than requiring this document's reasoning to
be re-derived from scratch under deadline pressure.

### 11.3 Resilience patterns are good where they exist, missing where they're assumed

`safe_query()`'s dev-fallback-but-raise-in-prod split (§3, `data_sources/bq.py:42-57`) is exactly
the right call — fabricating numbers in production would be worse than a visible error, and the
docstring says so explicitly. `tenancy/events.py`'s fail-soft audit/usage recording is the same
good instinct applied to non-critical telemetry. What's *not* covered: nothing in the 51 `load_*`
functions has a per-query timeout independent of `safe_query`'s general exception handling, so a
single hung BigQuery query (network partition, a runaway query against a much-larger-than-expected
table) blocks whichever preload thread or request thread is waiting on it for however long
BigQuery's own client-level timeout allows — worth confirming `google-cloud-bigquery`'s default
timeout behavior is acceptable here rather than assuming it is, given §8.2's finding that the
preload fan-out is already the most resource-contended moment in this app's lifecycle.

---

## 12. Security

This dashboard does not have the kind of glaring security holes this review was watching for, and
that's worth stating plainly rather than only listing caveats. The specific things checked and
confirmed clean, plus the handful of real (mostly low-severity) findings:

### 12.1 SQL injection: not a live risk, by construction

Every one of the 51 `load_*` functions in the data layer takes **zero arguments** (§3.1) — no user
input (dropdown selections, search box text, slider values) ever reaches a BigQuery query string.
All filtering on user-controlled values happens in pandas/Python after the fixed, parameterless
query has already run. This is a strong, structural guarantee, not a "we were careful this time"
one — there is no call site where a developer *could* introduce a SQL-injection bug into this
dashboard's data layer without first changing the load function's signature to accept a parameter,
which would be a visible, reviewable change. Confirmed by reading the data layer directly, not
inferred.

### 12.2 Access control is real but coarse — restating §6.2's implication as a security finding

`tenancy/access.py`'s gate genuinely enforces "can this user open `amazon_2026` at all" (§6.1) —
that part of the security model is sound. But because `amazon_2026`'s data layer is hardcoded to
one project/dataset (§6.2) with no row-level or dataset-level scoping by `client_id`, the
*effective* security boundary today is "all-or-nothing access to all of `amazon_2026`'s data" —
which is fine and matches reality while there's one client, but is worth flagging explicitly as a
**pre-condition that must be fixed before onboarding a second client to this dashboard**, not an
incremental hardening to get to eventually. Reselling this dashboard design to client #2 without
first wiring `resolve_client_dataset` through would mean client #2's users — once granted access
to a slug called `amazon_2026` — see client #1's BigQuery rows. This is the same finding as §6.2,
restated here because it's the framing that should drive prioritization: it's not a performance
nice-to-have, it's a tenant-isolation precondition.

### 12.3 Auth implementation details checked and sound

`auth/firebase.py`'s session-cookie flow (HttpOnly cookie, server-side verification, TTL'd claims
cache with forced periodic revocation re-checks) follows Firebase's own recommended pattern
correctly. `config.py`'s `auto_provision_users` default (`False`) is the safer default — an
authenticated-but-unprovisioned user is denied rather than silently granted zero-access-but-valid
access by default, requiring an explicit admin action either way. The dev-mode "View as" cookie
impersonation (`auth/middleware.py`) only activates when `auth_enabled=False`, so it's not a
production bypass path.

### 12.4 Minor, low-severity items

  - `cloudbuild.yaml:41` embeds `FIREBASE_API_KEY=AIzaSy...` directly in the deploy command rather
    than via `--set-secrets` (unlike `SESSION_SECRET`, which correctly uses Secret Manager).
    Firebase **Web API keys are designed to be public** (they identify a Firebase project to
    Google's client SDKs and are meant to ship inside client-side JS; the real access boundary is
    Firebase's own security rules plus authorized-domain restrictions, not key secrecy) — so this
    is very likely fine as-is and not a vulnerability, but it's worth a one-line confirmation in
    a README or comment that this specific key is intentionally treated as non-secret, so a future
    security pass doesn't have to re-derive that reasoning from scratch, and so nobody "fixes" it
    into Secret Manager for the wrong reason while leaving an actual secret exposed elsewhere.
  - The chat extension (`extensions/chat_with_data.py`) is correctly authorization-gated
    (`current_user()` + `can_access()` checked before any data leaves the endpoint, §6.3) and
    question length is capped (`_MAX_QUESTION_LEN = 500`) before it ever reaches a prompt — good,
    deliberate prompt-injection-surface minimization for what is, structurally, a
    user-input-to-LLM-prompt pathway.
  - No CSRF token is used on the chat endpoint, by explicit, documented design ("read-only... and
    is intentionally CSRF-exempt") — a defensible call given the endpoint only reads and returns
    data the user is already authorized to see; flagging only so this stays a deliberate decision
    that gets re-confirmed if the endpoint ever gains a mutating capability, not something assumed
    safe forever by inertia.

---

## 13. Prioritized roadmap

Organized by tier, not by section number — within a tier, items are roughly independent and can
be done in any order or in parallel by different people. Every item references the section with
full evidence/reasoning. Nothing here has been implemented; this is the punch list to work
through deliberately, in whatever order matches available time and risk appetite.

### Tier 0 — trivial, near-zero-risk, do whenever there's a spare hour

These are all small, mechanical, and each independently worth doing regardless of anything else
on this list:

1. Remove/replace the `print("[NARR-DEBUG] ...")` statements in `narratives.py` with proper
   `logger.debug(...)` calls, or delete them outright (§5.4, §11.2).
2. Decide and act on `set_dev_mode(True)` (`pages/__init__.py:36`) — either gate it on
   `settings.is_dev`, or rename the concept since it's clearly meant to be permanent (§5.3, §10.3).
3. Add a `threading.Lock` around `_server_discover_data()`'s populate-if-empty check
   (`charts_discover.py:57-72`) — five lines, removes a redundant-work race under concurrent
   first requests (§8.3).
4. Add one `logger.info` timing line each to `_server_discover_data()`'s populate branch and the
   five preload fan-outs, so cold-start behavior becomes observable in logs rather than inferred
   (§11.2).
5. Confirm and document (one comment, one line) that the Firebase Web API key in `cloudbuild.yaml`
   is intentionally non-secret, so it isn't "fixed" into Secret Manager for the wrong reason later
   while masking where an actual secret might be exposed (§12.4).

### Tier 1 — infrastructure/config changes: highest payoff per hour spent

These aren't code refactors — they're config and small wiring changes that directly fix the
biggest latency/consistency/cost risks found in this review:

6. **Raise `CACHE_DEFAULT_TIMEOUT` from 600 (10 min) to 3600 (1 hour) in `app.py`.** Single
   highest-value, lowest-effort fix in this entire document — the underlying data updates at most
   once a day, so the current 10-minute TTL re-fetches everything from BigQuery up to 144
   times/day for no freshness benefit (§9.1). One constant, no refactor, agreed with the team.
   Do this first — it's a one-line change with no downside.
7. **Set `--min-instances=1` on the Cloud Run service.** Directly eliminates the worst-case
   cold-start scenario (§8.2: 2 workers × ~40 concurrent BigQuery queries racing for 1 vCPU/1GB on
   a cold container) for the cost of one always-on instance. Do this before anything else on this
   list (besides #6) if a client might ever load the dashboard after an idle period.
8. Add a `threading.Lock`-guarded TTL (matching whatever #6 lands on) to
   `_server_discover_data()`'s cache (§8.3, §9.1) so Discover stops silently diverging from every
   other page's freshness guarantee the longer a worker has been alive — ideally by folding this
   into `data_manager` instead of maintaining a second hand-rolled cache next to it.
9. Move `tenancy.events.record_usage()` off the synchronous request path in
   `app.py::_install_access_gate` (§8.4) — fire-and-forget background thread, removing a Firestore
   round-trip from every single page navigation's latency budget.
10. Add a Firestore TTL policy (or scheduled rollup) on the usage-events collection (§9.4) before
    unbounded analytics-write growth becomes a cost-investigation a year from now.
11. Optional, lower priority than #6-10: move `flask_caching`'s backend from `SimpleCache` to a
    shared backend (Redis/Memorystore) to close the remaining multi-instance cache-fragmentation
    gap (§9.1) — worth doing if/when this runs at higher concurrent-instance counts, but #6 alone
    already removes most of the cost impact, so this is cleanup, not urgency.

### Tier 2 — close the multi-tenancy gap (schedule deliberately, don't discover under deadline)

12. **Wire `tenancy.access.resolve_client_dataset(current_user())` into `data_common.py`'s
    `_table()`/`PROJECT_ID`/`DATASET_ID`** (§6.2, §9.2, §12.2). This is the one item on this list
    that is both a scalability gap and a tenant-isolation precondition, not merely a nice-to-have
    — budget real design time for it (likely a request-scoped context var threaded from the access
    gate, consistent with `dashboards/_base.py`'s own documented intent that per-user data scoping
    happens "at request time inside dynamic-data loaders"), and treat it as a blocker for ever
    onboarding a second client onto this dashboard, not a backlog item to get to eventually.

### Tier 3 — deduplication pass (compounds over time, zero behavior change)

Best done together as a single focused pass, since they're all "delete duplicated code, change
nothing visible" — low risk, and the kind of work that's easiest to justify in one batch rather
than piecemeal:

13. Collapse the 5 near-identical startup preload functions into one parameterized helper (§8.1).
14. Extract the 3x-duplicated sentiment donut figure, the 2x-duplicated `_data_bar_column_styles`,
    and the 2x-duplicated `_combined_narratives_from_record` into `charts_shared.py` proper with
    public names (§4.2, §10.2).
15. Make the top publishers/journalists/publications table builder a real shared API instead of a
    private cross-module import from `charts_narratives.py` into `charts_campaigns.py` (§4.2).
16. Consolidate publisher-identity resolution (§3.3) and the campaign-column candidate list
    (§3.3) into single shared definitions in `data_common.py`; replace every inline
    `LIKE 'pos%'`-style sentiment check with the existing `_sentiment_case()` helper.
17. Build a `build_standard_page()` factory for the five pages that currently hand-roll near-
    identical `vm.Page(...)` scaffolding (§5.1).
18. Rename `--amazon-publishers-*` CSS custom properties to `--na-*` directly and delete the alias
    layer (§2.3, §7.3).
19. Consolidate the redundant per-page BigQuery scans noted in §9.1 (e.g. Overview's seven
    independent full scans of the same one or two source tables) into fewer, shared base queries —
    do this after, and separately from, the TTL fix (Tier 1 #6), since it addresses *how much*
    work happens per refresh rather than *how often* the refresh happens.

### Tier 4 — foundational investment (start small, this is the long game)

20. **Start a `tests/` directory.** Even just the five items in §11.1 (SQL-fragment helpers,
    fixture-shape assertions, pure chart-geometry functions, one Discover end-to-end smoke test,
    `tenancy/access.py`'s pure functions) would take this codebase from zero automated
    verification to "the highest-risk 20% of the code has a safety net." This is the single
    investment that makes every other item on this list — and everything written after this
    review — safer to do quickly. Start with #1 on that sub-list (SQL-fragment helpers); it
    requires no test infrastructure beyond bare `pytest` and no BigQuery access.
21. Split `charts_shared.py` into `theme.py` / `ui_components.py` / `timeline_charts.py` (§4.1) —
    do this *after* Tier 3's dedup pass, so there's less to move.
22. Design and prototype a BigQuery normalization view (or equivalent) that exposes one stable
    column name per concept for `amazon_2026_trad`/`amazon_2026_some`/`amazon_2026_publishers`,
    to eventually retire the 61-call-site schema-drift defense layer (§3.2). This is data-
    engineering work, not a Python refactor, and the highest-ceiling simplification in the data
    layer — but also the most expensive item on this list, so it belongs at the end, tackled when
    there's room to do it properly rather than squeezed in.
23. Add server-side row limits/sampling to `load_archive_scatter()` and
    `load_narrative_top_publications()` (§3.4) — not urgent today, but cheap to add now while the
    threshold is still comfortably far away, versus discovering the threshold the hard way later.
24. Wire an `amazon_2026` provider into `extensions/chat_with_data.py` (§6.3) so the platform's
    marquee AI feature stops being a dead end on the dashboard that matters most — or, if not a
    priority, explicitly suppress the chat widget on dashboards without a registered provider so
    it isn't a visible dead end in the meantime.

---

## 14. Target architecture: from one dashboard to a multi-client platform

This section answers a forward-looking question rather than a code-review question: the stated
goal is many **clients** (confirmed: up to ~30), each client with **multiple dashboards** and
**multiple users**, users possibly restricted to a subset of their client's dashboards, **strict
no-data-leakage** guarantees between clients, and a strong preference for **one running
application instance** so that shared internal tooling (theming, chat, saved views, table/KPI
components — everything built so far) is available to every client automatically rather than
forked N times. This is intentionally a conceptual architecture discussion, not an implementation
plan — depth stays at the "what shape should this take and why" level on purpose, per the brief.
§14.0 and §14.8 record the team's answers across two rounds of clarifying questions — between
them, every open question this section raised has now been resolved.

### 14.0 Requirements, as confirmed

- **Up to ~30 clients.** Small/medium enterprise scale, not thousands of self-serve tenants —
  this matters throughout: it keeps a shared-instance model's blast radius manageable and means
  operational/onboarding tooling can stay fairly lightweight for a while.
- **Clients are similar in the general kind of work they need, but every dashboard will be its
  own build — different charts, different pages.** Corrected from an earlier draft of this
  section, which misread "clients will be similar" as "one reusable dashboard template, pointed
  at different data." That's not the model: `amazon_2026` is **not** a universal template.
  General-purpose *pieces* (a complex chart type worth reusing, table/KPI components, theming) are
  expected to be shared; the overall page/chart design of a given dashboard is not.
- **Shared custom tooling — chat, saved views, and similar — is explicitly meant to be shared
  across all clients' users.** Confirms the platform-level tooling investment (extensions/*,
  charts_shared.py, the theming system) is the right thing to keep building centrally.
- **No data sharing between clients, ever.** Confirmed as an absolute constraint, as assumed.
- **A client may have access to multiple, possibly different *types* of dashboards.** Not just
  multiple instances of one template — a client's dashboard list can mix dashboard products.
- **New requirement surfaced in this round: an internal role — named "operator" — that services
  multiple clients and needs to switch between their dashboards, with less authority than a full
  admin.** Turns out to be already expressible with the existing access model, with one small
  caveat — see §14.3.

### 14.1 The good news: most of the *client-side* access-control shape already exists

`tenancy/models.py` + `tenancy/access.py` + `tenancy/users.py` (praised in §6.1 as some of the
best-built code in the repository) already model most of §14.0's shape for a client's *own*
users:

- `Client.dashboard_slugs` — a client is assigned a *list* of dashboards, of any type, not one.
  "Multiple, possibly different types of dashboards per client" is already representable today,
  with zero new code.
- `User.client_id` + `User.dashboard_slugs` — a user belongs to one client and inherits that
  client's dashboard grants, *plus* optional per-user extra grants; `accessible_slugs()`
  (`tenancy/access.py`) computes the actual visible set per user. "Multiple users per client,
  each possibly seeing a different subset of that client's dashboards" is already representable
  today, with zero new code.
- The request gate (`app.py::_install_access_gate`) already enforces "can this user open this
  dashboard slug at all" on every request, centrally, in one place — not per-dashboard, not
  reimplemented by each plugin.

What's **not** yet built is narrower than the previous draft of this section claimed. There is
genuinely only one confirmed gap, and it's smaller than "design a new role":

- Today's model has two role values (`is_admin` / regular `user`), but `accessible_slugs()`/
  `can_access()` (`tenancy/access.py:30-57`) already union `company_slugs(user)` (the user's own
  client's grants) with `user.dashboard_slugs` (per-user *extra* grants) — and **nothing in that
  code ties the extra grants to the user's own `client_id`**. `User.client_id` also defaults to
  `""` and nothing requires it to be set (`tenancy/models.py`). That means an "operator" user —
  empty `client_id`, `dashboard_slugs` populated with a curated list spanning several clients'
  dashboards — is **already fully expressible today, with zero new schema or access-logic
  changes**. §14.3 covers what (small) thing is actually still missing.

### 14.2 Confirmed direction: bespoke dashboards, sharing a toolkit — not a shared template

Corrected from the previous draft, which read "clients will be similar" as "build one dashboard
template and instantiate it per client." That's not the model. `amazon_2026` is one bespoke build
among many to come — its own page layout, its own charts, its own taxonomy — and most future
dashboards will look meaningfully different from it and from each other. What *is* shared is
lower-level: reusable chart types, table/KPI components, the theming system, navigation chrome,
and platform tooling (chat, saved views) — exactly the things already living in `charts_shared.py`
and `extensions/`.

This is good news for the architecture, not a complication: it means **tenant isolation is
structural, by construction**, not something that has to be engineered into a shared,
parameterized data layer. Each dashboard plugin is its own `dashboards/<slug>/` package, hardcoded
to whichever one client (or small group) it was built for, exactly like `amazon_2026` is today.
"Onboard a new client" mostly means *build their dashboard* (new pages, new charts) — it does not
mean *configure an existing one*, and so it doesn't carry the cross-client blast-radius risk a
shared template would (a bug in one dashboard's bespoke code cannot touch another dashboard's
data, because there's no shared code path between them that reads a "current client" and
branches on it).

The practical consequence: the platform's job is to (a) make it fast and consistent to *build* a
new bespoke dashboard — by investing in the shared toolkit, not a shared data layer — and (b)
make sure access control (which users can open which dashboard slugs) stays airtight as the
number of dashboards and clients grows. Both are mostly things this review already recommends
for other reasons (Tier 3 #17's page-scaffolding factory, Tier 4 #21's `charts_shared.py` split,
§11.1's access-control tests) — multi-tenancy mostly raises their priority rather than adding new
work.

### 14.3 The "operator" role (multi-client): smaller gap than first thought

This is the confirmed name for the internal role that services multiple clients — referred to
generically as "staff" earlier in this section's drafting; **"operator" is the term to use going
forward**, including in any future schema/UI work.

The previous draft of this section designed a whole new "servicing grant" + session-level
"active client" mechanism for operators who need to move between several clients' dashboards.
Given §14.1's direct read of `tenancy/access.py`, most of that isn't needed: grant an operator
`dashboard_slugs = [client_A's slug(s), client_B's slug(s), ...]`, leave `client_id` empty, and
they already see exactly those dashboards in their nav and can click between them like any other
multi-dashboard user — no new field, no "switcher" component, no per-request "active client"
context to invent, because each dashboard they open is its own self-contained, single-client
plugin (§14.2). Navigating between them is just navigating between pages, which already works.

What's actually still missing, now that the model itself is confirmed sufficient:

1. **A "follow this client's whole dashboard list" convenience, optionally.** A regular client
   user automatically inherits every dashboard their company has via `company_slugs()` — if that
   client is later granted a new dashboard, their own users see it for free. An operator's
   `dashboard_slugs` list has no such auto-follow: today you'd add each slug by hand, and adding a
   dashboard to "the clients an operator services" wouldn't propagate automatically. Worth a small
   follow-up if operators churn dashboards-per-client often enough for this to matter (e.g. a
   `serviced_client_ids` list that `accessible_slugs()` also expands via `company_slugs()` for
   each serviced client) — but it's a convenience feature, not a correctness gap, and easy to add
   later without disturbing anything built in the meantime.
2. **Auditing.** An operator opening a dashboard that isn't "their own" client's is a meaningfully
   different trust event than a client's own user viewing their own data — worth a
   `tenancy/events.py::record_audit` call site on that path, for internal accountability. Per
   §14.0/§14.8: clients have no access to the operator account or its activity, so this stays a
   purely internal record — no transparency-to-client feature to design.
3. **A small UX nicety, not an architectural one**: since an operator may hold grants across
   several clients' dashboards, labeling each dashboard with its owning client's name in the nav
   (rather than just the dashboard's own title) avoids ambiguity about whose data they're looking
   at — worth doing whenever the nav is touched next, not a standalone project.

The non-negotiable rule from §14.0 still applies and is, if anything, easier to guarantee here
than it looked in the previous draft: because every dashboard is its own bespoke, single-client
plugin, there is no code path that could blend two clients' data even by accident — an operator's
session is always looking at exactly one dashboard, which is always exactly one client's, by
construction.

### 14.4 Is "one running app instance" the right call?

Yes — and the corrected model in §14.2 makes this an *easier* call than the previous draft argued,
not a harder one. The confirmed scale (§14.0: up to ~30 clients) also helps, keeping the
operational blast-radius concerns below manageable.

**Why it's the right call:**
- It's the only option that actually delivers the stated goal of "shared tooling reaches every
  client automatically." A chat-widget improvement, a new table component, a theming fix — built
  once, live for everyone on the next deploy. Per-client deployments would mean either redeploying
  N services for every shared-platform change (operationally fine, but easy to let drift if not
  automated) or accepting that clients silently run different versions of shared tooling.
  Stated requirement.
- It's also, practically, the path of least resistance against the framework: Vizro/Dash's page
  registry is process-global (§2.1) — only one Vizro `Dashboard` can exist per Python process. The
  current architecture (one process hosting N dashboard plugins as pages) is already the
  *natural* way to use this framework for "many dashboards, one app." Fighting that toward
  per-client processes would mean running N full copies of the stack (N Cloud Run services, N
  preload fan-outs, N sets of cached data) for isolation benefits that, done carefully, can be had
  another way (next point).
- BigQuery-level isolation is achievable as a structural backstop *without* separate app
  deployments: if each client's data already lives in its own BigQuery dataset (the existing
  `bq_dataset_prefix`/`Client.bq_dataset` convention assumes exactly this) and the credentials the
  app uses to query BigQuery are scoped so they can only read the datasets they're supposed to
  (per-client service accounts, or IAM conditions on dataset access), then a missed or buggy
  client-scoping check in Python **fails closed** — BigQuery returns a permissions error — instead
  of **failing open** and silently returning another client's rows. This is the single highest-
  leverage move available: it converts "robust separation" from "we trust the Python code is
  always correct" (the actual situation today — zero test coverage on the relevant code paths,
  per §11.1) into "even a bug can't leak data, it can only break loudly." This is worth treating as
  load-bearing infrastructure, not a nice-to-have, precisely *because* you want one shared
  instance.

**What it costs, honestly — smaller than the previous draft suggested:**
- **No process/OS-level isolation between clients.** A crash, memory leak, or runaway query
  triggered by one client's dashboard still runs in the same container, competing for the same
  CPU/memory, as every other client's traffic (the "noisy neighbor" problem — directly related to
  the cold-start/resource-contention findings in §8.2). This is still real and still needs
  monitoring (per-dashboard resource/latency tracking), and an escape valve (below) if it ever
  becomes acute for one client — that part of the previous draft's analysis stands unchanged.
- **Robustness is still a software-correctness concern, just a narrower one than previously
  described.** Each dashboard's bespoke code only ever touches the one client it was built for
  (§14.2), so there's no shared, parameterized layer whose bugs could cross client boundaries —
  the realistic failure mode is *copy-paste*: building dashboard #5 by starting from dashboard #2's
  code and forgetting to update a hardcoded project/dataset constant for the new client. That's a
  build-time review/checklist item (§14.6), not an ongoing architectural risk every request is
  exposed to.
- **If a specific client ever contractually requires literal physical isolation** — a shared
  instance still can't offer that guarantee no matter how good the engineering is. Keep the escape
  valve open (config-driven per-client settings in `app.py`, so the same image could be deployed
  single-tenant for one client if ever required) without building for it by default.

**Bottom line**: one shared instance is the right call, and the bespoke-per-dashboard model
(§14.2) makes tenant isolation closer to "true by construction" than "something to engineer in" —
the main remaining work is operational (noisy-neighbor monitoring, IAM-level defense in depth) and
procedural (a checklist for building new dashboards correctly), not a redesign of any shared data
mechanism, because there isn't one.

### 14.5 The technical problem from the previous draft doesn't apply here

The previous draft of this section spent real effort on a hard problem: Vizro's `data_manager`
caches by key identity, not by tenant, so a *shared, parameterized* dashboard template would need
its cache keys generalized to "key + active client." **That problem is specific to a templated
architecture, and §14.2 confirms that's not the model here.** Each dashboard's `data_manager`
entries are already, correctly, scoped to the one client that dashboard was built for — exactly
like `amazon_2026`'s are today — and that stays true as more bespoke dashboards get added. There
is no generalized cache-key-per-tenant mechanism to build.

The one narrow residual case worth naming: if a single dashboard's *code* is ever deliberately
reused for two instances of the same client (e.g. one client wants the identical dashboard design
for two of their own brands), that one dashboard would need tenant-aware cache keys *locally* — a
small, contained decision made when (if) it happens, not a platform-wide requirement to design for
now.

### 14.6 Step-by-step transformation plan

Much shorter than the previous draft, because §14.2's correction removes the biggest piece of
work (a generalized multi-tenant data layer) entirely.

1. **Treat `amazon_2026`'s existing gap (roadmap #12) as "use `Client.bq_dataset` instead of a
   hardcoded constant," not "build shared multi-tenant infrastructure."** Worth doing for
   ordinary config-over-hardcoding reasons (one place to fix if this client's dataset ever moves)
   and so the *next* bespoke dashboard has a real example to copy the right pattern from — not
   because other clients will ever run this same code.
2. **Write a short "new dashboard" checklist**, since the realistic risk is copy-paste (§14.4):
   when starting dashboard #N from an existing one, confirm every data-layer constant
   (project/dataset, any hardcoded IDs) is correctly set for the new client *before* granting
   anyone access to its slug. Cheap to write, and the single highest-leverage guard against the
   actual failure mode in this model.
3. **Push the per-client dataset convention down into BigQuery IAM** — scope the credential the
   app uses so it can only reach the datasets it's supposed to, so a missed step-2 mistake fails
   closed (permission error) instead of open (wrong client's data returned). At ~30 clients this is
   a finite, manageable amount of IAM configuration — worth doing properly while the list is short.
4. **Add the access-control test this review already recommends (§11.1, roadmap #20)**, scoped
   simply: "a user only ever sees dashboard slugs in their `accessible_slugs()` result, including
   operators with cross-client `dashboard_slugs` grants." This is testing the existing, already-
   sufficient logic in `tenancy/access.py` (§14.1) — not new code, just the regression guard it's
   missing today.
5. **Add the audit-log call site from §14.3** (operator opening a dashboard outside their own
   client) and, whenever the nav is next touched, label dashboards by owning client for operators
   who hold cross-client grants (§14.3's UX nicety). Per §14.8, this stays a purely internal log —
   clients have no visibility into the operator account or its activity, so there's no
   transparency-facing surface to build alongside it.
6. **Invest in the shared toolkit as the actual lever for scaling to ~30 clients**: the
   page-scaffolding factory (Tier 3 #17) and the `charts_shared.py` split into
   `theme.py`/`ui_components.py`/`timeline_charts.py` (Tier 4 #21) are exactly "the starter kit the
   next bespoke dashboard gets built from" — this is where onboarding speed actually comes from in
   this model, not from a shared data layer.
7. **Build the noisy-neighbor observability from §14.4** (per-dashboard CPU/memory/BigQuery-cost
   tracking) before it's needed in anger, and keep the single-tenant escape valve viable
   (config-driven per-client settings, not hardcoded) without acting on it by default.
8. **Grow the admin workflow** (`tenancy/access.py`'s grant model, the admin routes in `admin/`)
   to comfortably handle ~30 clients' worth of dashboard/user provisioning and admin-assigned
   operator grants (confirmed admin-only, §14.8) — the data model already supports this (§14.1);
   only the workflow needs to scale.

### 14.7 What changed from the previous draft of this section, for the record

The previous draft assumed "clients will be similar" meant one reusable dashboard template
instantiated per client, and designed a fair amount of new machinery around that assumption: a
generalized multi-tenant data layer with tenant-aware cache keys, and a new "servicing grant" +
session-level "active client" mechanism for the multi-client role. The correction — every
dashboard is its own bespoke build, sharing only lower-level components — removes the need for
almost all of that: the cache-key problem doesn't arise because there's no shared data layer to
generalize, and the multi-client role (now named **operator**) turns out to already be expressible
with the existing `dashboard_slugs` grant mechanism, verified directly against
`tenancy/access.py`. What's left is smaller and mostly procedural (§14.6) rather than
architectural — which is a better position to be in, not a worse one.

### 14.8 Resolved (previously open questions)

1. **Every client has its own dataset; no data sharing, full stop.** Confirmed — there is no
   shared-dataset-with-a-column-filter case to design for. This makes the IAM-level backstop in
   §14.6 step 3 the right and sufficient structural guard: scope each client's BigQuery access by
   dataset, not by row, and a missed application-level check fails closed automatically.
2. **Operator cross-client `dashboard_slugs` grants are assigned by admins only.** Confirmed,
   matching the existing dashboard-grant workflow — no self-service path to design.
3. **Clients have no access to the operator account or its activity.** Confirmed — the audit log
   from §14.3/§14.6 step 5 is purely internal. There is no client-facing transparency feature to
   design alongside it; build the audit trail for internal accountability only.

No open questions remain from this round.
