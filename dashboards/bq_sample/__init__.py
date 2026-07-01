"""
Dashboard plugin: Disinformation Timeline (BigQuery).

Wired to ``native-analytics-486522.amazon_2025.disinformation_timeline`` via
Vizro *dynamic data* so the query runs at render time, with a fixture fallback
when BigQuery is unavailable.
"""

from __future__ import annotations

import vizro.models as vm
import vizro.plotly.express as px
from vizro.managers import data_manager

from dashboards._base import BuildContext, DashboardManifest, export_button
from dashboards.bq_sample.data import DATA_KEY, data_health, load_disinformation_timeline

MANIFEST = DashboardManifest(
    slug="bq_sample",
    title="Disinformation Timeline",
    description="Daily publication counts per disinformation-lifecycle stage, queried live from BigQuery (with offline fallback).",
    icon="cloud",
    category="Disinformation",
    data_requirements=["bigquery:amazon_2025.disinformation_timeline"],
    internal=True,
)

def _register_data_sources() -> None:
    # Register the dynamic data source at build time too because Vizro resets
    # clear the shared data manager during dev hot reload.
    data_manager[DATA_KEY] = load_disinformation_timeline


_register_data_sources()


def build_pages(ctx: BuildContext) -> list[vm.Page]:
    _register_data_sources()
    page = vm.Page(
        id="bq_sample",
        title=MANIFEST.title,
        path=MANIFEST.base_path,
        description=(
            "Daily publication counts per disinformation-lifecycle stage, queried live from "
            "BigQuery (with an offline fallback). Use the Stage filter to focus on specific stages. "
            "Data source: live."
        ),
        components=[
            vm.Graph(
                id="bq_timeline_area",
                title="Publications Over Time by Stage",
                figure=px.area(
                    data_frame=DATA_KEY,
                    x="day",
                    y="number_of_publications",
                    color="stage",
                    labels={
                        "day": "Day",
                        "number_of_publications": "Publications",
                        "stage": "Stage",
                    },
                ),
            ),
            vm.Graph(
                id="bq_stage_bar",
                title="Total Publications by Stage",
                figure=px.bar(
                    data_frame=DATA_KEY,
                    x="stage",
                    y="number_of_publications",
                    color="stage",
                    labels={
                        "stage": "Stage",
                        "number_of_publications": "Publications",
                    },
                ),
            ),
            export_button(),
        ],
        controls=[
            vm.Filter(column="stage", selector=vm.Checklist(title="Stage")),
        ],
    )
    return [page]

