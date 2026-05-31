"""
Page 1 — Reach & Engagement Timeline

Layout
  Row A (tall)  : dual-axis reach/engagement line chart
  Row B (short) : campaign Gantt timeline

Controls
  Narrative   : single-select dropdown (6 options incl. "All narratives")
  Sentiment   : multi-select checklist
  Date range  : date-picker range
  Campaigns   : multi-select checklist → only affects the Gantt
  Axis scale  : radio items → toggles both y-axes between linear / log
"""

import vizro.models as vm

from charts import campaign_gantt, reach_engagement_timeline
from data import df_campaigns, df_weekly

# All campaign labels for default checklist value
_ALL_CAMPAIGNS = df_campaigns["campaign_label"].tolist()

timeline_page = vm.Page(
    title="Reach & Engagement Timeline",
    layout=vm.Grid(
        grid=[
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ],
        row_min_height="80px",
    ),
    components=[
        vm.Graph(
            id="reach_eng_chart",
            title="Weekly Reach (solid) & Engagement (dotted) by Sentiment",
            figure=reach_engagement_timeline(data_frame=df_weekly),
        ),
        vm.Graph(
            id="campaign_chart",
            title="Campaign Timeline  ·  bar colour = total reach (blue-low → yellow-high)",
            figure=campaign_gantt(data_frame=df_campaigns),
        ),
    ],
    controls=[
        # ── Narrative selector ────────────────────────────────────────────────
        vm.Filter(
            column="narrative_label",
            targets=["reach_eng_chart"],
            selector=vm.Dropdown(
                title="Narrative",
                multi=False,
                value="All narratives",
            ),
        ),

        # ── Sentiment checklist ───────────────────────────────────────────────
        vm.Filter(
            column="sentiment",
            targets=["reach_eng_chart"],
            selector=vm.Checklist(
                title="Sentiment",
                value=["positive", "neutral", "negative"],
            ),
        ),

        # ── Date range ────────────────────────────────────────────────────────
        vm.Filter(
            column="week_start",
            targets=["reach_eng_chart"],
            selector=vm.DatePicker(
                title="Date range",
                range=True,
            ),
        ),

        # ── Campaign toggle (affects Gantt only) ──────────────────────────────
        vm.Filter(
            column="campaign_label",
            targets=["campaign_chart"],
            selector=vm.Checklist(
                title="Show campaigns",
                value=_ALL_CAMPAIGNS,
            ),
        ),

        # ── Y-axis scale parameter ────────────────────────────────────────────
        vm.Parameter(
            targets=["reach_eng_chart.yaxis.type", "reach_eng_chart.yaxis2.type"],
            selector=vm.RadioItems(
                options=["linear", "log"],
                value="linear",
                title="Axis scale",
            ),
        ),
    ],
)
