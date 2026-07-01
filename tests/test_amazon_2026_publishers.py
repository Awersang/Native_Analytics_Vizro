import ast
from pathlib import Path

import pytest


def _load_share_helpers():
    helper_names = {"_coerce_float", "num", "_share_fraction"}
    helper_defs = []
    for path in [
        Path("dashboards/amazon_2026/ui_components.py"),
        Path("dashboards/amazon_2026/charts_publishers.py"),
    ]:
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name in helper_names:
                helper_defs.append((source, node))
    helper_code = "from __future__ import annotations\nfrom typing import Any\n\n"
    helper_code += "\n\n".join(ast.get_source_segment(src, node) for src, node in helper_defs)
    namespace: dict[str, object] = {}
    exec(helper_code, namespace)
    return namespace["_share_fraction"]


def _load_timeline_helpers():
    source_path = Path("dashboards/amazon_2026/timeline_charts.py")
    source = source_path.read_text(encoding="utf-8")
    module = ast.parse(source)
    helper_names = {"_timeline_axis_title", "_timeline_chart_title"}
    helper_defs = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in helper_names
    ]
    helper_code = "from __future__ import annotations\n\n"
    helper_code += "\n\n".join(ast.get_source_segment(source, node) for node in helper_defs)
    namespace: dict[str, object] = {}
    exec(helper_code, namespace)
    return namespace["_timeline_axis_title"], namespace["_timeline_chart_title"]


def _load_topic_area_helper():
    helper_names = {
        "_coerce_float",
        "_as_list",
        "_topic_area_counts",
        "_topic_area_rows",
    }
    helper_defs = []
    for path in [
        Path("dashboards/amazon_2026/ui_components.py"),
        Path("dashboards/amazon_2026/timeline_charts.py"),
        Path("dashboards/amazon_2026/charts_publishers.py"),
    ]:
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name in helper_names:
                helper_defs.append((source, node))
    helper_code = "from __future__ import annotations\nfrom typing import Any\n\n"
    helper_code += "\n\n".join(ast.get_source_segment(src, node) for src, node in helper_defs)
    namespace: dict[str, object] = {}
    exec(helper_code, namespace)
    return namespace["_topic_area_counts"], namespace["_topic_area_rows"]

def test_share_fraction_treats_source_values_as_percentage_points() -> None:
    share_fraction = _load_share_helpers()
    record = {
        "some_positive_pct": 0.7,
        "some_negative_pct": 87.9,
        "trad_positive_pct": 77.6,
        "trad_negative_pct": 0,
    }

    assert share_fraction(record, "some_positive_pct") == pytest.approx(0.007)
    assert share_fraction(record, "some_negative_pct") == pytest.approx(0.879)
    assert share_fraction(record, "trad_positive_pct") == pytest.approx(0.776)
    assert share_fraction(record, "trad_negative_pct") == pytest.approx(0.0)


def test_publications_timeline_uses_shared_axis_label() -> None:
    timeline_axis_title, timeline_chart_title = _load_timeline_helpers()

    assert timeline_chart_title("publications", "posts") == "Publications Timeline by Sentiment"
    assert timeline_axis_title("Trad", "publications", "posts") == "Publications and Posts"
    assert timeline_axis_title("SoMe", "publications", "posts") == "Publications and Posts"


def test_reach_timeline_uses_reach_and_engagement_labels() -> None:
    timeline_axis_title, timeline_chart_title = _load_timeline_helpers()

    assert timeline_chart_title("reach", "engagement") == "Reach and Engagement by Sentiment"
    assert timeline_axis_title("Trad", "reach", "engagement") == "Trad Reach"
    assert timeline_axis_title("SoMe", "reach", "engagement") == "SoMe Engagement"


# NOTE: publisher_uid filtering happens once, upstream, in pages/publishers.py's
# `_load_uid_rows` (a DataFrame filter before these helpers ever see the rows) —
# _topic_area_counts/_topic_area_rows deliberately don't re-filter by publisher.
# These tests pass already-scoped-to-one-publisher rows, matching that contract.


def test_topic_area_counts_sums_publication_count_by_topic_area() -> None:
    topic_area_counts, _ = _load_topic_area_helper()
    rows = [
        {"topic_area": "Prime", "publication_count": 3},
        {"topic_area": "Marketplace", "publication_count": 2},
        {"topic_area": "", "publication_count": 1},
        {"topic_area": "Prime", "publication_count": 4},
    ]

    assert topic_area_counts(rows) == {
        "Prime": 7.0,
        "Marketplace": 2.0,
        "Unknown": 1.0,
    }


def test_topic_area_counts_support_post_count_values() -> None:
    topic_area_counts, _ = _load_topic_area_helper()
    rows = [
        {"topic_area": "Prime", "post_count": 5},
        {"topic_area": "Deals", "post_count": 3},
        {"topic_area": "Prime", "post_count": 2},
    ]

    assert topic_area_counts(rows, value_key="post_count") == {
        "Prime": 7.0,
        "Deals": 3.0,
    }


def test_topic_area_rows_combine_trad_and_some_sources() -> None:
    _, topic_area_rows = _load_topic_area_helper()
    payload = {
        "trad_topic_areas": [
            {"topic_area": "Prime", "publication_count": 4},
            {"topic_area": "Marketplace", "publication_count": 2},
        ],
        "some_topic_areas": [
            {"topic_area": "Prime", "post_count": 3},
            {"topic_area": "Deals", "post_count": 5},
        ],
    }

    assert topic_area_rows(payload, ["Trad", "SoMe"]) == [
        {"topic_area": "Prime", "value": 7.0},
        {"topic_area": "Deals", "value": 5.0},
        {"topic_area": "Marketplace", "value": 2.0},
    ]
