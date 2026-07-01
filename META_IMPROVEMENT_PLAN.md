# Meta Layer Improvement Plan — Client Hub, Admin, Auth, Tenancy, Extensions

> **Update (2026-06-29): items #1–#4 implemented; #5 reconsidered (no code change needed); #6
> (admin/routes.py split) deliberately not bundled into this pass — see §4.** `pytest` green
> (109 tests, 2 new: `tests/test_auth_firebase.py`, `test_chat_endpoint_rate_limits_repeated_calls`
> in `tests/test_routes.py`). Details:
> - **#2/#3 (cookie flag + session-secret guard) — done.** `pages_landing/routes.py`'s dev-
>   impersonation cookie now sets `secure=not settings.is_dev`, matching the real session cookie.
>   `config.py` exports `DEFAULT_SESSION_SECRET`; `app.py::create_app()` now raises at boot if
>   `settings.env == "prod"` and `session_secret` is still that literal.
> - **#1 (claims-cache eviction) — done.** `auth/firebase.py::_claims_cache` now sweeps entries
>   older than `SESSION_COOKIE_TTL` every 200 inserts (`_maybe_sweep_claims_cache`) instead of
>   relying on the same key being looked up again to evict itself. No new dependency — a plain
>   periodic sweep, not a TTL-cache library, for one dict.
> - **#4 (chat rate limit) — done.** `extensions/chat_with_data.py::ask()` now rejects a user's
>   21st call within 60 seconds with 429 (`_rate_limited`, an in-process sliding window —
>   per-process like the existing `SimpleCache`/`/internal/cache/refresh` caveat already
>   documented elsewhere in this codebase; add a shared backend only if multi-instance abuse is
>   observed).
> - **#5 (usage-event pagination) — reconsidered, no change made.** On closer look, the admin
>   Usage page already renders one row per *dashboard* (an aggregate), not one row per event —
>   `dashboards/amazon_2026/IMPROVEMENT_PLAN.md` §5.24 already concluded pagination there "would
>   solve a non-problem," and that reasoning holds. `list_usage_events(limit=5000)` is already a
>   bounded read, not unbounded growth; past 5000 cumulative events the aggregate would only become
>   stale (most-recent-5000-only), not slow or memory-heavy — a different, lower-priority concern
>   than what was originally flagged, not worth code churn at current scale.
> - **#6 (split admin/routes.py) — done, as its own confirmed pass, separate from #1–#4.**
>   `admin/routes.py` (1148 lines) is now three files: `admin/services.py` (134 lines —
>   non-HTTP business logic: invites, role/client validation, sanitization, dashboard-owner
>   assignment, logo encoding), `admin/views.py` (320 lines — HTML-rendering widgets and the
>   per-page detail-panel builders), and `admin/routes.py` (769 lines — the Blueprint and its
>   view functions only, plus small per-route closures that close over route-local variables).
>   Pure move + rename (dropped the leading underscore from functions that are now another
>   module's public API; no behavior change). Only `bp` was ever imported from `admin.routes`
>   elsewhere in the repo (`app.py`), so no other module needed updating. Verified: `pytest`
>   green (109 tests, unchanged), plus a direct in-process hit of all 8 admin pages
>   (`/admin/`, `/users`, `/operators`, `/clients`, `/dashboards`, `/audit`, `/usage`, `/health`)
>   confirming 200s post-split.
> - **#7 (dashboard_owner_map/operator_slugs caching) — skipped, as planned.** Still premature
>   against the ~30-client target.
>
> Audit date: 2026-06-29. Scope: `app.py`, `config.py`, `auth/*`, `tenancy/*`, `admin/routes.py`,
> `pages_landing/*`, `extensions/*`, `data_sources/bq.py` — the platform shell shared by every
> dashboard, not the `amazon_2026` dashboard's own data/chart layer.
>
> This is a companion to `dashboards/amazon_2026/IMPROVEMENT_PLAN.md`, which already covers this
> same shell plus the dashboard layer in much greater depth and has an active, dated history of
> fixes (§5.1–§5.27). Read that document first — most structural findings about this layer already
> live there, several already fixed. This file holds only what that document doesn't yet cover:
> findings new to this pass, with the false positives this pass ruled out kept for the record so
> they aren't re-flagged blind in a future audit.
>
> Verification method: four parallel read-only code audits (auth/tenancy, admin, app
> bootstrap/config, extensions/data_sources), then every claim above "low" severity was checked
> directly against the source before being kept — several were not. `pytest` was green (107 passed)
> at audit time.

---

## 1. Rating

| Area | Grade | Why |
|---|---|---|
| `tenancy/` (access.py, users.py, models.py, events.py) | **A-** | `Protocol`-typed dual store (in-memory dev / Firestore prod), single source of truth for access (`accessible_slugs`), fail-soft audit events off-thread. Best-structured code in the repo. Minor scale rough edges only. |
| `auth/` (firebase.py, middleware.py) | **B+** | Correct dev-fallback/prod-raise discipline, real+effective identity separation for impersonation, periodic revocation re-check. One real cache leak, one real cookie-flag gap (below). |
| `admin/routes.py` | **B-** | Functionally solid (users/clients/grants/audit/search/pagination all present), but a 1148-line single file mixing routing, inline HTML generation, and business logic. Needs a split before the next admin feature lands in it. |
| `app.py` / `config.py` (bootstrap) | **B** | Self-aware about its own risk — every framework-internal dependency (Dash monkeypatch, `ScopedNavBar`) is documented inline. Gaps are real but small. |
| `pages_landing/` (Client Hub) | **B+** | CSRF is deliberately and correctly scoped: state-changing forms protected, the token-gated JSON login endpoint exempted with a documented reason. One real cookie-flag gap (below). |
| `extensions/` (chat, saved views) | **B** | Both detachable-by-design and well-scoped — chat only ever touches pre-aggregated keys, never raw tables; saved-views is honestly browser-only, not a half-built sync feature. Missing rate-limit on the LLM endpoint is the one real gap. |

**Overall: B+.** No rewrite is warranted anywhere in this layer.

---

## 2. Confirmed findings (new to this pass)

Each was verified by reading the actual source, not taken on the auditing agent's word.

1. **`auth/firebase.py:33` — `_claims_cache` grows unbounded.**
   Keyed by SHA-256 of the session cookie; an entry is only evicted lazily when *that same key* is
   re-accessed after its TTL expires. A user who authenticates once and never returns leaves a
   permanent entry. Medium severity at the platform's documented ~30-client target; a real,
   slow leak over months of uptime.
   **Fix direction:** swap the bare `dict` for a `cachetools.TTLCache` (or add a periodic sweep) so
   stale entries are reclaimed without needing a matching request. Effort: XS.

2. **`pages_landing/routes.py:511` — dev-impersonation cookie (`na_dev_as`) missing `secure=`.**
   The real session cookie (line 442) correctly sets `secure=not settings.is_dev`. This cookie
   doesn't — and per `dashboards/amazon_2026/IMPROVEMENT_PLAN.md` §5.24, "view as" now runs for real
   admins in **production**, not just dev, so this flag now matters in the environment where it's
   missing.
   **Fix direction:** add `secure=not settings.is_dev` to match the session cookie. Effort: XS.

3. **`config.py:53` — `session_secret` has an insecure literal default with no production guard.**
   `cloudbuild.yaml` does inject the real secret via Secret Manager today, so this isn't currently
   exploited — but nothing in code stops a future deploy from silently running with the placeholder
   if that wiring is ever dropped or misconfigured.
   **Fix direction:** fail fast in `create_app()` if `settings.env == "prod"` and `session_secret`
   still equals the default literal. Effort: XS.

4. **`extensions/chat_with_data.py` — `/ext/chat/ask` has no rate limiting.**
   Auth-gated and dashboard-access-gated, but any logged-in user can loop it and run up Gemini
   billing with no per-user or global cap.
   **Fix direction:** a simple per-user token-bucket or a `Flask-Limiter` rule on the blueprint.
   Effort: S.

5. **`admin/routes.py` — Usage page loads up to 5000 events into memory per request for in-process
   aggregation** (`list_usage_events(limit=5000)`), and the Audit page similarly caps at 1000
   (`list_audit_events(limit=1000)`). Fine today; a real ceiling once event volume grows.
   `dashboards/amazon_2026/IMPROVEMENT_PLAN.md` §5.24 already added search+pagination to the
   Users/Audit pages — this usage-event aggregation path wasn't part of that pass and is still open.
   **Fix direction:** paginate or pre-aggregate server-side once usage-event volume actually grows;
   not urgent at current scale. Effort: S.

6. **`admin/routes.py` is a 1148-line single file** mixing route handlers, inline HTML
   string-building, and business logic (user/client CRUD, grants, audit, health, usage). Not a bug,
   but the next thing to get harder to touch as admin features keep landing — the same shape of
   problem `charts_shared.py` had before `dashboards/amazon_2026/IMPROVEMENT_PLAN.md` §5.4 split it.
   **Fix direction:** split into routing / HTML-rendering / business-logic modules when the next
   substantial admin feature is added, not as a standalone refactor. Effort: M.

7. **`tenancy/access.py::dashboard_owner_map()` and `operator_slugs()` — no caching.**
   Both do a full `list_clients()` scan on every call; called per-request from admin pages and the
   access gate. Real N+1, but harmless at the platform's documented ~30-client target.
   **Fix direction:** skip unless the client count target actually moves past ~30 — premature
   otherwise. Effort: XS if/when needed.

---

## 3. False positives ruled out this pass

Recorded so a future audit doesn't re-flag these blind. Each was checked directly against the
source or the codebase's own documented design rationale.

- **`/sessionLogin` "missing CSRF protection."** Deliberate, documented in `security.py`'s own
  module docstring: it's a token-gated JSON endpoint (requires an unguessable Firebase ID token),
  not a cookie-riding form submission, so CSRF doesn't apply. Correct as-is.
- **`app.py` "`debug=True` hardcoded in production."** Only inside `if __name__ == "__main__":`,
  which never executes in production — the real entrypoint is `gunicorn app:server`
  (see `Dockerfile`), which never imports that block's `debug=` flag. Dev-only convenience.
- **`tenancy/access.py::resolve_client_dataset` "silently returns empty dataset on a missing
  client, breaking tenant isolation."** Misread: it falls back to a dataset name derived from
  config convention, never an empty string in that branch. Separately, `company_slugs()` and
  `can_access()` correctly fail **closed** (deny access) when a client record is missing — not
  open, as the original claim assumed.
- **`extensions/saved_views.py` "no tenant isolation — a user can read another user's saved
  views."** Misunderstands `dcc.Store(storage_type="local")`: that's the *browser's own*
  localStorage, scoped per-origin per-browser. There is no server-side storage for one user's
  browser to leak into another's.
- **`extensions/chat_with_data.py` "prompt injection via dataset column names."** Theoretically
  real in the abstract, but not exploitable here: column names come from the platform's own fixed
  schema (`data_*.py` modules), never from user-supplied input.

---

## 4. Priority order

1. **XS, do first:** dev-cookie `secure=` flag (#2), prod session-secret guard (#3) — one line each,
   both close a real (if currently mitigated by other layers) gap.
2. **S:** `_claims_cache` TTL eviction (#1), chat endpoint rate limit (#4).
3. **S:** usage-event pagination on the admin Usage page, matching what §5.24 already did for
   Users/Audit (#5).
4. **M, schedule deliberately — don't bundle with unrelated work:** split `admin/routes.py` (#6).
5. **Skip unless client count grows past ~30:** the `dashboard_owner_map`/`operator_slugs` caching
   (#7) — premature against a target that isn't close.

Items in `dashboards/amazon_2026/IMPROVEMENT_PLAN.md` that bear on this same scope and remain open,
not duplicated here: **T1.2** (`--min-instances=1`, a cost decision, not code), **T1.3** (create the
`amazon` `Client` record + scope BigQuery IAM — an ops action), and the admin panel's still-open
reverse "who can access dashboard X" view and access-request notifications (end of §5.24).

No code was changed as part of this audit.
