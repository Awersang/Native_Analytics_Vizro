# How to set up & operate this app

`README.md` is for developers (how to run the code). This file is for whoever
**operates the live app** day-to-day: onboarding a new client, creating users,
granting dashboard access. No code changes needed for any of this — it's all
admin-panel clicks — but the clicks only make sense once you know the model
underneath them.

## 1. The four building blocks

Everything in this app is built from four ideas. Get these straight and every
admin-panel screen is self-explanatory.

```
Dashboard  ──  a bespoke product (e.g. "amazon_2026"). One folder of code,
               built for ONE client. Not a template — a second client never
               reuses another client's dashboard build.

Client     ──  a tenant / company (e.g. "Amazon"). Owns:
                 - a BigQuery dataset (their data, isolated from everyone else)
                 - a list of dashboard slugs it's allowed to open

User       ──  one login. Belongs to at most one Client (`client_id`).
               Automatically inherits every dashboard slug their Client owns.
               Can also get a few EXTRA per-user dashboard slugs on top.

Grant      ──  not a separate object — it's just "this slug is in a Client's
               or User's list". Granting/revoking access = editing that list.
```

Two roles sit on top of this:
- **admin** — bypasses all of the above, sees every dashboard + the `/admin`
  panel itself. Reserved for staff who run the platform.
- **user** — everything above applies. Most people, including every client's
  staff, are `user`.

There's a third, informal pattern worth knowing: an **operator** — internal
staff who service several clients but shouldn't be a full admin. You make one
by creating a `user` with **no Client** (`client_id` empty) and a hand-picked
list of per-user dashboard slugs spanning whichever clients they support. See
§5.

### Why this shape, specifically

- A Client's data lives in its own BigQuery dataset. Because dashboards are
  bespoke (one build per client), there's no shared query layer that could
  leak rows between clients by accident — the isolation is structural, not a
  permissions check that could be forgotten in one query.
- Access is **company-first**: grant the dashboard to the Client, and every
  user at that company gets it for free, forever, with zero per-user admin
  work. Per-user grants exist only for the exception (one extra dashboard for
  one specific person), not as the default way to grant access.

## 2. The map: what's where

| URL | Who sees it | What it's for |
|---|---|---|
| `/` | anyone logged in | Client Hub — cards for every dashboard *they* can open |
| `/account` | anyone logged in | their own profile and the dashboards they can access |
| `/login`, `/logout` | everyone | Firebase sign-in (skipped entirely when `AUTH_ENABLED=false`) |
| `/app/d/<slug>` | anyone granted `<slug>` | the actual dashboard (Vizro pages) |
| `/admin` | admins only | the screens below |
| `/admin/clients` | admins | create clients, set their BigQuery dataset, assign dashboards |
| `/admin/users` | admins | create users, set their Client, set per-user extra grants |
| `/admin/audit`, `/admin/usage` | admins | who did what, who opened what |
| `/admin/health` | admins | per-dashboard data-source health check |

## 3. Onboard a new client (dashboard already built for them)

Use this when the dashboard product already exists (e.g. a second instance of
a dashboard type you've built before, pointed at a new client's own data).

1. **Confirm the dashboard's data layer is wired to the new client**, not
   copy-pasted from whoever it was built for last. Every dashboard package
   has its own hardcoded-or-resolved dataset reference (see
   `dashboards/<slug>/data_common.py` for the pattern, and the checklist at
   the top of `dashboards/_base.py`). Get this right *before* step 2 — it's
   the one step that's a code/config change, not an admin click, and the one
   mistake that actually crosses a tenant boundary.
2. **`/admin/clients` → "Add client"**: pick an `id` (short, lowercase,
   no spaces — this is a permanent key, not just a label), a display `name`,
   and the `BQ dataset` field if their dataset name doesn't follow the
   `{prefix}{id}` convention (it usually won't for a one-off build — set it
   explicitly).
3. **Same page, that client's row → "Dashboards"**: select the dashboard
   slug(s) they should see, **Save**. This is the actual access grant — every
   user you put under this Client inherits it automatically from here on.
4. **`/admin/users` → "Add user"**: set `email`, the Firebase `uid` (see the
   note below if you don't have one yet), `role = user`, and `Company` = the
   client you just created. They now see exactly that client's dashboard(s),
   nothing else.
5. **Verify**: log in as that user (or, in dev, use the "View as" switcher) and
   confirm the Client Hub shows only their dashboard, and the dashboard shows
   only their data.

**Don't have a Firebase UID yet?** Set `AUTO_PROVISION_USERS=true` (env var)
and have the person log in once — they're auto-created with zero access, then
you just set their Company in step 4 (skip the "Add user" form entirely).

## 4. Onboard a new client that needs a brand-new dashboard build

Same as §3, but step 1 is "build the dashboard" rather than "fix a constant."
See `README.md`'s **Adding a new dashboard** section for the code-level
how-to (folder layout, `MANIFEST`, `build_pages`). Once the package exists and
its data layer points at the right BigQuery dataset, steps 2–5 above are
identical.

## 5. Create an operator (internal staff, multiple clients)

1. **`/admin/users` → "Add user"**: leave `Company` set to **— none —**.
2. **`/admin/users`**, that user's row → the per-user grants control: tick
   every dashboard slug they need across whichever clients they support.
   (They will **not** auto-inherit a client's future dashboards the way a
   real Client user does — each slug here is a manual pick. If an operator's
   list of clients changes often, that's a known, deliberately-deferred
   convenience gap, not a bug.)
3. They now see a Client Hub mixing dashboards from several clients, can open
   each one, and — because every dashboard is single-client by construction
   (§1) — there is no path for them to see two clients' data blended on one
   screen even by accident.

Keep operators as `role = user`, not `admin` — admin sees the admin panel
itself and every dashboard unconditionally, which is more than an operator
needs.

## 6. Day-2 operations

- **Revoke a dashboard from a whole client**: `/admin/clients`, deselect the
  slug in their "Dashboards" box, Save. Every user at that company loses
  access immediately on their next request.
- **Revoke just one person's extra grant**: `/admin/users`, edit their
  per-user grants.
- **See who did what**: `/admin/audit` (admin actions) and `/admin/usage`
  (who opened which dashboard, when).
- **Check a data source is alive**: `/admin/health`.

## 7. What "data isolation" does and doesn't guarantee

- **Does**: each dashboard's code queries one specific BigQuery dataset,
  resolved from that one client's `Client.bq_dataset` record (or a safe
  hardcoded fallback if that record doesn't exist yet — see §3 step 1's
  link). Two different clients are never read by the same dashboard build.
- **Doesn't, by itself**: stop someone from *building* dashboard #5 by
  copy-pasting dashboard #2 and forgetting to repoint a constant at the new
  client's dataset. That's a one-time code-review step (§3 step 1), not
  something the admin panel can catch for you.
- **Belt-and-suspenders, not yet wired**: scoping the BigQuery credentials
  themselves so a missed step-1 mistake fails with a permissions error
  instead of silently returning the wrong client's rows. Infra-level, tracked
  as a follow-up — ask whoever owns `cloudbuild.yaml` / the service account.

## 8. Troubleshooting

| Symptom | Likely cause |
|---|---|
| User logs in, Client Hub is empty | No `Company` set on the user, and no per-user grants either |
| User sees the hub card but gets 403 opening it | Slug typo somewhere, or the Client's "Dashboards" list doesn't actually include that slug — check `/admin/clients` |
| New client's dashboard shows another client's numbers | The dashboard's data layer still points at the old dataset — see §7 "doesn't guarantee" |
| Admin panel itself is unreachable | You're not `role = admin` — check `/admin/users` |
| Nothing requires login at all | `AUTH_ENABLED=false` (normal for local dev) — every request is the fixture Dev Admin |
