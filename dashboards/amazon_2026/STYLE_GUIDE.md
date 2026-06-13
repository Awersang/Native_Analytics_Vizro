# Amazon 2026 Dashboard — Style Guide (as implemented)

This documents the unified style system implemented per `STYLE_PLAN.md`.
It supersedes the pre-implementation audit that used to live here.

---

## 1. Design tokens (`--na-*`)

Single source of truth: `assets/native_analytics.css`, declared once on
`:root` (light) with overrides under `[data-bs-theme="dark"]`. Covers the
Overview, Narratives and Publishers pages.

| Token | Light | Dark | Used for |
|---|---|---|---|
| `--na-text` | `#212529` | `rgba(235,241,250,0.92)` | titles, headers, KPI values, axis titles, legends, annotations |
| `--na-text-muted` | `rgba(33,37,41,0.72)` | `rgba(235,241,250,0.72)` | labels, captions, group titles, axis tick numbers |
| `--na-text-soft` | `rgba(33,37,41,0.58)` | `rgba(235,241,250,0.58)` | secondary captions |
| `--na-border` | `rgba(33,37,41,0.18)` | `rgba(247,249,252,0.12)` | all box borders, axis lines, tick marks |
| `--na-surface` | `var(--bs-body-bg, #ffffff)` | `#111827` | card/KPI/page backgrounds |
| `--na-surface-alt` | `var(--bs-tertiary-bg, #f8f9fa)` | `#1b212b` | panel/section backgrounds |
| `--na-surface-hover` | `var(--bs-secondary-bg, #edf1f5)` | `#202631` | hover states |
| `--na-row-even` / `--na-row-odd` | surface / surface-alt | same | table zebra striping |
| `--na-header-bg` | = surface-alt | = surface-alt | table header background |
| `--na-grid` | `rgba(33,37,41,0.16)` | `rgba(247,249,252,0.1)` | Plotly gridlines |
| `--na-dropdown-bg` / `--na-dropdown-hover` | surface / surface-hover | same | `dcc.Dropdown` |
| `--na-link` | `var(--bs-link-color, #0d6efd)` | `#9fd1ff` | clickable cells/links |
| `--na-kpi-group-bg` | = surface-alt | = surface-alt | KPI panel background |
| `--na-avatar-bg` | `var(--bs-primary-bg-subtle, #dfe7f3)` | `#283645` | author avatar box |

Categorical tokens (theme-independent, also defined in `:root`):

| Token | Hex | Meaning |
|---|---|---|
| `--na-sentiment-positive` | `#2ca02c` | Positive sentiment (charts + table data-bars) |
| `--na-sentiment-neutral` | `#1f77b4` | Neutral sentiment |
| `--na-sentiment-negative` | `#d62728` | Negative sentiment |
| `--na-accent-trad` | `#2f7dd1` | Trad (blue) accent — Overview source bars, Venn, data-bar trad-publications |
| `--na-accent-some` | `#d98933` | SoMe (orange) accent — Overview source bars, Venn, data-bar some-posts |
| `--na-accent-trad-fill` / `--na-accent-some-fill` | `rgba(47,125,209,0.28)` / `rgba(217,137,51,0.28)` | Venn fill colors |
| `--na-bar-trad-publications` ... `--na-bar-some-average` | see `:root` | table data-bar gradient palette |

### Page-scoped aliases

Each page declares an `--amazon-publishers-*` alias block (under its own page
container id: `#amazon-2026-overview`, `#amazon-2026-narratives`,
`#amazon-2026-publishers`) mapping every `--amazon-publishers-*` name used by
shared Python components (`charts_shared.py`'s `THEME_*` constants, `_kpi_card`,
`na_panel`, table styles, etc.) to the corresponding `--na-*` token. This keeps
existing component code working unchanged while resolving to the single token
set.

---

## 2. Box styles — `na_panel`

`charts_shared.py::na_panel(title, children, *, box="panel" | "flat", controls=None)`
is the single shared wrapper for charts, tables, and KPI groups:

```python
def na_panel(title, children, *, box="panel", controls=None) -> html.Div:
    ...
```

| Style | Class | Look |
|---|---|---|
| `panel` (default) | `.na-panel` | `border: 1px solid var(--na-border)`, `border-radius: 8px`, `background: var(--na-surface-alt)`, `padding: 18px`, `gap: 14px` |
| `flat` | `.na-panel.na-panel--flat` | no border/background/padding — content sits directly on the page |

Both render an optional `.na-element-title` div (16px / 600 / `--na-text`)
above the content when `title` is truthy.

`_analysis_card = na_panel` is kept as a backward-compatible alias (same
signature, `box="panel"`).

### Source-toggle controls (`controls=`)
Charts/tables with a Trad/SoMe `dcc.RadioItems`/`dcc.Checklist` source toggle
(P2S2G1, P2S4G1, P2S4G2, P3S2G2/G3, P3S2G4, P3S2T1) pass it via `controls=`
rather than embedding it in `children`. `na_panel` then renders title +
controls together in a `.na-panel-header` flex row — title on the left,
controls top-right, `space-between`, **no separator line**:

```python
return na_panel(
    ref_label("Chart title", "P#S#G#"),
    [dcc.Store(...), dcc.Graph(...)],
    controls=html.Div(className="amazon-publishers-chart-controls", children=[dcc.Checklist(...)]),
)
```

When a chart has only one available source, pass
`controls=html.Div(..., style={"display": "none"}, children=[...])` — the
hidden control collapses out of the header row and the title sits alone on
the left (P3S2G4, P3S2T1 already do this).

Charts that build their own header row manually (P2S2G1, P2S4G1) follow the
same visual pattern directly with an `html.Div(style={"display": "flex",
"alignItems": "center", "justifyContent": "space-between", "flexWrap":
"wrap", "gap": "8px"})` containing an `html.H3.na-element-title` and the
control — equivalent to what `na_panel(..., controls=...)` produces.

---

## 3. Typography

| Role | Class | Size / weight | Notes |
|---|---|---|---|
| Section header | `.amazon-publishers-section-header h2` | 22px / 700 | structural groupings ("Overview", "Details", "Narrative Details") |
| Element title (chart/table/panel) | `.na-element-title` | 16px / 600 | inside every `na_panel`, replaces old `.amazon-publishers-analysis-title` and ad-hoc `<h3>` |
| KPI group title | `.amazon-publishers-kpi-group-title` | 12px / 700 / uppercase | |
| KPI label | `.amazon-publishers-kpi-label` | 12px / 700 / uppercase | |
| KPI value | `.amazon-publishers-kpi-value` | 28px / 750 (24px compact) | |
| KPI caption | `.amazon-publishers-kpi-caption` | 12px / 400 | |

All Plotly `title=`/`title_font`/`title_y` have been removed from figure
layouts dashboard-wide (P1, P2, P3). Every chart's title now lives in
`.na-element-title`, owned by `na_panel`. Figure margins are tightened
(`t=12` typical) since the figure no longer reserves space for an in-canvas
title.

---

## 4. Color system

### 4a. Sentiment (canonical, `SENTIMENT_COLORS` in `charts_shared.py`)
| Sentiment | Hex |
|---|---|
| Positive | `#2ca02c` |
| Neutral | `#1f77b4` |
| Negative | `#d62728` |

Used for Plotly sentiment traces **and** the table data-bar
positive/negative columns (`--na-bar-positive` / `--na-bar-negative` alias
this same pair — the old separate `#35a66b`/`#c84e5a` pair is gone).

### 4b. Trad / SoMe accent pair (canonical, `ACCENT_TRAD` / `ACCENT_SOME` in `charts_shared.py`)
| Role | Hex |
|---|---|
| Trad (blue) | `#2f7dd1` |
| SoMe (orange) | `#d98933` |

Reused for:
- Overview "Publications and Posts" / sentiment-split bar charts (`pubs_posts_reach_by_source_panel`)
- Publisher overlap Venn diagram fills/strokes (`_hex_to_rgba(ACCENT_TRAD/ACCENT_SOME, 0.28)`)
- Table data-bars (`--na-bar-trad-publications`, `--na-bar-some-posts`)

(Previously three separate pairs: `#1f77b4`/`#ff7f0e` on Overview,
`#4ba3ff`/`#f0a03f` on the Venn, `#2f7dd1`/`#d98933` on data-bars.)

### 4c. Categorical / cycling palettes (unchanged, kept as-is)
- `MEDIA_TYPE_COLORS` (10 colors, Overview media-type donut)
- `PLATFORM_COLORS` (4 colors, Overview platform donut)
- `DONUT_COLORS` (10-color cycle, Publishers/Narratives mini-donuts and treemaps)

### 4d. Tooltips / hover labels — theme-aware everywhere
All `hoverlabel` (and the P2S2G1 custom legend, see §6) use:

```python
hoverlabel = dict(
    bgcolor=THEME_SURFACE,
    bordercolor=THEME_BORDER,
    font=dict(color=THEME_TEXT, size=...),
)
```

There is **no dark-only tooltip/legend** anywhere in the dashboard — the
previous hardcoded `#111827` / `rgba(255,255,255,0.18)` / `#f7f9fc` literals
in `charts_narratives.py` have been replaced with the theme tokens above.

---

## 5. KPI cards (`_kpi_card` helper, `charts_shared.py`)

Single reusable component: `<div class="amazon-publishers-kpi[ amazon-publishers-kpi-compact]">`
containing label / value / optional caption divs.

- **Standard** (`min-height: 96px`, value 28px) — Overview, publisher detail KPIs.
- **Compact** (`min-height: 0`, value 24px) — summary panels (Publishers
  overview, Narratives KPI grid).

**Overview page** (P1S1) now uses this component too (via `overview_kpi_panel`,
see §9), grouped into two `na_panel(box="panel")` containers — "Traditional
Media" (3 KPIs) and "Social Media" (2 KPIs) — matching the Publishers/
Narratives KPI box treatment. There is no longer a separate `vm.Card`-based
KPI style on Overview.

---

## 6. Charts (Plotly figures)

### Common conventions (all charts)
- `paper_bgcolor` / `plot_bgcolor`: `rgba(0,0,0,0)` (transparent)
- `font.color`: `THEME_TEXT`
- Gridlines: `THEME_GRID`
- Hover label: `THEME_SURFACE` / `THEME_BORDER` / `THEME_TEXT` (see §4d)
- No in-canvas `title` (see §3) — title lives in the surrounding `na_panel`
- Modebar hidden via `dcc.Graph(config={"displayModeBar": False, "responsive": True})`
  on every chart (the per-id CSS `.modebar { display: none }` allowlist in
  `amazon_2026_overview.css` is now redundant but harmless)

### Theming enforcement (CSS overrides)
Passing `THEME_TEXT`/`THEME_GRID`/etc. (`var(--na-*)` strings) into Plotly's
`font`/`gridcolor`/`hoverlabel` options is necessary but **not sufficient**:
Plotly bakes these into inline SVG styles/attributes at draw time and does
not reliably re-resolve them when `data-bs-theme` toggles afterwards, so a
chart first painted in one theme can stay "stuck" on that theme's colors
for axis ticks, axis titles, gridlines, axis/zero lines, legend text/box,
hover-label box/text, pie "outside" labels and `mode="text"` scatter labels
(e.g. the Venn "Trad"/"SoMe"/count labels).

To fix this, `assets/native_analytics.css` carries a dashboard-wide block of
`!important` rules targeting Plotly's standard SVG class hooks
(`.xtick > text`, `.ytick > text`, `.x2tick`/`.y2tick`, `.xtitle`/`.ytitle`/
`.x2title`/`.y2title`, `.legend .legendtext`, `.legend .bg`,
`.gridlayer .xgrid`/`.ygrid`/`.x2grid`/`.y2grid`, `.zerolinelayer path`,
`.xaxislayer-above path.domain`/`.yaxislayer-above path.domain`/`.x2.../.y2...`,
`.xtick.ticks`/`.ytick.ticks`/`.x2tick.ticks`/`.y2tick.ticks` (the tick-mark
lines, a separate `<path>` from the tick label `<text>`),
`.hoverlayer .hovertext .bg`/`text`, `.scatterlayer .textpoint text`,
`.outsidetextlayer text`, `.annotation-text`), bound to `--na-text` /
`--na-text-muted` / `--na-grid` / `--na-border` / `--na-surface`. Stylesheet
`!important` rules win over Plotly's inline styles and re-resolve `var()`
live on every theme change.

Within that block there's a deliberate text-weight hierarchy (titles can run
brighter than body text, but neither should be a glaring 100%-opacity
white-on-dark):
- `--na-text` (axis titles, legend entries, annotation/group labels like
  "Jan"/"Feb"/"Total", hover text, "outside" bar value labels) — the
  brightest tier. In dark mode this is `rgba(235,241,250,0.92)`, not a flat
  `#f7f9fc`/opacity-1 white, which read as too harsh against the dark
  surface.
- `--na-text-muted` (axis tick numbers only) — recedes behind titles/labels,
  `rgba(235,241,250,0.72)` in dark mode.

Three extra gotchas, found via headless-browser inspection (the standard
"is the rule winning?" check isn't enough — the *value* of the variable and
other baked-in properties also matter):

1. **`--na-text` / `--na-border` must be hardcoded, not `var(--bs-*, fallback)`.**
   `vizro-bootstrap.min.css` defines `--bs-body-color` and `--bs-border-color`
   multiple times for different DOM scopes (e.g. one `--bs-body-color` is a
   60%-opacity gray meant for secondary text). At `:root` scope this resolved
   to `rgba(20,23,33,0.6)` — so even with the `!important fill` rule winning,
   axis/legend/tooltip text rendered as a washed-out 60%-opacity gray. Both
   tokens are now hardcoded explicit values (see table above).
2. **`stroke-opacity`/`fill-opacity` are baked in as separate inline
   properties** alongside `stroke`/`fill` (Plotly's `tinycolor` split splits a
   color into an RGB triple + a separate opacity). Overriding `stroke` alone
   left the *old* theme's baked `stroke-opacity` (e.g. `0.078` from a
   dark-mode gridline) in place, multiplying against the new color's own
   alpha and making gridlines/tick-marks/axis lines nearly invisible. Every
   `stroke`-setting rule above also sets `stroke-opacity: 1 !important`, and
   the text rules set `fill-opacity: 1 !important`.
3. **Don't over-correct dark mode while fixing light mode.** An earlier pass
   hardcoded dark-mode `--na-border`/`--na-grid` at 0.18–0.2 alpha and
   `--na-text` at a fully-opaque near-white — this fixed light mode but made
   dark-mode gridlines/axis lines/tick marks noticeably thicker/more
   pronounced than before, and chart text read as a glaring pure white.
   `--na-border`/`--na-grid` are now 0.1–0.12 in dark mode, and `--na-text`
   is 0.92 alpha — light and dark each need their own tuning, the same
   numeric alpha doesn't "feel" the same on a light vs. dark surface.
4. **Plotly `fig.add_annotation()` text (`class="annotation-text"`, e.g. the
   Overview "Jan"/"Feb"/.../"Total" month-group labels) is a separate element
   from `.outsidetextlayer text`/`.xtick > text` and was not covered by the
   original rule set** — it kept its baked dark-mode `rgb(255,255,255)` fill
   in light mode until `.annotation-text` was added to the `--na-text` rule.

This block deliberately **excludes**:
- Pie/donut "inside" slice text and stacked-bar "inside" % labels (intentional
  white-on-color, set via `textfont=dict(color="white", ...)`) — these live
  in `.barlayer`/`.pielayer` without a distinguishing class from "outside"
  text, so they are left alone by the global rule.
- "Outside" bar value labels on the Overview pubs/posts/reach chart
  (`#amazon-2026-pubs-posts-reach .barlayer text`) — handled by a
  chart-scoped override instead, for the same reason.
- Annotation `<tspan>` colors set via inline `<span style="color:...">`
  (e.g. the P2S2G1 narrative legend swatches) — these carry deliberate
  per-item colors and are not part of the global override.

When adding a new chart, you should not normally need to add new CSS — the
global rules cover standard axes/gridlines/legend/hover/outside-text. Only
add a scoped override if you introduce another "outside" bar/pie text label
with `textfont=dict(color=THEME_TEXT, ...)` next to "inside" white labels in
the same chart.

### Donut/pie charts (Overview TML/media-type/platform donuts, Publisher mini-donuts)
- `hole`: 0.46 (Overview donuts) vs 0.62 (Publisher mini-donuts)
- Slice text: white, 11–14px, `textposition="inside"`
- Marker line: 0.5px, color = `THEME_SURFACE` (separation between slices)
- `sort=False` (preserves category order)
- Legend: vertical, `x=1.02, y=0.5` where shown; mini-donuts have
  `showlegend=False` with inline labels

### Bar charts (Overview pubs/posts/reach, sentiment-split stacked bars)
- Custom numeric x-axis positions (not categorical) to interleave Trad/SoMe
  bars per month, with a wider gap before a "Total" group
- Bar width 0.9, `barmode="group"` or `"stack"`
- Value labels: `textposition="outside"` (grouped) or `"inside"` white 10px (stacked %)
- Legend: vertical, `x=1.02, y=0.5`
- Month labels rendered as paper-space annotations below the x-axis

### Line/timeline charts (Publisher/Narrative weekly timelines)
- `mode="lines+markers"`, spline shape, `smoothing=0.45`
- Line width 2.5 (sentiment timelines) or 1.5 (trend lines)
- Markers: size 5–6, `circle` (Trad) / `diamond` (SoMe)
- Dash style: `solid` (Trad) / `dot` (SoMe)
- Fill: `tozeroy`, fillcolor = sentiment/narrative color at 8–18% alpha (`_hex_to_rgba`)
- Dual y-axis (`yaxis2`) when Trad+SoMe use different units
- Legend: horizontal, top-right (`y=1.08, x=1, xanchor="right"`)
- `hovermode="x unified"`

### Treemap (Publisher topic-area breakdown)
- Uses `DONUT_COLORS` cycling palette
- `texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}"`, font 14px
- Root tile color = `--na-surface-alt`
- Annotation (top-left) shows total count, 12px muted

### Venn-style overlap chart (Publishers KPI)
- Two semi-transparent filled circles (scatter `fill="toself"`), colors from §4b
  (`ACCENT_TRAD`/`ACCENT_SOME` via `_hex_to_rgba(..., 0.28)`)
- Hand-computed circle geometry (radius scaled by `sqrt(count)`, manual overlap math)
- Text traces for "Trad"/"SoMe" labels (14px, Arial Black) and counts (15px, Arial Black)

---

## 7. Tables (`dash_table.DataTable`)

Common shape, built from `THEME_*` tokens (now backed by `--na-*` via the
page-scoped alias blocks, see §1):
- `style_as_list_view=True`
- Cell: `fontSize: 12px`, `padding: 5px 9px`, `height: 34–38px`, `lineHeight: 1.2`,
  background = row-even, border = `1px solid <border>`
- Header: background = surface-alt/header-bg, `fontWeight: 700`, height 32–34px, centered
- Zebra striping: odd rows get `row-odd` background
- Active/selected cell highlight: `var(--bs-primary-bg-subtle)` background + border
- Container: `border: 1px solid <border>`, `border-radius: 8px`, `overflow: hidden`
- Tooltips (`TOOLTIP_CSS`): forced dark (`#111827`/`#f8fafc`), `border-radius: 10px`,
  `box-shadow: 0 14px 32px rgba(0,0,0,0.35)`, z-index 5000–9999 — kept as a
  deliberate exception (see §10)

### "Data bar" cells (Publishers overview table, Narratives table)
Per-cell inline `linear-gradient(90deg, <semantic-color> 0%, <semantic-color> X%,
<row-bg> X%, <row-bg> 100%)` where X% = value's share of the column max.
Colors come from `--na-bar-*` (§1/§4).

### Pagination — never hardcode black/white
Dash's default pagination bar (current-page digit, `<<`/`<`/`>`/`>>` arrows)
renders in plain black, which is invisible/wrong in dark mode and inconsistent
in light mode. **Every page must apply a single page-scoped, generic rule
targeting `.dash-table-container` (not individual table ids)** so it covers
all current and future tables on that page automatically:

```css
#amazon-2026-<page> .dash-table-container .current-page,
#amazon-2026-<page> .dash-table-container .current-page input,
#amazon-2026-<page> .dash-table-container .current-page-shadow,
#amazon-2026-<page> .dash-table-container .current-page-container input,
#amazon-2026-<page> .dash-table-container .page-number,
#amazon-2026-<page> .dash-table-container .page-number *,
#amazon-2026-<page> .dash-table-container .dash-table-pagination,
#amazon-2026-<page> .dash-table-container .dash-table-pagination *,
#amazon-2026-<page> .dash-table-container input.current-page,
#amazon-2026-<page> .dash-table-container .first-page,
#amazon-2026-<page> .dash-table-container .previous-page,
#amazon-2026-<page> .dash-table-container .next-page,
#amazon-2026-<page> .dash-table-container .last-page {
  color: var(--amazon-publishers-text) !important;
  -webkit-text-fill-color: var(--amazon-publishers-text) !important;
}
```

(`current-page` additionally gets `background`/`border-color` from
`--amazon-publishers-surface`/`--amazon-publishers-border`.) **Rule of thumb
for the whole dashboard: text must never be literal `#000`/`#fff`/`black`/
`white` — always a `--na-text*` (or page-alias) token, so it tracks the
light/dark theme.** Adding a new table never requires new pagination CSS;
if it does, the page-scoped rule above is missing or mis-scoped.

---

## 8. Controls (filters)

| Control | Class | Style |
|---|---|---|
| Dropdowns | `.amazon-publishers-dropdown` | background/color via `--dropdown-bg`/`--text`, `Select-control` radius 8px, min-height 38px |
| Trad/SoMe toggle | `.amazon-publishers-radio label` | pill: border 1px, radius 8px, padding 6px 10px, font 13px, min-height 34px |
| Control label | `.amazon-publishers-control-label` | 12px, 700, uppercase, `--text-muted` |
| Chart controls row | `.amazon-publishers-chart-controls` | flex, `padding-bottom: 14px`, `border-bottom: 1px solid <border>` |

Controls grid (Publishers overview): 3 columns
`minmax(280px,1.3fr) minmax(180px,0.8fr) minmax(240px,1fr)`. Narratives
overrides this to a single column `minmax(280px, 440px)`.

---

## 9. Layout grids (page structure)

| Page/section | Grid |
|---|---|
| Overview KPI row | `.amazon-overview-kpi-grid` → `2fr 1fr` (Trad / SoMe `na_panel`s), collapses to 1 col below 900px |
| Overview "Traditional Media" KPIs | `.amazon-publishers-kpis` → `repeat(3, minmax(320px,1fr))` |
| Overview "Social Media" KPIs | `.amazon-publishers-kpis.amazon-publishers-kpis--2col` → `repeat(2, minmax(0,1fr))` |
| Overview donut row | `vm.Grid([[0,1,2]])`, row-min-height 380px, each donut a `vm.Figure` + `na_panel` |
| Publishers KPI row | `.amazon-publishers-kpis` → `repeat(3, minmax(320px,1fr))`, collapses to 1 col below 1100px |
| Publishers KPI panel summary | `minmax(180px,220px) minmax(0,1fr)` (KPIs + venn) |
| Publishers KPI panel body | `minmax(150px,180px) minmax(0,1fr)` (stat + donut) |
| Narratives KPI grid | `.amazon-publishers-kpis-grid` → flex column of two 3-col grids (2 rows × 3) |
| Publisher detail grid | `minmax(280px,0.9fr) minmax(360px,1.3fr)` (KPIs + profile), collapses <1100px |
| Narrative detail grid | `minmax(200px,0.7fr) minmax(360px,2fr)` (summary + Trad/SoMe panels), collapses <900px |
| Narrative source grid | `repeat(2, minmax(280px,1fr))`, collapses <900px |
| Detail KPI grid | `repeat(2, minmax(130px,1fr))`, collapses <720px |
| Profile grid | `78px minmax(0,1fr)` (avatar + body), collapses <720px |
| Links row | `repeat(2, minmax(0,max-content))`, collapses <720px |

Responsive breakpoints used: `720px`, `900px`, `1100px`.

---

## 10. Deliberate exceptions

1. **P2S2G1 (Weekly Reach by Narrative)** keeps its custom small-multiples
   tooltip/legend (needed for custom item ordering that the native Plotly
   legend doesn't support) — but its colors are now theme-aware
   (`THEME_SURFACE`/`THEME_BORDER`/`THEME_TEXT`), not a separate dark-only
   constant. Wrapped in `na_panel` like every other element, so the box and
   element title match the rest of the dashboard.
2. **Dash table tooltips** (`TOOLTIP_CSS`) remain forced-dark regardless of
   page theme — these are small floating popovers that need guaranteed
   contrast against arbitrary page content underneath them.
3. **Categorical/cycling palettes** (`MEDIA_TYPE_COLORS`, `PLATFORM_COLORS`,
   `DONUT_COLORS`) are kept as-is (not part of the `--na-*` consolidation) —
   they're large qualitative sets where consolidation would reduce distinctiveness.
