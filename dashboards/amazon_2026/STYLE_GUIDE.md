# Amazon 2026 Dashboard — Style Guide (as implemented)

This documents the unified style system implemented per `STYLE_PLAN.md`.
It supersedes the pre-implementation audit that used to live here.

---

## 1. Design tokens (`--na-*`)

Single source of truth: `assets/native_analytics.css`, declared once on
`:root` (light) with overrides under `[data-bs-theme="dark"]`. Covers the
Overview, Narratives and Publishers pages.

| Token                                      | Light                                  | Dark                     | Used for                                                       |
| ------------------------------------------ | -------------------------------------- | ------------------------ | -------------------------------------------------------------- |
| `--na-text`                                | `#212529`                              | `rgba(235,241,250,0.92)` | titles, headers, KPI values, axis titles, legends, annotations |
| `--na-text-muted`                          | `rgba(33,37,41,0.72)`                  | `rgba(235,241,250,0.72)` | labels, captions, group titles, axis tick numbers              |
| `--na-text-soft`                           | `rgba(33,37,41,0.58)`                  | `rgba(235,241,250,0.58)` | secondary captions                                             |
| `--na-border`                              | `rgba(33,37,41,0.18)`                  | `rgba(247,249,252,0.12)` | all box borders, axis lines, tick marks                        |
| `--na-surface`                             | `var(--bs-body-bg, #ffffff)`           | `#111827`                | card/KPI/page backgrounds                                      |
| `--na-surface-alt`                         | `var(--bs-tertiary-bg, #f8f9fa)`       | `#1b212b`                | panel/section backgrounds                                      |
| `--na-surface-hover`                       | `var(--bs-secondary-bg, #edf1f5)`      | `#202631`                | hover states                                                   |
| `--na-row-even` / `--na-row-odd`           | surface / surface-alt                  | same                     | table zebra striping                                           |
| `--na-header-bg`                           | = surface-alt                          | = surface-alt            | table header background                                        |
| `--na-grid`                                | `rgba(33,37,41,0.16)`                  | `rgba(247,249,252,0.1)`  | Plotly gridlines                                               |
| `--na-dropdown-bg` / `--na-dropdown-hover` | surface / surface-hover                | same                     | `dcc.Dropdown`                                                 |
| `--na-link`                                | `var(--bs-link-color, #0d6efd)`        | `#9fd1ff`                | clickable cells/links                                          |
| `--na-kpi-group-bg`                        | = surface-alt                          | = surface-alt            | KPI panel background                                           |
| `--na-avatar-bg`                           | `var(--bs-primary-bg-subtle, #dfe7f3)` | `#283645`                | author avatar box                                              |

Categorical tokens (theme-independent, also defined in `:root`):

| Token                                                    | Hex                                               | Meaning                                                                     |
| -------------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------- |
| `--na-sentiment-positive`                                | `#2ca02c`                                         | Positive sentiment (charts + table data-bars)                               |
| `--na-sentiment-neutral`                                 | `#1f77b4`                                         | Neutral sentiment                                                           |
| `--na-sentiment-negative`                                | `#d62728`                                         | Negative sentiment                                                          |
| `--na-accent-trad`                                       | `#2f7dd1`                                         | Trad (blue) accent — Overview source bars, Venn, data-bar trad-publications |
| `--na-accent-some`                                       | `#d98933`                                         | SoMe (orange) accent — Overview source bars, Venn, data-bar some-posts      |
| `--na-accent-trad-fill` / `--na-accent-some-fill`        | `rgba(47,125,209,0.28)` / `rgba(217,137,51,0.28)` | Venn fill colors                                                            |
| `--na-bar-trad-publications` ... `--na-bar-some-average` | see `:root`                                       | table data-bar gradient palette                                             |

### Page-scoped aliases

Each page declares an `--amazon-publishers-*` alias block (under its own page
container id: `#amazon-2026-overview`, `#amazon-2026-narratives`,
`#amazon-2026-publishers`) mapping every `--amazon-publishers-*` name used by
shared Python components (`charts_shared.py`'s `THEME_*` constants, `_kpi_card`,
`na_panel`, table styles, etc.) to the corresponding `--na-*` token. This keeps
existing component code working unchanged while resolving to the single token
set.

---

## 1a. Header logo

The dashboard header shows the full Native Analytics wordmark instead of the
"Native Analytics" text title (`#dashboard-title` is hidden via CSS, but the
title string is kept for the browser tab title).

- `assets/logo_light.svg` — dark grey (`#495057`) wordmark, shown in light
  mode (`#logo-light`, Vizro's naming: the logo for the *light* theme).
- `assets/logo_dark.svg` — light grey (`#ced4da`) wordmark, shown in dark
  mode (`#logo-dark`). Same colors as `--na-loader-color`.
- Vizro auto-discovers `logo_light.*`/`logo_dark.*` in the assets folder and
  toggles visibility via `[data-bs-theme]` — no Python wiring needed.
- Size is controlled by the `--na-logo-height` token (`native_analytics.css`,
  `:root`, default `40px`) — change this one value to resize the logo in the
  header.

---

## 2. Box styles — `na_panel`

`charts_shared.py::na_panel(title, children, *, box="panel" | "outline" | "flat", controls=None)`
is the single shared wrapper for charts, tables, and KPI groups:

```python
def na_panel(title, children, *, box="panel", controls=None) -> html.Div:
    ...
```

| Style             | Class                         | Look                                                                                                                             | Used for                                                                                                                                                                                         |
| ----------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `panel` (default) | `.na-panel`                   | `border: 1px solid var(--na-border)`, `border-radius: 8px`, `background: var(--na-surface-alt)`, `padding: 18px`, `gap: 14px`    | Charts, tables, donut/treemap/Venn panels, detail KPIs                                                                                                                                           |
| `outline`         | `.na-panel.na-panel--outline` | same border/radius/padding as `panel`, but `background: transparent` — a bordered box that lets the page background show through | Overview "Traditional Media" / "Social Media" KPI groups (P1S1) — a deliberate lighter-weight variant of `panel` for grouping KPI cards without adding another filled surface on top of the page |
| `flat`            | `.na-panel.na-panel--flat`    | no border, no background, no padding, `min-height: 0` — content sits directly on the page, not in a box at all                   | Sub-components that already live inside another panel (e.g. mini-donuts/Venn inside a KPI panel)                                                                                                 |

All three render an optional `.na-element-title` div (16px / 600 / `--na-text`)
above the content when `title` is truthy.

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

| Role                              | Class                                  | Size / weight             | Notes                                                                                       |
| --------------------------------- | -------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------- |
| Section header                    | `.amazon-publishers-section-header h2` | 22px / 700                | structural groupings ("Overview", "Details", "Narrative Details")                           |
| Element title (chart/table/panel) | `.na-element-title`                    | 16px / 600                | inside every `na_panel`, replaces old `.amazon-publishers-analysis-title` and ad-hoc `<h3>` |
| KPI group title                   | `.amazon-publishers-kpi-group-title`   | 12px / 700 / uppercase    |                                                                                             |
| KPI label                         | `.amazon-publishers-kpi-label`         | 12px / 700 / uppercase    |                                                                                             |
| KPI value                         | `.amazon-publishers-kpi-value`         | 28px / 750 (24px compact) |                                                                                             |
| KPI caption                       | `.amazon-publishers-kpi-caption`       | 12px / 400                |                                                                                             |

All Plotly `title=`/`title_font`/`title_y` have been removed from figure
layouts dashboard-wide (P1, P2, P3). Every chart's title now lives in
`.na-element-title`, owned by `na_panel`. Figure margins are tightened
(`t=12` typical) since the figure no longer reserves space for an in-canvas
title.

---

## 4. Color system

### 4a. Sentiment (canonical, `SENTIMENT_COLORS` in `charts_shared.py`)
| Sentiment | Hex       | CSS token                 |
| --------- | --------- | ------------------------- |
| Positive  | `#3f9d5c` | `--na-sentiment-positive` |
| Neutral   | `#4a8fc2` | `--na-sentiment-neutral`  |
| Negative  | `#d9534f` | `--na-sentiment-negative` |

Used for Plotly sentiment traces **and** the table data-bar
positive/negative columns (`--na-bar-positive` / `--na-bar-negative` alias
this same pair — the old separate `#35a66b`/`#c84e5a` pair is gone).

### 4b. Trad / SoMe accent pair (canonical, `ACCENT_TRAD` / `ACCENT_SOME` in `charts_shared.py`)
| Role          | Hex       |
| ------------- | --------- |
| Trad (blue)   | `#2f7dd1` |
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

### 4e. `TOPIC_AREA_PALETTE` saturation — match `SENTIMENT_COLORS`
`SENTIMENT_COLORS` (§4a) sits at ~43-64% saturation / ~43-58% lightness — a
deliberately muted, "data-viz" feel. `TOPIC_AREA_PALETTE` (`charts_shared.py`,
used by `topic_area_color_map` for the Topic Areas treemap and tables) should
stay in that same ~55-65% saturation band so no topic area's tile reads as
more "neon"/cartoonish than its neighbors or than the Sentiment chart.

A handful of entries originally sat at 72-100% saturation and were toned down:
| Topic area (palette index) | Was                             | Now       |
| -------------------------- | ------------------------------- | --------- |
| Economic Impact (1)        | `#F58518` (92% sat)             | `#D1853C` |
| Workplace & Operations (3) | `#E45756` (72% sat)             | `#DA6160` |
| Innovation (6)             | `#EECA3B` (84% sat)             | `#D3B745` |
| Community Impact (7)       | `#FF9DA6` (100% sat, 81% light) | `#E5919A` |
| Amazon Haul (18)           | `#5BA300` (100% sat)            | `#7BBA2C` |

When adding new entries to `TOPIC_AREA_PALETTE`, check the new color's
saturation/lightness against this band before committing it.

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
see §9), grouped into two `na_panel(box="outline")` containers — "Traditional
Media" (3 KPIs) and "Social Media" (2 KPIs). The `outline` variant (a bordered
box with a transparent background, see §2) avoids stacking another filled
surface on top of the page background for these groups. There is no longer a
separate `vm.Card`-based KPI style on Overview.

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
3a. **`marker.line.color` on `go.Treemap`/`go.Pie` traces does not resolve
   `var(--na-*)` tokens** — unlike `bordercolor`/`font.color` on layout-level
   shapes/annotations (which Plotly renders via CSS-able SVG attributes that
   the stylesheet's `var()` re-resolution picks up), trace-level marker line
   colors are baked into the SVG `stroke` attribute at render time without
   CSS variable support, and a `var(...)` string renders as black/invalid.
   Use a literal color value (e.g. `"rgba(255,255,255,0.55)"`) for these.
3b. **Don't over-correct dark mode while fixing light mode.** An earlier pass
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
5. **`go.Sankey` node labels (`.node-label`) ignore the trace-level
   `textfont.color` entirely** — Plotly hardcodes them to white text with a
   dark `text-shadow` halo for contrast against arbitrary node colors. In
   light mode this rendered as a glaring white-with-grey-halo label on the
   page background. Fixed in `amazon_2026_topic_areas.css` for
   `#amazon-2026-topic-area-media-sankey-section .node-label`: drop the
   `text-shadow` in both themes, and in light mode (`:root:not([data-bs-theme="dark"])`)
   override `fill`/`fill-opacity` to `--na-text`. Dark mode keeps Plotly's
   default white fill (already correct there), just without the halo.

This block deliberately **excludes**:
- Pie/donut "inside" slice text and stacked-bar "inside" % labels (intentional
  white-on-color, set via `textfont=dict(color="white", ...)`) — these live
  in `.barlayer`/`.pielayer` without a distinguishing class from "outside"
  text, so they are left alone by the global rule.
- "Outside" bar value labels on the Overview pubs/posts/reach chart and the
  Campaign Timeline (`#amazon-2026-pubs-posts-reach .barlayer text`,
  `#amazon-2026-campaign-timeline-graph .barlayer text`) — handled by
  chart-scoped overrides instead, for the same reason. **Any new chart that
  uses `textposition="outside"` on a `go.Bar` needs its own
  `#<graph-id> .js-plotly-plot .barlayer text { fill: var(--na-text)
  !important; fill-opacity: 1 !important; }` rule** — otherwise the labels
  stay stuck white (baked in dark mode) when the page is in light mode.
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

### Mirrored media-split timeline (P2S4G3, `media_split_timeline_figure` in `charts_shared.py`)
- Single chart placed under P2S4G2, with a "Stacked" `dcc.Checklist` toggle in
  the panel header (`controls=` arg of `na_panel`, styled via
  `amazon-publishers-radio`). Toggling re-renders the figure via a
  `@callback` (`_update_narrative_media_split_figure` in
  `charts_narratives.py`) reading raw trad/some records + flag data from a
  `dcc.Store` (`amazon-2026-narrative-media-split-store`) — no extra queries.
- Shared weekly x-axis (Trad media types vs. SoMe platforms for the same narrative)
- Single y-axis split at zero, **shared step but independent extents**: Trad
  (above) and SoMe (below) tick at the same `step` (`_nice_axis_step`), so
  equal values sit the same pixel-distance from zero on both sides — but each
  half's axis only extends (`trad_tick_count` / `some_tick_count` ticks) as
  far as its own data needs (`trad_extent` / `some_extent` = the stacked
  total when `stacked=True`, or the tallest single series when unstacked).
  `yaxis.range = [-some_edge, trad_edge]` is therefore usually asymmetric.
  `tickvals`/`ticktext` show **absolute** values on both halves (SoMe values
  are plotted negated but unscaled).
- **Dynamic height**: `media_split_timeline_figure()` returns
  `(figure, height_px)`. `height_px = axis_height + margin_t + margin_b`,
  where `margin_t`/`margin_b` are small fixed values
  (`MEDIA_SPLIT_MARGIN_TOP_BASE`/`_BOTTOM_BASE` = 20px/40px) and
  `axis_height = (trad_tick_count + some_tick_count) *
  MEDIA_SPLIT_AXIS_PIXELS_PER_TICK` (68px/tick — ~50% taller than a plain
  45px/tick chart) **plus** `top_extra_px` / `bottom_extra_px` — the pixel
  space needed beyond the data extent for flag boxes (see below). The panel's
  `dcc.Graph` gets `style={"height": f"{height_px}px"}` (set on initial render
  and again by `_update_narrative_media_split_figure`'s second
  `Output(..., "style")` on toggle) — no fixed min-height CSS, so there's no
  leftover empty space. `MEDIA_SPLIT_MIN_HEIGHT_PX` (480px) is the floor.
- **Legend**: compact single vertical column, placed outside the plot to the
  right (`legend=dict(orientation="v", x=1.02, xanchor="left", y=1,
  yanchor="top")`), with extra right margin `MEDIA_SPLIT_MARGIN_RIGHT` (150px)
  reserved for it. The dummy legend-marker traces for flags use plain text
  ("Top 5 pub. by reach" / "Top week by pub.") — no emoji in the name, since
  the marker swatch (gray triangle / yellow star) already conveys the icon and
  duplicating it with an emoji looked cluttered.
- **Y-axis section labels**: the old single `yaxis.title` ("Trad publications
  ↑ / SoMe posts ↓") was confusing, so it's removed (`yaxis.title=None`) in
  favor of two rotated annotations placed in the left margin
  (`xref="paper", x=0, xshift=-58`), each centred vertically in its half of
  the plot (`y=trad_edge/2` for "Trad publications", `y=-some_edge/2` for
  "SoMe posts"). `MEDIA_SPLIT_MARGIN_LEFT` (70px) leaves room for both the
  tick numbers and these labels without overlap.
- **Zero line**: `yaxis.zeroline` is disabled; instead an explicit
  `fig.add_shape` line (`layer="above"`, `THEME_GRID`, `width=2` — matching
  the data lines' `line=dict(width=2, ...)`) is drawn across the full plot at
  `y=0`. With many overlapping filled lines converging on zero, the axis's own
  zeroline got visually lost underneath them; drawing it above the traces
  keeps it as a clear reference.
- Colors via `media_label_color(label, "Trad"/"SoMe")` (canonical
  `MEDIA_TYPE_COLORS`/`PLATFORM_COLORS`, falls back to `DONUT_COLORS` hash)
- Unstacked (default): `mode="lines"`, spline, `fill="tozeroy"` at 12% alpha,
  each series independent
- Stacked: same but `fill="tonexty"` at 28% alpha with
  `stackgroup="trad"` / `stackgroup="some"` (separate stacks per half)
- SoMe traces use `dash="dot"`; hovertemplate reads `customdata` (the
  un-negated value) so tooltips show positive counts
- **Flag annotations** (`_add_reach_flag_annotations`), two kinds:
  - 🚩 **Reach flags** (`top_reach_flags()`): top 5 Trad publications and top
    5 SoMe posts by `Reach` (from `NARRATIVE_TOP_PUBLICATIONS_KEY`), styled
    with `THEME_BORDER`, text = `"🚩 {label}<br>Reach: {value}"` (2 lines).
    Legend entry: "🚩 Top 5 pub. by reach".
  - ⭐ **Volume flags** (`_top_volume_week_flag()`): one per side, marking the
    single week with the highest total Trad publications / SoMe posts, styled
    with `MEDIA_SPLIT_VOLUME_COLOR` (yellow, `#D3B745`) for the box
    border/text, text = `"⭐ {label}: {value}"` (1 line). Legend entry: "Top
    week by pub.".
  - Both kinds are anchored to their week at the stacked total (stacked mode)
    or the tallest series that week (unstacked), pointing up for Trad / down
    for SoMe. Both kinds' arrows use `THEME_BORDER` (gray) — only the box
    border/text color differs by kind. Annotations sharing a week are stacked
    vertically (`ay` offset = `10 + slot * MEDIA_SPLIT_FLAG_SLOT_PX`,
    50px/slot); flags with a larger offset (farther from the axis) are drawn
    first so closer flags' arrows/labels stay on top instead of being covered.
  - **Axis-range extension**: for each flag, `_add_reach_flag_annotations`
    computes the pixel distance from the zero line to the far edge of its box
    (`abs(base) * px_per_unit + offset + box_height`, where `box_height` is
    ~38px for 2-line reach flags / ~24px for 1-line volume flags) and returns
    the max across all flags on that side. The caller compares this to the
    pixel coverage of the "normal" tick range and extends `trad_edge`/
    `some_edge` (and thus the y-axis `range`) by the shortfall
    (`top_extra_px`/`bottom_extra_px`, converted via `px_per_unit =
    MEDIA_SPLIT_AXIS_PIXELS_PER_TICK / step`) so every flag box lands inside
    the plot area instead of the margins — keeping `margin_t`/`margin_b`
    minimal while still avoiding overlap with the x-axis labels or the top
    edge.
  - Dummy marker traces (triangle for reach, star for volume) add the two
    legend entries above; only added when at least one flag of that kind
    exists.

### Treemap (Publisher topic-area breakdown)
- Uses `DONUT_COLORS` cycling palette
- `texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}"`, font 14px
- Root tile color = `--na-surface-alt`
- Annotation (top-left) shows total count, 12px muted

### Campaign Timeline (Gantt-style, P7S1G1)
- Horizontal `go.Bar` per campaign, `base`/`x` encode the date span
  (`MIN_BAR_SPAN_DAYS = 4` minimum width so short campaigns stay visible)
- Bar color encodes which source drove the campaign's reach
  (`_campaign_bar_color` in `charts_campaigns.py`, threshold band 35%/65%):
  - `ACCENT_TRAD` (blue) — Trad-led (≥65% of reach from Trad)
  - `ACCENT_SOME` (orange) — SoMe-led (≥65% of reach from SoMe)
  - `ACCENT_MIXED` (`#8c6fc9`, purple) — Mixed (neither side ≥65%, or no reach)
  - A horizontal legend (top-right, like the line/timeline charts) explains
    the three colors via three invisible dummy `go.Bar` traces
- `marker.line` = `THEME_SURFACE` (1px) for separation against the panel
  background, `marker.cornerradius = 6` for a softer/modern bar shape
- Outside text label = total reach; see §6 "Theming enforcement" for the
  `#amazon-2026-campaign-timeline-graph .barlayer text` override this needs
- Hover shows the date span and the Trad/SoMe reach breakdown

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

| Control            | Class                               | Style                                                                                       |
| ------------------ | ----------------------------------- | ------------------------------------------------------------------------------------------- |
| Dropdowns          | `.amazon-publishers-dropdown`       | background/color via `--dropdown-bg`/`--text`, `Select-control` radius 8px, min-height 38px |
| Trad/SoMe toggle   | `.amazon-publishers-radio label`    | pill: border 1px, radius 8px, padding 6px 10px, font 13px, min-height 34px                  |
| Control label      | `.amazon-publishers-control-label`  | 12px, 700, uppercase, `--text-muted`                                                        |
| Chart controls row | `.amazon-publishers-chart-controls` | flex, `padding-bottom: 14px`, `border-bottom: 1px solid <border>`                           |

Controls grid (Publishers overview): 3 columns
`minmax(280px,1.3fr) minmax(180px,0.8fr) minmax(240px,1fr)`. Narratives
overrides this to a single column `minmax(280px, 440px)`.

### Discover page controls (P8)

| Control                     | Class                                                                                   | Style                                                                                                                                                                                                                                                                                          |
| --------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search input                | `.amazon-discover-search`                                                               | `dcc.Input`, height 38px, radius 8px, border `--border`, background `--dropdown-bg`, color `--text`, focus border `--link`                                                                                                                                                                     |
| Search full-text toggle     | `.amazon-discover-search-fulltext`                                                      | `dcc.Checklist` below the search input, styled as a track/thumb toggle switch (native checkbox hidden, `label::before`/`::after` via `:has(input:checked)`); when checked, search matches `Full_Text` (`_search_fulltext`) in addition to publisher/title/summary (`_search`)                |
| Reference article box       | `.amazon-discover-reference-box`                                                        | sits right of the search input (`.amazon-discover-reference-col`, flex row with `.amazon-discover-search-col`, stacks below 900px); shows the short date, publisher and title of the publication picked via "Use as reference" on a single line with spaced-out columns (`.amazon-discover-reference-item`, flex row with 24px gaps, `--text-muted`/`--text-soft`/`--text`), plus a `close` icon-button (`.amazon-discover-reference-clear`) to reset; placeholder text (`.amazon-discover-reference-empty`) when none selected |
| Similarity slider            | `.amazon-discover-similarity-slider`                                                    | `dcc.Slider` (0–100, default 50, marks `{0:"Close", 100:"Far"}`) below the reference box, themed like `.amazon-discover-rangeslider`; when a reference is selected, maps linearly to a UMAP-space radius: `radius = (value/100) × diagonal` where `diagonal` is the bounding-box diagonal of all records; at 0 only the reference itself qualifies, at 100 the whole data cloud is included. Wired as `Input` to both `_update_discover_clusters` (draws a dashed circle on the UMAP) and `_update_discover_results` (filters the table to records within that radius via `filter_discover_records` `similarity_radius` kwarg). |
| Filter dropdowns            | `.amazon-publishers-dropdown` (in `.amazon-publishers-control`)                         | reuses shared dropdown styling; Publisher options/values use canonical `display_name` from `amazon_2026_publishers` (joined via `publisher_uid`/`publisher_display`, falling back to the raw `Publisher`/`Author` value)                                                                       |
| Date range slider           | `.amazon-discover-rangeslider`                                                          | themes `rc-slider` rail/track/handle/marks via `--border`/`--link`/`--surface`/`--text-muted`; label above shows resolved `YYYY-MM-DD to YYYY-MM-DD`; marks generated by `discover_date_marks` show `DD Mon YYYY` at the min/max ends plus one tick per calendar month (`Mon YYYY`) in between |
| Results count               | `.amazon-discover-results-count`                                                        | 12px, `--text-soft`                                                                                                                                                                                                                                                                            |
| Results table row selection | `style_data_conditional` via `clientside_callback` (`pages/discover.py`) | clicking a cell instantly highlights the whole row (`row_index` match) with `var(--bs-primary-bg-subtle)` background; implemented as two `clientside_callback`s (one per table) that fire in-browser with no server round-trip, so the highlight appears at the same moment as DataTable's native cell border; base style lives in `amazon-2026-discover-trad-base-style` / `amazon-2026-discover-some-base-style` stores (hidden stores panel) |

Controls grid (Discover filters): `.amazon-discover-controls` → `repeat(5, minmax(160px,1fr))`
(Source/Sentiment/Publisher/Topic Area/Narrative), collapses to 3 cols below
1300px and 1 col below 800px. `.amazon-discover-search-row` (full width, above
the grid) is a flex row of two equal columns: `.amazon-discover-search-col`
(search input + full-text toggle) and `.amazon-discover-reference-col`
(reference article box + similarity slider); stacks to a single column below
900px.

### Discover "Narrative Clusters (UMAP)" panel (P5S1G1 copy, P8)

A second `na_panel` placed directly below the Filters panel
(`build_discover_clusters_section`, `charts_discover.py`), reusing the
P5S1G1 Archive scatter renderer (`_archive_figure`/`_build_color_map` from
`charts_archive.py`) with `discover_cluster_records` mapping
`umap_x`/`umap_y`/`Narrative`/`Source` to the `narrative_label`/`source`
shape the renderer expects. Same "Color by narrative"/"KDE" toggles as the
Archive page, but the `dcc.Graph` height is reduced to `320px` (vs `640px`
on Archive) to keep it compact above the Results table. The
`_update_discover_clusters` callback (`pages/discover.py`) takes the same
filter `Input`s as `_update_discover_results` plus the toggle values, so the
cluster scatter re-renders in sync with all Discover filters (source,
sentiment, publisher, topic area, narrative, date range, search). The
`dcc.Graph` height is `800px`, matching the Archive page.

**Reference overlay**: when a reference publication is set (`amazon-2026-discover-reference-data`), `_add_reference_overlay` (`charts_archive.py`) adds two visual elements on top of the normal scatter: (1) a `go.Scattergl` trace at the reference point with `marker_symbol="cross"`, size 14, color `REFERENCE_MARKER_COLOR = "#ffffff"`, `showlegend=True`, labelled "Reference" — the underlying narrative-colored dot for that point remains visible beneath; (2) when similarity slider radius > 0, a `fig.add_shape(type="circle")` dashed outline in `REFERENCE_CIRCLE_COLOR = "#c8d0da"`, `width=1.5`, no fill, layer "above". The circle's x/y bounds are `reference_point ± radius` in data coordinates. Both are drawn in all coloring modes (color/time/plain). The `_update_discover_clusters` callback takes both `amazon-2026-discover-reference-data` (Input) and `amazon-2026-discover-similarity-slider` (Input), recomputing the radius from `umap_distance_bounds(all_records)` on every redraw.

**Lasso/box-select filtering**: each scatter point carries `customdata =
[_id, source]` (`_point_customdata` in `charts_archive.py`, used by both this
panel and Archive P5S1G1). Using the chart's lasso/box-select toolbar tool
fires `selectedData` on `amazon-2026-discover-clusters-graph`, captured by
`_update_discover_selection` (`pages/discover.py`) into the
`amazon-2026-discover-selected-ids` store and shown via the
`.amazon-discover-selection-banner` (with a "Clear selection" button,
`.amazon-discover-selection-clear`). `_update_discover_results` takes this
store as an additional `Input` and `filter_discover_records` (`charts_discover.py`)
ANDs it with the other filters via a new `selected_ids` kwarg (matched
against each record's `_id`). The `.amazon-discover-selection-hint` line
below the chart points users at the toolbar tool. Changing any filter
re-renders the cluster figure (new figure object); the shared `uirevision`
keeps pan/zoom stable across that re-render. The drawn lasso/box outline
(`relayoutData.selections`) is captured into the
`amazon-2026-discover-clusters-selections` store by
`_update_discover_clusters_selections` (`pages/discover.py`) and re-applied
via `fig.update_layout(selections=...)` in `_update_discover_clusters`, so the
outline survives a filter-driven redraw. Both that store and
`amazon-2026-discover-selected-ids` ignore the spurious empty
`selectedData`/`relayoutData.selections` events a redraw fires, and are only
cleared when the user clicks "Clear selection"
(`.amazon-discover-selection-clear`).

### Discover hidden stores panel (P8)

A hidden `vm.Figure` (`discover_stores_panel`, `pages/discover.py`) rendered as `display:none` holds all `dcc.Store` components for the Discover page: `amazon-2026-discover-data` (full records), `amazon-2026-discover-bounds` (date bounds), `amazon-2026-discover-detail-id` (selected row _id), `amazon-2026-discover-reference-data`, `amazon-2026-discover-selected-ids`, `amazon-2026-discover-clusters-selections`, `amazon-2026-discover-clusters-colormap`, plus `amazon-2026-discover-trad-base-style` / `amazon-2026-discover-some-base-style` (base `style_data_conditional` arrays for the clientside row-highlight callbacks). Keeping stores here rather than inside the visible panels prevents Vizro's `dcc.Loading` overlay from activating on visible panels when callbacks write to stores (e.g. writing `detail-id` on row click previously flashed the Filters panel).

### Discover "Publication Details" panel (P8)

A fourth `na_panel` below the Results table (`build_discover_detail_section`,
`charts_discover.py`). Clicking any cell in a results row except the `Link`
column (`active_cell.column_id != "URL"`) looks up that row's `_id` (added to
`discover_records`/`discover_*_table_data`, not rendered as a column) in the
`amazon-2026-discover-data` store, re-renders the panel body via
`build_discover_detail_content`, and stores the `_id` in
`amazon-2026-discover-detail-id`.

`_apply_archive_layout` (`charts_archive.py`) sets `uirevision="amazon-2026-umap"`
on every cluster figure, so changing a filter and getting a new figure object
preserves the user's pan/zoom and any active lasso/box-select outline instead
of resetting them.

The panel header (`na_panel(..., controls=...)`) carries a "Use as reference"
button (`.amazon-discover-reference-btn`, `bookmark_add` icon via
`material-symbols-outlined`). Clicking it looks up `amazon-2026-discover-detail-id`
in `amazon-2026-discover-data` and writes the record to
`amazon-2026-discover-reference-data`, rendering the short date/publisher/title
into the reference box (see Discover page controls table above). The
`.amazon-discover-reference-clear` icon-button resets both back to
`discover_reference_placeholder()`.

- `.amazon-discover-detail-grid` → `minmax(220px,0.8fr) minmax(360px,1.6fr)`,
  collapses to 1 col below 900px — KPIs on the left, details body on the right.
- `.amazon-discover-detail-kpis` → flex column; contains `.amazon-discover-detail-kpis-cards`
  (`repeat(2, minmax(130px,1fr))` of `_kpi_card`s: Reach, Engagement for SoMe only, Sentiment,
  Media Type/Platform) and, for SoMe only, an engagement-by-sentiment mini donut
  (`.amazon-discover-engagement-donut`, overrides `min-height: 160px` / graph `height: 148px`).
- **Trad body** (`.amazon-discover-detail-body`) — bordered `--surface-alt` box: Source/Media-type
  badges, title (`<h3>`), summary (`.amazon-publishers-profile-summary`), metadata grid
  (`.amazon-discover-detail-meta`, labels reuse `.amazon-publishers-kpi-label`), "Open original"
  link (`.amazon-publishers-links`). Below the grid: optional "Show full text" collapsible
  (`.amazon-discover-detail-fulltext`, Trad only).
- **SoMe body** — social-post layout inside `.amazon-discover-detail-body`: author name
  (`.amazon-discover-some-post-author`) + platform badge row, then date + followers count
  (`.amazon-discover-some-post-date/followers`) as muted sub-line, then post text
  (`.amazon-discover-some-post-content`, bordered top/bottom), topic/narrative badges, "Open post"
  link (`.amazon-discover-some-post-link`). No summary placeholder, no full-text section.
- Empty/placeholder state reuses `.amazon-publishers-empty`.

---

## 9. Layout grids (page structure)

| Page/section                      | Grid                                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| Overview KPI row                  | `.amazon-overview-kpi-grid` → `2fr 1fr` (Trad / SoMe `na_panel`s), collapses to 1 col below 900px |
| Overview "Traditional Media" KPIs | `.amazon-publishers-kpis` → `repeat(3, minmax(320px,1fr))`                                        |
| Overview "Social Media" KPIs      | `.amazon-publishers-kpis.amazon-publishers-kpis--2col` → `repeat(2, minmax(0,1fr))`               |
| Overview donut row                | `vm.Grid([[0,1,2]])`, row-min-height 380px, each donut a `vm.Figure` + `na_panel`                 |
| Publishers KPI row                | `.amazon-publishers-kpis` → `repeat(3, minmax(320px,1fr))`, collapses to 1 col below 1100px       |
| Publishers KPI panel summary      | `minmax(180px,220px) minmax(0,1fr)` (KPIs + venn)                                                 |
| Publishers KPI panel body         | `minmax(150px,180px) minmax(0,1fr)` (stat + donut)                                                |
| Narratives KPI grid               | `.amazon-publishers-kpis-grid` → flex column of two 3-col grids (2 rows × 3)                      |
| Publisher detail grid             | `minmax(280px,0.9fr) minmax(360px,1.3fr)` (KPIs + profile), collapses <1100px                     |
| Narrative detail grid             | `minmax(200px,0.7fr) minmax(360px,2fr)` (summary + Trad/SoMe panels), collapses <900px            |
| Narrative source grid             | `repeat(2, minmax(280px,1fr))`, collapses <900px                                                  |
| Detail KPI grid                   | `repeat(2, minmax(130px,1fr))`, collapses <720px                                                  |
| Profile grid                      | `78px minmax(0,1fr)` (avatar + body), collapses <720px                                            |
| Links row                         | `repeat(2, minmax(0,max-content))`, collapses <720px                                              |

Responsive breakpoints used: `720px`, `900px`, `1100px`.

---

## 10. Narratives — Angles table (P2S4T1) column schema

Columns: **Angle** | **Sentiment** | **Trad** | **SoMe** | **Reach** | **Popularity (%)**

- `trad_publications` (Trad): count from the `amazon_2026_trad` table joined on `dominant_angle_label`; bar color `--na-bar-trad-publications`
- `some_posts` (SoMe): count from the `amazon_2026_some` table joined on `dominant_angle_label`; bar color `--na-bar-some-posts`
- Both fall back to 0 when `dominant_angle_label` column is absent from the source tables (handled by `_optional_string_expr` in `data_angles.py`)
- The old aggregate `publications` column (from `article_count`) is retained in the BQ select for backward compatibility but no longer displayed in the table

**Top Publications / Posts (P2S4T4) angle filtering:** `_filter_top_items_by_angle` in `charts_narratives.py` falls back to showing all top-N publications when the selected angle has no matching `Angle` field in the publications dataset (covers the case where the angle label exists in the summary table but none of the reach-ranked top-50 carry it). The callback in `narratives.py` also auto-switches the Trad/SoMe source toggle when the current source has zero results but the other has data.

## 11. Deliberate exceptions

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
4. **Topic Areas theme-treemap tile dividers** use a hardcoded
   `"rgba(255,255,255,0.55)"` literal in `_topic_area_theme_treemap_figure`
   (`charts_topic_areas.py`) — a semi-transparent white that reads fine
   against the colored treemap tiles in either theme. This must stay a
   literal, not a `var(--na-*)` token: see gotcha 4 below — `marker.line.color`
   on a `go.Treemap` trace does not resolve CSS custom properties, so a
   `var(...)` value renders as a solid black/dark divider in both themes.
