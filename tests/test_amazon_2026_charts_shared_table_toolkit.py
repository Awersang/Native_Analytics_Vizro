"""Regression guard for the Tier 3 #7 dedup pass: the generic trad/some metric
table toolkit and the top-publishers/top-journalists table builders moved out
of charts_publishers.py / charts_narratives.py into ui_components.py (formerly
charts_shared.py, split per IMPROVEMENT_PLAN.md §5.4), and the modules that
used to reach into them privately now import from ui_components.
"""
import importlib

import dashboards.amazon_2026.ui_components as ui_components

MOVED_NAMES = [
    # Generic trad/some metric table + KPI/UI toolkit (originally Publishers-only)
    "SOURCE_OPTIONS",
    "table_records",
    "table_columns",
    "header_divider_styles",
    "data_bar_styles",
    "cell_width_styles",
    "detail_kpi_groups",
    "dev_inline_label",
    "find_record",
    # Top publishers / top journalists detail tables (originally Narratives-only)
    "TOP_TABLES_PAGE_SIZE",
    "build_shared_x_range",
    "top_publishers_table_columns",
    "top_publishers_table_rows",
    "top_publishers_data_bar_styles",
    "top_journalists_table_columns",
    "top_journalists_table_rows",
    "top_journalists_data_bar_styles",
]


def test_moved_names_are_importable_from_ui_components():
    for name in MOVED_NAMES:
        assert hasattr(ui_components, name), f"{name} missing from ui_components"


def test_consumer_modules_import_cleanly_after_the_move():
    for module_name in [
        "dashboards.amazon_2026.charts_publishers",
        "dashboards.amazon_2026.charts_narratives",
        "dashboards.amazon_2026.charts_campaigns",
        "dashboards.amazon_2026.charts_topic_areas",
        "dashboards.amazon_2026.pages.campaigns",
        "dashboards.amazon_2026.pages.publishers",
        "dashboards.amazon_2026.pages.narratives",
        "dashboards.amazon_2026.pages.topic_areas",
    ]:
        importlib.import_module(module_name)


def test_table_records_and_table_columns_no_longer_privately_cross_imported():
    for module_name in [
        "dashboards.amazon_2026.charts_campaigns",
        "dashboards.amazon_2026.charts_topic_areas",
    ]:
        source = importlib.import_module(module_name).__file__
        text = open(source, encoding="utf-8").read()
        assert "from dashboards.amazon_2026.charts_publishers import" not in text
        assert "from dashboards.amazon_2026.charts_narratives import" not in text
