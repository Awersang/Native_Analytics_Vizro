"""safe_load() must log a failed load, not silently render it as "no data"
(see IMPROVEMENT_PLAN.md §5.17) -- otherwise a real BigQuery outage in prod
is indistinguishable from an empty result. The empty frame it returns also
carries a `.attrs["load_failed"]` tag so chart builders can show "Data
temporarily unavailable" instead of "No data available" for that case.
"""
import logging

import pandas as pd

import dashboards.amazon_2026.ui_components as ui_components
from dashboards.amazon_2026.timeline_charts import timeline_figure
from dashboards.amazon_2026.ui_components import (
    data_load_failed,
    detail_weekly_figure,
    load_and_filter,
)


def test_safe_load_returns_empty_frame_and_logs_on_failure(caplog):
    with caplog.at_level(logging.ERROR, logger=ui_components.logger.name):
        result = ui_components.safe_load("amazon_2026_does_not_exist")

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert any("amazon_2026_does_not_exist" in record.message for record in caplog.records)
    assert data_load_failed(result)


def test_load_and_filter_propagates_load_failed_flag(caplog):
    with caplog.at_level(logging.ERROR, logger=ui_components.logger.name):
        result = load_and_filter("amazon_2026_does_not_exist", "publisher_uid", "x")

    assert result.empty
    assert data_load_failed(result)


def test_data_load_failed_is_false_for_a_genuinely_empty_frame():
    assert not data_load_failed(pd.DataFrame())


def _empty_annotation_text(fig) -> str:
    return fig.layout.annotations[0].text


def test_detail_weekly_figure_distinguishes_failed_from_empty():
    failed_fig = detail_weekly_figure(
        ui_components.safe_load("amazon_2026_does_not_exist"), "weekly_publications", "Y", "Cum",
    )
    assert _empty_annotation_text(failed_fig) == ui_components.UNAVAILABLE_MESSAGE

    empty_fig = detail_weekly_figure(pd.DataFrame(), "weekly_publications", "Y", "Cum")
    assert _empty_annotation_text(empty_fig) == "No data available"


def test_timeline_figure_distinguishes_failed_from_empty():
    failed_fig = timeline_figure({"load_failed": True}, ["Trad", "SoMe"])
    assert _empty_annotation_text(failed_fig) == "Data temporarily unavailable"

    empty_fig = timeline_figure({}, ["Trad", "SoMe"])
    assert _empty_annotation_text(empty_fig) == "No weekly data"
