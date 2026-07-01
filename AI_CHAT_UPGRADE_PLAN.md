# AI Chat Upgrade Plan — from Q&A widget to embedded data analyst

Status: **plan only, nothing implemented**. Written 2026-07-02.

---

## 1. Where we are today

The current feature (`extensions/chat_with_data.py` + `assets/ext_chat.js`) is a
minimal one-shot Q&A widget:

| Aspect | Today |
|---|---|
| Model | Single Gemini call (`gemini-2.0-flash`), no tools, no loop |
| Context | `df.head(15)` + `describe()` of **one** dataframe per dashboard |
| Data access | 1 hardcoded provider per dashboard (`_DATA_PROVIDERS`); amazon_2026 exposes only the narratives table |
| Conversation | None — every question is independent, no history sent |
| Output | Plain text only; no charts, no tables, no citations |
| UX | Fixed side panel, no streaming, no markdown rendering |
| Fallback | Keyword-matching pandas heuristic when no API key |

The plumbing around it is good and should be kept: auth/tenancy gating
(`can_access`), per-user rate limiting, the detachable-extension pattern, and
the graceful offline fallback.

The gap to "cutting edge" is not the model — it's that the assistant **cannot
see the data catalogue, cannot run its own queries, and cannot produce
anything but text**.

---

## 2. Target vision

> A PR analyst's junior colleague that lives inside the dashboard: it knows
> every table behind every page, runs its own queries to answer questions it
> can't answer from summaries, cites the articles/posts behind every claim,
> builds charts on demand in a Playground page, and proactively writes the
> "so what" — weekly digests, anomaly explanations, coverage-report drafts.

Concrete user stories (PR-agency flavoured):

1. *"Why did negative sentiment spike in week 23?"* → agent queries the weekly
   sentiment timeline, finds the spike, pulls the top publications from that
   week via the Discover corpus, and answers with linked citations.
2. *"Compare the 'Prime Day' and 'Sustainability' campaigns on earned vs. paid
   reach"* → agent joins two campaign tables, returns a table + a grouped bar
   chart pinned to the Playground.
3. *"Draft a one-page coverage summary for the client for June"* → agent
   aggregates KPIs, top narratives, sentiment shifts, notable outlets, and
   produces a formatted markdown brief the analyst can copy out.
4. *"Show me reach by media type over time, but only for negative coverage"*
   → a chart that doesn't exist on any page, generated in the Playground.

---

## 3. Architecture

### 3.1 Core: an agentic tool-use loop (replace the one-shot prompt)

Replace the single `generate_content` call with a **function-calling loop**
(Gemini's native function calling — the key and SDK are already wired in;
`gemini-2.0-flash` and successors support it). No LangChain, no framework:
the loop is ~150 lines — send messages + tool declarations, execute the
requested tool, append the result, repeat until the model answers, cap at
N=8 tool calls per turn.

```
extensions/chat_with_data.py   (grows into extensions/chat/ package)
├── agent.py        # the loop: messages ⇄ Gemini ⇄ tool dispatch
├── tools.py        # tool implementations (below)
├── catalog.py      # data-awareness registry (§3.2)
├── routes.py       # /ext/chat/ask (SSE), /ext/chat/history, ...
└── charts.py       # chart-spec validation → plotly Figure
```

### 3.2 Data awareness: a dataset catalogue, not one hardcoded frame

The single biggest unlock. The app already has a natural catalogue — the
~50 `data_manager` keys in `dashboards/amazon_2026/data_common.py`
(`NARRATIVES_KEY`, `CAMPAIGN_TIMELINE_KEY`, `TOPIC_AREA_*`, `PUBLISHER_*`, …).
Every one of those is a cached, pre-aggregated, tenant-scoped DataFrame that
the dashboards themselves render. The agent should see the same data the user
sees — nothing more, nothing less.

Build a `catalog.py` that, per dashboard slug, exposes:

```python
@dataclass
class DatasetInfo:
    key: str            # data_manager key
    name: str           # human name, e.g. "Weekly reach per narrative"
    description: str    # 1–2 sentences: grain, filters, caveats
    columns: dict[str, str]   # name -> dtype + meaning
```

- Generated **mostly automatically** at startup (key, columns, dtypes, row
  count from the cached frame) + a small hand-written description per key.
  The descriptions are the "semantic layer" — this is what makes text-to-query
  accurate (the same idea as Vanna/WrenAI's context layer, at 1/100th the
  machinery).
- Dashboards opt in by exporting `CHAT_DATASETS: dict[key, description]` from
  their package (fits the existing plugin contract in `dashboards/_base.py`).
- The catalogue (names + descriptions only, not data) goes into the system
  prompt. Cheap: ~2–3k tokens for all of amazon_2026.

### 3.3 The agent's tools

| Tool | What it does | Safety boundary |
|---|---|---|
| `list_datasets()` | Catalogue for the current dashboard slug | Slug from the authed request, never from the model |
| `get_dataset(key, ...)` | Schema + sample rows + describe() of one catalogued frame | Only catalogued keys |
| `query(sql)` | **DuckDB SQL over the cached DataFrames** (each catalogued frame registered as a view). Returns ≤200 rows as markdown/JSON | Read-only in-memory engine; zero BigQuery cost; can't reach raw PII tables; result-size cap |
| `search_coverage(query, filters)` | Semantic + keyword search over the Discover corpus — **reuse the existing `DISCOVER_VECTORS_TABLE` VECTOR_SEARCH path** from `charts_discover.py` | Same table Discover already exposes to this user |
| `create_chart(spec)` | Validated chart spec → Plotly figure rendered in chat / pinned to Playground (§4) | Spec-based, no code execution |
| `get_page_context()` | What page the user is on + current filter selections (sent by the client with each message) | Client-supplied, display-only |

Why DuckDB over the cached frames instead of letting the model write BigQuery
SQL: it's free (no bytes billed), fast (data is already in memory), inherently
scoped to what the dashboards show, and `pip install duckdb` is the only new
dependency. Text-to-BigQuery against raw `amazon_2026_trad`/`_some` tables is
deliberately **out of scope for v1** — the pre-aggregated frames answer ~95%
of analyst questions; revisit only if users hit real walls (then: SELECT-only
validation via `sqlglot`, table allowlist, `maximum_bytes_billed` — the knobs
already exist in `data_sources/bq.py`).

### 3.4 Conversation state & history

- Send the running message list (client keeps it in `sessionStorage`; server
  stays stateless per request — no new infra).
- Persist finished conversations to Firestore (`chat_sessions/{uid}/...`)
  for "continue where I left off" + an admin usage view. The Firestore client
  and tenancy model already exist.
- Token budget: truncate to last ~20 messages; summarize older turns into one
  system line if needed.

### 3.5 Streaming

Switch `/ext/chat/ask` to **Server-Sent Events** (`stream=True` on the Gemini
SDK, `Response(generator, mimetype="text/event-stream")` in Flask — no new
dependency). Stream text tokens; emit structured events for tool activity
(`{"event": "tool", "name": "query", "detail": "..."}`) so the UI can show
"🔍 Querying weekly sentiment…" progress lines — this transparency is a large
part of what makes modern AI chat feel trustworthy.

### 3.6 Frontend

Keep the vanilla-JS extension pattern (`ext_chat.js`) — it survived Dash's
DOM churn and needs no build step. Upgrade it:

- Markdown rendering (tables, bold, links) — add `marked.min.js` (~40KB) or
  a minimal renderer; sanitize output.
- Streaming via `EventSource`/fetch-readable-stream.
- Tool-activity status lines (collapsible).
- Inline Plotly charts in the chat log (Plotly.js is already on every page —
  `Plotly.newPlot` on a div with the figure JSON is free).
- Suggested starter questions per dashboard (from the catalogue).
- "Pin to Playground" button on every chart/table the agent produces.

---

## 4. The Playground page

A new page per dashboard: `/d/<slug>/playground` (fits the existing
`build_pages` plugin contract and the nav rail scoping in `app.py`).

Layout: chat panel on the left (same widget, docked open), a **chart canvas**
on the right — a grid of cards, each card one AI-generated chart or table.

How charts are created — **spec-based, not code-execution**:

1. The `create_chart` tool takes a constrained JSON spec:
   `{dataset_key, transform: {filter, groupby, agg, pivot…}, chart: {type: bar|line|area|scatter|pie|heatmap, x, y, color, facet, title}}`.
2. Server validates the spec (catalogued dataset, real columns, whitelisted
   aggregations), runs the transform in pandas/DuckDB, builds the figure with
   plotly-express, and applies the existing dashboard theme/template so
   Playground charts look native.
3. The spec (not the figure) is what gets persisted — reproducible, tiny, and
   re-runs against fresh data on reload. Persist pinned specs per user in
   Firestore; the existing `saved_views` extension is the pattern to follow.

Why not let the model write Python (the Vizro-AI / pandas-ai approach):
`exec()` of LLM-generated code on a multi-tenant server handling client data
is a real security decision, and prompt-injection via the data itself (article
titles!) makes it worse. The spec covers the overwhelming majority of chart
requests. If a hard requirement for arbitrary code emerges later, the upgrade
path is a sandboxed executor (separate Cloud Run job, no creds, seconds
timeout) — noted here so it's a decision, not an accident.

Each card gets: refresh, edit-spec-via-chat ("make it stacked"), download PNG/CSV
(Plotly modebar gives PNG for free), delete, and "explain this chart" (feeds
the spec + data back to the agent).

---

## 5. PR-industry killer features (the differentiators)

These are what make it more than a generic "chat with your data" clone.
Ordered by value/effort:

1. **Cited answers.** Every claim the agent makes about coverage links to the
   underlying publications via `search_coverage` — rendered as footnote links
   that open the Discover page filtered to that item. Analysts can't put
   uncited numbers in front of clients; this single feature makes answers
   *usable in deliverables*.
2. **"Explain this chart."** A small ✨ button in the existing chart menu
   (`native_analytics_chartmenu.js`) that opens chat pre-seeded with that
   chart's dataset + current filters and asks the agent to interpret it.
   Cheap to build, high perceived intelligence, and it teaches users what
   the chat can do.
3. **Weekly digest generator.** One prompt template over the weekly tables:
   what moved (reach, sentiment, share-of-voice), which narratives/campaigns
   drove it, notable new publications. Output = markdown brief. This is the
   deliverable PR agencies produce by hand every Monday.
4. **Anomaly explanations.** Deterministic detection (rolling z-score on
   weekly reach/sentiment per narrative — pandas, no AI) surfaces "week 23:
   negative reach 3.2σ above trend"; the agent is then asked to explain it
   from the coverage. AI explains, code detects — cheaper and more trustworthy
   than asking the model to find anomalies itself.
5. **Comparative briefs.** "Compare narrative A vs B", "this month vs last" —
   template-guided prompts over the catalogue, output with charts pinned to
   the Playground.
6. *(Later)* Scheduled digests emailed/posted per client; crisis-detection
   alert («negative reach on narrative X doubled day-over-day») — needs the
   existing daily-load hook (`/internal/cache/refresh`) as the trigger point.

---

## 6. Security & cost (non-negotiables)

- **Tenancy**: slug + user come from the session, never from model output;
  every tool call re-checks `can_access`. The agent process only ever holds
  frames the user's dashboards already expose.
- **Prompt injection**: article titles/summaries in the corpus are untrusted
  input. Tool results are wrapped in delimiters with an instruction that data
  is data; tools are read-only, so the blast radius of a successful injection
  is a wrong answer, not an action. Keep it that way — no write-tools, ever,
  without a human click.
- **Cost caps**: keep the per-user rate limit; add a per-turn tool-call cap
  (8) and a daily per-user token budget (counter in the existing cache).
  Flash-class models keep a heavy session at fractions of a cent.
- **Output size**: tool results truncated (≤200 rows, ≤20KB) before entering
  the prompt.
- **Logging**: log (uid, slug, question, tool calls, tokens, latency) to the
  existing audit/events path — needed for both abuse detection and knowing
  what users actually ask (which drives the roadmap).
- **XSS**: markdown rendering must sanitize (model output + data columns both
  end up as HTML).

---

## 7. What we looked at, and what to copy vs. build

| Project | Verdict |
|---|---|
| [Vizro-MCP / Vizro-AI](https://github.com/mckinsey/vizro) (same authors as our framework) | **Copy the idea, not the code.** Vizro-AI dashboard generation is discontinued in favour of Vizro-MCP, which targets desktop LLM clients (Claude Desktop/Cursor), not embedded in-app chat. Their lasting lesson: charts as *validated specs/models*, which §4 adopts. ([docs](https://vizro.readthedocs.io/projects/vizro-ai/)) |
| [Vanna](https://github.com/vanna-ai/vanna) | Text-to-SQL via RAG over schema+docs. Their lesson: **accuracy comes from the curated semantic layer**, not the model — adopted as our catalogue descriptions (§3.2). The library itself brings a vector-store stack we don't need for ~50 well-described tables. |
| [WrenAI](https://github.com/Canner/WrenAI) | Governed text-to-SQL platform incl. BigQuery. Impressive, but it's a whole separate service + UI to deploy and reverse-integrate; overkill vs. ~1k lines inside our extension. Its "context layer" concept validates §3.2. |
| [DB-GPT](https://github.com/eosphoros-ai/DB-GPT) | Full agentic data platform. Same verdict: architecture inspiration (agent + tools + chart output), too heavy to embed. |
| pandas-ai | LLM-generated pandas code + exec. Rejected for the exec risk (§4). |

Net: **nothing is drop-in** for an embedded, multi-tenant, Vizro-hosted chat —
but every proven pattern above (tool loop, semantic catalogue, spec-based
charts, cited retrieval) is small enough to implement directly. Total new
dependencies: `duckdb` (+ optionally `sqlglot` later, `marked.js` client-side).

---

## 8. Phased roadmap

Each phase ships something usable on its own; stop after any phase and the
feature is still coherent.

**Phase 1 — Agent core + data awareness (the 80/20).**
Catalogue (§3.2), tool loop (§3.1) with `list_datasets` / `get_dataset` /
`query`, conversation history in the request, markdown rendering in the panel.
*Outcome: the assistant genuinely knows and can interrogate all dashboard data.*
~3–5 dev-days.

**Phase 2 — Streaming + citations.**
SSE streaming with tool-activity lines (§3.5), `search_coverage` tool reusing
the Discover vector search, footnote citations linking into Discover.
*Outcome: trustworthy, sourced answers with modern UX.* ~3–4 dev-days.

**Phase 3 — Charts + Playground.**
`create_chart` spec tool, inline charts in chat, the `/playground` page with
pin/persist via the saved-views pattern (§4).
*Outcome: the headline feature — the assistant builds its own charts.*
~5–7 dev-days.

**Phase 4 — PR-analyst features.**
"Explain this chart" button, weekly digest template, anomaly detection +
explanation (§5 items 1–4), Firestore chat history, admin usage view.
~5+ dev-days, prioritized by what Phase 1–3 usage logs show people ask for.

**Deliberately not planned** (YAGNI until proven needed): raw-table
text-to-BigQuery, sandboxed code execution, voice input, multi-model routing,
LangChain/agent frameworks, a vector DB (BigQuery VECTOR_SEARCH already
serves that role).

---

## 9. Open questions for the team

1. **Model**: stay on Gemini (key wired, flash is cheap, function calling +
   SSE supported)? The loop is provider-agnostic in shape, but write it for
   one SDK — don't build an abstraction for a second provider we don't use.
2. Should the Playground be per-dashboard (`/d/amazon_2026/playground`,
   recommended — inherits tenancy for free) or one global page?
3. Is Firestore chat persistence wanted in v1, or is per-tab session memory
   enough to start? (Recommended: start per-tab, add Firestore in Phase 4.)
4. Digest distribution: in-app only first, or is email delivery a near-term
   client ask? (Affects whether Phase 4 needs an email integration.)
