# Native Analytics — Multi-tenant Vizro Dashboard Platform

A multi-tenant analytics platform built on [Vizro](https://vizro.readthedocs.io/)
(Dash/Plotly/Flask), designed to run on **Google Cloud Run**. Users sign in,
each user sees only the dashboards they have been granted, admins manage access,
and dashboards pull data from **BigQuery** with per-client data isolation.

## Key capabilities

- **Authentication** via Firebase / Identity Platform, toggleable with a single
  env var (`AUTH_ENABLED`) so local development needs no login.
- **Per-user dashboard access** — the Client Hub lists only the
  dashboards a user may open; a request gate blocks everything else.
- **Admin panel** — manage users, clients (tenants) and dashboard grants.
- **Plugin dashboards** — drop a folder under `dashboards/<slug>/` and it is
  auto-discovered. No central registration.
- **BigQuery integration** with per-client dataset isolation and an offline
  fixture fallback for fast local work.

## Architecture

```
            ┌────────────────────── Cloud Run (one container) ──────────────────────┐
Browser ──► │  Flask server (created by Vizro)                                       │
            │   /            Client Hub  (pages_landing)                              │
            │   /login,/logout, /sessionLogin       (Firebase session cookies)       │
            │   /admin/*     admin panel            (admin blueprint)                 │
            │   before_request gate → auth + per-dashboard access check               │
            │   /app/*       ONE Vizro app with ALL dashboards' pages                 │
            │                  /app/d/<slug>  ← one page per dashboard plugin         │
            └────────────┬───────────────────────────────┬──────────────────────────┘
                         │                                │
                  Firestore (users,              BigQuery (one dataset
                  clients, grants)                per client)
```

> **Why one Vizro app for everything?** Dash's page registry is process-global
> and every Vizro `Dashboard` claims path `/`. Running multiple Vizro apps in one
> process collides. So all dashboards contribute pages to a single Vizro app
> mounted under `/app/`, leaving `/` free for our own pages.

### Project layout

```
app.py                  # entry: builds the Vizro app, mounts blueprints, access gate
config.py               # env-driven settings (pydantic-settings)
auth/                   # firebase.py, middleware.py, dev_users.py
tenancy/                # models.py, users.py (Firestore/in-memory), access.py
data_sources/           # bq.py (BigQuery), fixtures.py (offline data)
dashboards/             # plugin packages, auto-discovered
  _base.py              #   DashboardManifest + BuildContext
  __init__.py           #   discover_dashboards()
  timeline/             #   reach & engagement (synthetic data)
  breakdown/            #   narrative breakdown (synthetic data)
  bq_sample/            #   BigQuery-connected sample
pages_landing/          # Client Hub/login/logout routes + shared HTML shell
admin/                  # admin panel (users / clients / grants)
tests/                  # pytest suite
Dockerfile              # Cloud Run image
cloudbuild.yaml         # build + deploy pipeline
.devcontainer/          # VS Code Dev Container (mirrors the prod image)
```

## Local development

The fastest path uses no GCP at all: auth off, in-memory fixture users, and a
BigQuery fixture fallback.

### Option A — venv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env       # AUTH_ENABLED=false by default
python app.py                     # → http://127.0.0.1:8050
```

### Option B — Dev Container (recommended)

Open the folder in VS Code and choose **Reopen in Container**. The container
mirrors the Cloud Run image and mounts your host `gcloud` credentials so real
BigQuery works. Run `gcloud auth application-default login` on the host first if
you want live BigQuery.

### What you get in dev mode

- `AUTH_ENABLED=false` → every request is the fixture **Dev Admin**, so all
  dashboards and the admin panel are reachable instantly.
- Fixture users/clients (see `auth/dev_users.py`) let you exercise the admin
  grant workflow.
- The `bq_sample` dashboard falls back to a local fixture when BigQuery is
  unreachable.

### Tests

```powershell
python -m pytest -q
```

## Adding a new dashboard

1. Create `dashboards/<slug>/__init__.py` exposing two things:

   ```python
   import vizro.models as vm
   from dashboards._base import BuildContext, DashboardManifest

   MANIFEST = DashboardManifest(
       slug="<slug>",                 # MUST equal the folder name
       title="My Dashboard",
       description="What it shows.",
   )

   def build_pages(ctx: BuildContext) -> list[vm.Page]:
       return [vm.Page(title=MANIFEST.title, path=MANIFEST.base_path,
                       components=[...])]
   ```

2. Use unique Vizro component `id`s across the whole app (Vizro enforces global
   uniqueness). Page paths **must** be `/d/<slug>` via `MANIFEST.base_path`.
3. For BigQuery-backed dashboards, add a `data.py` that registers a loader with
   Vizro's `data_manager` (see `dashboards/bq_sample/`). Use
   `data_sources.bq.safe_query(sql, fallback=...)` for graceful local dev.
4. Restart the app. The dashboard is auto-discovered, appears in the admin grant
   UI, and shows in the Client Hub once granted.

### Responsive Plotly charts in cards

For charts inside custom flex/grid cards, make the whole sizing chain shrinkable:
use `dcc.Graph(responsive=True, style={"width": "100%", "height": "...", "minWidth": 0})`,
set Plotly `layout.autosize=True` with `width=None` and `height=None`, and add
`min-width: 0` to the card, grid item, and graph wrapper. Vizro/Dash layouts can
otherwise keep a content-based minimum width and the Plotly SVG will overflow the
card. For donut charts with outside labels, keep `automargin=True`.

## Authentication & tenancy

- **Toggle:** `AUTH_ENABLED=true` enables Firebase. Set `FIREBASE_API_KEY`,
  `FIREBASE_AUTH_DOMAIN`, `GCP_PROJECT_ID`. On Cloud Run, the Firebase Admin SDK
  uses the service account's Application Default Credentials.
- **User store:** Firestore collections `users` and `clients` in production;
  an in-memory fixture store in dev. Same `UserStore` interface either way.
- **Roles:** `admin` (all dashboards + admin panel) and `user` (only granted
  dashboards, scoped to one `client_id`).
- **Data isolation:** each client maps to its own BigQuery dataset
  (`{BQ_DATASET_PREFIX}{client_id}`, or an explicit override on the client
  record). `tenancy.access.resolve_client_dataset()` resolves it at query time.

## Deploy to Cloud Run

Prerequisites: an Artifact Registry repo, Identity Platform enabled, a
`na-session-secret` in Secret Manager, and the Cloud Run service account granted
`roles/datastore.user` plus read access to the client BigQuery datasets.

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=europe-west1,_SERVICE=na-dashboards
```

The image runs `gunicorn app:server`. Secrets and env vars (including
`AUTH_ENABLED=true`) are injected by Cloud Run — never bake them into the image.

## Dependencies

- [Vizro](https://github.com/mckinsey/vizro) — low-code dashboards on Dash/Plotly
- Flask · gunicorn — web serving
- firebase-admin · google-cloud-firestore — auth & user store
- google-cloud-bigquery — data
- pydantic-settings — configuration

Python 3.11+.
