# Style & UX Improvement Plan

> Analysis of the app's visual style (light + dark mode), the styling-file architecture,
> and overall UI/UX. Written 2026-07-02 from direct reads of `assets/*.css`,
> `dashboards/amazon_2026/theme.py`, `ui_components.py`, `STYLE_GUIDE.md`,
> `IMPROVEMENT_PLAN.md`, `app.py` and the shell/admin CSS. **Plan only — nothing here
> is implemented.**

---

## 1. Current state — what is already good

Worth stating so it doesn't get "improved" away:

- **Token system.** `--na-*` custom properties in `assets/native_analytics.css` are a real
  single source of truth: one `:root` block (light), one `[data-bs-theme="dark"]` override
  block, and Python chart code consumes them as `var(--na-*)` strings via `theme.py`'s
  `THEME_*` constants. Page CSS files are almost fully tokenized — a repo grep finds only
  ~10 hardcoded color literals across all `amazon_2026_*.css` files, most of them deliberate.
- **Plotly re-theming.** The `!important` SVG-override block (gridlines, ticks, legends,
  hover labels) that keeps charts in sync with live theme toggles is hard-won and thoroughly
  documented (STYLE_GUIDE §6), including the `stroke-opacity` and `var()`-in-trace gotchas.
- **Component consistency.** `na_panel` (panel/outline/flat), `_kpi_card`, one typography
  scale, one sentiment palette, one Trad/SoMe accent pair — the dashboard pages look like
  one product.
- **Loading UX.** Per-figure reserved min-heights + branded spinner mean no layout jump and
  no spinner pile-up at the top of the page.
- **Dark mode is genuinely tuned.** The `#111827 / #1b212b / #202631` surface ramp,
  0.92-alpha text, 0.10–0.12 alpha grid/borders were iterated deliberately (STYLE_GUIDE
  gotcha 3b). Dark mode is the designed mode.

---

## 2. Light mode — why it looks worse, and what to change

Dark mode got a hand-picked surface ramp and per-theme alpha tuning. Light mode inherits
Bootstrap defaults and the *dark* mode's design decisions. Four structural causes:

### 2.1 No surface hierarchy (the biggest problem)

Light mode: page background `#ffffff` (`--bs-body-bg`), panels `#f8f9fa`
(`--na-surface-alt`). That's a ~3% luminance difference — panels are visually
indistinguishable from the page, so **everything is border-defined, nothing is
surface-defined**. The page reads as a flat wireframe of gray boxes.

Dark mode has the opposite (correct) relationship: a designed 3-step ramp with clearly
separated body / panel / hover surfaces.

**Fix — design a real light ramp, mirroring the dark one:**

| Token | Now (light) | Proposed | Rationale |
|---|---|---|---|
| page bg (`--na-surface`) | `#ffffff` | `#f2f4f7` (cool light gray, matches dark ramp's blue-gray cast) | tinted canvas |
| `--na-surface-alt` (panels) | `#f8f9fa` | `#ffffff` | **invert the relationship**: white cards on a tinted page — the standard light-dashboard pattern (Grafana, Looker, Tableau all do this) |
| `--na-surface-hover` | `#edf1f5` | `#f0f4f8` | hover slightly below panel white |
| panel elevation | none | `box-shadow: 0 1px 2px rgba(16,24,40,0.05)` on `.na-panel`, **light mode only** | dark mode separates surfaces by lightness; light mode needs subtle elevation instead |

Note: this means `--na-surface` can no longer alias `--bs-body-bg` blindly — either set
the Bootstrap body-bg variable too, or hardcode (the guide already established that
`--bs-*` fallthroughs are unreliable, see gotcha 1 in STYLE_GUIDE §6).
`--na-row-even/odd`, `--na-header-bg`, `--na-kpi-group-bg` all derive from these two
tokens and will follow automatically — verify table zebra striping still reads correctly
after the swap (white rows / `#f7f9fb` alt rows on a white panel is fine).

### 2.2 Borders and gridlines never got light-mode tuning

STYLE_GUIDE gotcha 3b says it explicitly: *"light and dark each need their own tuning"* —
but only dark got the second pass (borders lowered to 0.10–0.12). Light mode still runs:

- `--na-border: rgba(33,37,41,0.18)` — visibly heavier than dark mode's 0.12
- `--na-grid: rgba(33,37,41,0.16)` — chart gridlines look wiry/busy on white

**Fix:** lower light-mode `--na-border` to ~`0.12–0.14` and `--na-grid` to ~`0.10–0.12`.
With the surface ramp from 2.1 carrying more separation, borders can recede.

### 2.3 Hardcoded dark-mode values that are *bugs* in light mode

Concrete, file-level defects (each is a one-line fix):

| Location | Defect | Effect in light mode |
|---|---|---|
| `assets/native_analytics.css` `a.back-to-panel:hover` (~line 249) | `color: #fff` on hover | "Back to panel" header link turns **white-on-light = invisible** on hover |
| `assets/native_analytics.css` `a.back-to-panel` (~line 240) | border fallback `#444`, `--border-subtle-alpha-01` is a Vizro-dark token | wrong-weight border; use `--na-border` |
| `assets/native_analytics.css` `.na-dev-inline-label` (~line 273) | fallback `rgba(255,255,255,0.75)` | near-invisible label if `--bs-secondary-color` unresolved; use `--na-text-muted` |
| `assets/amazon_2026_narratives.css:219` | `color: var(--text-primary, #e5e7eb)` | narrative description text can render pale-gray-on-white; should be `var(--na-text)` |
| `assets/amazon_2026_discover.css:228` | `box-shadow: ... rgba(0,0,0,0.35)` | heavy smudge under light UI; tune per theme (~0.12 light) |
| `assets/amazon_2026_overview.css:143–156` + `ui_components.py::TOOLTIP_CSS` | table tooltips forced dark `#111827` | documented as deliberate (STYLE_GUIDE §11.2), but **inconsistent**: Plotly hover labels on the same page are theme-aware (`--na-surface`), so light mode shows two different tooltip styles side by side. Recommend making TOOLTIP_CSS token-based too — `--na-surface`/`--na-text` already guarantee contrast in both themes |
| `assets/ext_chat.css:75,121` | `.ext-chat-user` / `.ext-chat-send`: `background: var(--na-link); color: #fff` | fine in light (`#0d6efd` bg) but **broken in dark**: `--na-link` is pale `#9fd1ff` → white-on-pale-blue, unreadable. Needs a paired `--na-accent-contrast` token or a solid accent token that works as a fill in both themes |
| `assets/amazon_2026_discover.css:342` | similarity gradient hardcodes 5 hexes | acceptable (data encoding), but document it as a deliberate exception in STYLE_GUIDE §11 |

### 2.4 Chart internals tuned only against dark

- `theme.py` comments call `TOPIC_AREA_PALETTE` "dark-mode-friendly" — nobody has audited
  it against white panels. Most entries are mid-saturation and fine; verify the light ones
  (`#D3B745` yellow, `#8FCB7E`, `#E7969C`) still separate from a white background.
- Donut/pie **inside-slice text is hardcoded white** (STYLE_GUIDE §6). On light/yellow
  slices (`#D3B745`, `#E6B450`, `#8FCB7E`) white 11px text fails contrast in *both* themes.
  Fix: per-slice text color by luminance threshold (dark text on light slices) — a small
  helper in `theme.py`, applied where `textfont=dict(color="white")` is set today.
- Venn "Trad"/"SoMe" labels use Arial Black text traces — confirm they're covered by the
  `.textpoint` override (they are) but re-check fill alphas (0.28) on white; overlapping
  region may get too faint. Consider 0.34–0.38 in light mode via `--na-accent-*-fill`
  (these tokens already exist — the Python code should consume them instead of
  `hex_to_rgba` literals so they can differ per theme).

### 2.5 The shell (Client Hub / admin / sign-in) has no light mode at all

`assets/native_analytics_shell.css` is hardcoded dark (`color-scheme: dark`, `#0f1722`
gradient body, dark redefinitions of the same `--na-*` names). A user who toggles the
dashboard to light mode then clicks "Back to panel" gets slammed into a dark hub.

**Decision needed (recommendation: Option A):**
- **A — Keep the shell dark-only, on purpose.** Cheapest; dark hub as a "brand frame" is
  defensible. Then remove ambiguity: rename the shell's token copies (see §4.2) and accept
  the transition.
- **B — Theme the shell.** Port the shell to the same light/dark token pairs and sync via
  the same `localStorage` key Vizro uses for the dashboard toggle. More work: the shell's
  gradients/glows/shadows are all dark-designed.

---

## 3. Dark mode — minor findings

Dark mode is in good shape. Only:

1. `ext_chat.css` white-on-`--na-link` contrast bug (see table above — this is primarily a
   dark-mode defect).
2. The loader SVG `filter: invert(1)` trick is fragile (inverts hue, not just lightness).
   Works today because the logo is gray; will silently break if the logo gains brand color.
   Low priority; note it in the guide.
3. Discover row highlight uses `--bs-primary-bg-subtle` (clientside callback) while the
   token system defines `--na-row-selected` for exactly this purpose (STYLE_GUIDE §1 says
   `--na-row-selected` is for "clicked/selected row highlight (Discover results tables)").
   Two sources of truth for one state — pick `--na-row-selected`.

---

## 4. Styling architecture — assessment and changes

### 4.1 Verdict

The architecture is **fundamentally sound**: tokens → shared component classes →
page-scoped CSS files, with Python chart constants pointing at the same tokens. The
layering (`theme.py` → `timeline_charts.py` → `ui_components.py`, one-way) is clean after
the §5.4 split. Two structural debts remain:

### 4.2 The `--amazon-publishers-*` alias layer and `.amazon-publishers-*` class names

Twenty tokens in `native_analytics.css` exist only to alias `--na-*` under a legacy name,
and — worse — the *class* namespace `.amazon-publishers-*` is used on every page
(Overview KPIs, Narratives grids, Discover dropdowns all carry "publishers" class names).
This misleads every new reader and doubles the token vocabulary.

**Fix (mechanical, medium-sized, zero visual change):**
1. Rename classes `.amazon-publishers-*` → `.na-*` (e.g. `.na-kpi`, `.na-dropdown`,
   `.na-control-label`, `.na-section-header`) across `ui_components.py`, `charts_*.py`,
   `pages/*.py` and the CSS files.
2. Delete the alias `:root` block.
3. Update STYLE_GUIDE tables.
Do it as one dedicated pass (grep-driven), not incrementally — a half-renamed namespace is
worse than a consistently wrong one.

### 4.3 Shell token duplication

`native_analytics_shell.css` redefines `--na-text`, `--na-surface`, etc. with *different
values* than the dashboard's dark theme file. Same names, two meanings, only safe because
of `assets_ignore` — one refactor away from a collision. Either:
- extract a shared `tokens.css` both load (needed anyway if §2.5 Option B is chosen), or
- prefix the shell's copies (`--shell-*`) if the shell stays dark-only (Option A).

### 4.4 Accent color fragmentation

Four different "brand blues" in play: shell `--accent: #4a6cf7`, light link `#0d6efd`
(Bootstrap default), dark link `#9fd1ff`, chart accent `#2f7dd1`. The hub, the header
hover, dashboard links, and charts each pick a different blue.

**Fix:** declare one brand accent pair in the tokens
(`--na-accent` + `--na-accent-contrast`, light/dark tuned — `#4a6cf7` family is the most
"branded" candidate), point `--na-link` and the shell `--accent` at it. Keep
`--na-accent-trad` separate on purpose (it's a *data* color, not a brand color) — document
that distinction.

### 4.5 File layout — keep as is

One tokens+chrome file (`native_analytics.css`), one file per page, one per extension is
the right granularity. Don't introduce a build step / SCSS — plain CSS custom properties
are doing the job. The only file worth splitting is `native_analytics.css` *if* it keeps
growing: `na_tokens.css` (tokens only) + `na_chrome.css` (Plotly overrides, header,
loading). Optional, low value today.

### 4.6 STYLE_GUIDE.md drift (documentation is part of the architecture)

The guide is excellent but has drifted from the working tree:

| Guide says | Reality |
|---|---|
| `charts_shared.py::na_panel`, `THEME_*` in `charts_shared.py` (7 mentions) | `charts_shared.py` was deleted (IMPROVEMENT_PLAN §5.4); names live in `theme.py` / `ui_components.py` / `timeline_charts.py` |
| §1 table: sentiment `#2ca02c / #1f77b4 / #d62728` | actual tokens: `#3f9d5c / #4a8fc2 / #d9534f` (§4a of the same doc has the correct values — the doc contradicts itself) |
| §4c: "`DONUT_COLORS` (10-color cycle)" | 8 colors; the 10-color set is `NARRATIVE_LINE_COLORS` |
| `_hex_to_rgba` | renamed `hex_to_rgba` |

**Fix:** one doc pass. Also add the §11 exceptions found in this audit (Discover gradient,
loader invert). The standing memory rule ("always update STYLE_GUIDE.md on styling
changes") should be extended to renames/refactors, which is where this drift came from.

---

## 5. UI / UX assessment

### 5.1 What works

Real, above-baseline UX care is visible: instant clientside row highlight, `uirevision`
preserving pan/zoom across filter changes, session-persisted detail selections, reserved
loading heights, saved views, per-dashboard scoped nav rail, collapsible UMAP panel to
protect initial load time, "Use as reference" similarity flow.

### 5.2 Issues and improvements (ranked)

1. **Theme continuity.** Vizro defaults to dark; the toggle isn't reflected in the shell
   (§2.5) and light mode is the weaker theme — so users who prefer light get the worst
   version of the product on every surface. Fixing §2.1–2.3 is the single highest-impact
   UX improvement. Also verify the theme choice persists across dashboards/sessions
   (Vizro stores it; confirm it survives the hub round-trip).
2. **Feature discoverability.**
   - The chart context menu (⋮) is invisible until panel hover, **Overview-only**
     (`#amazon-2026-overview` selector), yet its global ON/OFF pill floats on *every* page.
     Either roll it out to all pages (the injection is generic already) or scope the toggle
     pill to Overview. The floating "Chart Menu ON/OFF" pill itself is developer UX, not
     product UX — long-term it belongs in a settings/kebab affordance, not fixed viewport
     chrome.
   - Lasso/box-select filtering on the UMAP is powerful but discoverable only via a hint
     line + hidden modebar. Consider a small explicit "Select" button in the panel header
     that activates lasso mode.
3. **Error vs. empty states** — already tracked as IMPROVEMENT_PLAN §5.17 (open half):
   "no data" and "query failed" render identically. From a user-trust standpoint this is
   the most serious open UX item on the list; re-prioritize it alongside this plan.
4. **Accessibility.**
   - Focus visibility: Dash table focus rings are deliberately suppressed (STYLE_GUIDE §7)
     and several custom buttons/toggles have `outline: none` focus treatment via border
     color only. Add `:focus-visible` styles (2px accent outline) to interactive chrome:
     mode tabs, clear-filters, UMAP toggle, chart-menu button, pagination.
   - Text sizes/contrast: 12px is the workhorse size for labels, captions, table cells;
     `--na-text-soft` at 0.58 alpha on 12px text is below WCAG AA in both themes. Bump
     soft-text usage at 12px to `--na-text-muted`, or raise soft to ~0.65.
   - White inside-slice chart text on light slices (see §2.4).
5. **Information density vs. hierarchy on Discover.** The page stacks Filters (2-row
   controls grid + search row) → collapsible UMAP → Results → Detail. It's the most
   complex page and mostly earns it, but: the results table and detail panel compete
   below the fold, and selecting a row gives no scroll affordance to the detail panel.
   Consider auto-scrolling the detail panel into view on first row click (respecting
   `prefers-reduced-motion`), or a side-by-side layout ≥1400px.
6. **Consistency nits.** Border radii vary between the dashboard (8px) and shell
   (10/12/14/18px pills and cards) — fine across products, but pick one radius scale if
   the shell is ever re-themed. `.na-element-title` at 16px vs section header 22px is a
   good scale; the shell's `clamp(34–54px)` hero is its own world (acceptable).

---

## 6. Prioritized roadmap

**Tier 1 — light-mode repair (small, high impact, do first)**
1. Fix the outright bugs: `back-to-panel:hover` white text, narratives `--text-primary`
   fallback, dev-label fallback, ext-chat contrast pair (§2.3 table). *(~6 one-line edits)*
2. Light surface ramp + panel elevation (§2.1) and light border/grid alpha tuning (§2.2).
   This is a token-only change — verify with both themes on Overview, Publishers,
   Discover.
3. Make `TOOLTIP_CSS` theme-aware (§2.3, tooltip row).
4. Update STYLE_GUIDE.md (§4.6 drift + new decisions), per the standing rule.

**Tier 2 — consistency and architecture**
5. Single brand accent pair; repoint `--na-link` and shell `--accent` (§4.4).
6. Decide shell theming (Option A recommended) and de-duplicate shell tokens (§2.5, §4.3).
7. `.amazon-publishers-*` → `.na-*` rename pass, delete alias token block (§4.2).
8. Discover row-highlight → `--na-row-selected` (§3.3).

**Tier 3 — UX polish**
9. `:focus-visible` styles + 12px soft-text contrast bump (§5.2.4).
10. Luminance-aware inside-slice text color helper (§2.4).
11. Chart menu: all pages or Overview-only toggle; rethink the floating pill (§5.2.2).
12. Discover detail-panel scroll affordance (§5.2.5).
13. Light-mode audit of `TOPIC_AREA_PALETTE` / Venn fill alphas against white panels (§2.4).

**Explicitly not proposed** (YAGNI): CSS preprocessor/build step, component library
migration, splitting `native_analytics.css`, theming the demo dashboards, redesigning the
dark theme (it's good).
