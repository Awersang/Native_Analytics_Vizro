"""capture("figure") wraps the build with a timing log (IMPROVEMENT_PLAN.md §5.21)."""
import logging

from dashboards.amazon_2026.ui_components import capture


def test_figure_capture_logs_build_time(caplog):
    @capture("figure")
    def fake_panel(data_frame):
        return data_frame

    captured_callable = fake_panel(data_frame="anything")

    with caplog.at_level(logging.INFO, logger="dashboards.amazon_2026.ui_components"):
        captured_callable()

    assert any("fake_panel built in" in record.message for record in caplog.records)


def test_non_figure_capture_is_unwrapped():
    from vizro.models.types import capture as vizro_capture

    assert type(capture("action")) is type(vizro_capture("action"))
