import dashboards.amazon_2026.data_common as dc


def test_optional_string_expr_picks_first_matching_candidate():
    columns = {"publisher_display": "Publisher_Display", "name": "Name"}
    expr = dc._optional_string_expr("p", columns, ["missing", "publisher_display", "name"])
    assert expr == "NULLIF(TRIM(CAST(p.`Publisher_Display` AS STRING)), '')"


def test_optional_string_expr_falls_back_when_no_candidate_exists():
    expr = dc._optional_string_expr("p", {}, ["missing", "also_missing"])
    assert expr == "CAST(NULL AS STRING)"


def test_optional_numeric_expr_picks_first_matching_candidate():
    columns = {"reach": "Reach"}
    expr = dc._optional_numeric_expr("t", columns, ["impressions", "reach"])
    assert expr == "COALESCE(t.`Reach`, 0)"


def test_optional_numeric_expr_falls_back_when_no_candidate_exists():
    expr = dc._optional_numeric_expr("t", {}, ["missing"])
    assert expr == "0"


def test_optional_json_string_expr_picks_first_matching_candidate():
    columns = {"platforms_url": "platforms_url"}
    expr = dc._optional_json_string_expr("p", columns, ["author_profile_url", "platforms_url"])
    assert expr == "NULLIF(TRIM(TO_JSON_STRING(p.`platforms_url`)), 'null')"


def test_optional_json_string_expr_falls_back_when_no_candidate_exists():
    expr = dc._optional_json_string_expr("p", {}, ["missing"])
    assert expr == "CAST(NULL AS STRING)"


def test_coalesce_string_expr_combines_every_matching_candidate_in_order():
    columns = {"description": "Description", "main_text": "Main_Text"}
    expr = dc._coalesce_string_expr(
        "s", columns, ["main_text", "description", "_3p_description"]
    )
    assert expr == (
        "COALESCE(NULLIF(TRIM(CAST(s.`Main_Text` AS STRING)), ''), "
        "NULLIF(TRIM(CAST(s.`Description` AS STRING)), ''))"
    )


def test_coalesce_string_expr_falls_back_when_no_candidate_exists():
    expr = dc._coalesce_string_expr("s", {}, ["missing"])
    assert expr == "CAST(NULL AS STRING)"


def test_sentiment_case_normalises_to_three_buckets():
    expr = dc._sentiment_case("t.Sentiment")
    assert expr == (
        "CASE WHEN LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'pos%' THEN 'Positive' "
        "WHEN LOWER(TRIM(COALESCE(t.Sentiment, ''))) LIKE 'neg%' THEN 'Negative' "
        "ELSE 'Neutral' END"
    )


def test_metric_pivot_uses_default_column_names():
    sql = dc._metric_pivot("agg", ["topic_area"])
    assert sql == (
        "SELECT topic_area, 'publications' AS base_metric, publications AS metric_value FROM agg\n"
        "        UNION ALL\n"
        "        SELECT topic_area, 'reach' AS base_metric, reach AS metric_value FROM agg"
    )


def test_metric_pivot_supports_custom_column_names_and_multiple_dims():
    sql = dc._metric_pivot("agg", ["topic_area", "week_start"], count_col="posts", reach_col="engagement")
    assert sql == (
        "SELECT topic_area, week_start, 'publications' AS base_metric, posts AS metric_value FROM agg\n"
        "        UNION ALL\n"
        "        SELECT topic_area, week_start, 'reach' AS base_metric, engagement AS metric_value FROM agg"
    )


def test_weekly_grid_cte_without_extra_filter():
    sql = dc._weekly_grid_cte("topic_area", "topic_areas")
    assert sql == (
        "all_topic_areas AS (\n"
        "        SELECT DISTINCT topic_area\n"
        "        FROM all_weekly\n"
        "        WHERE topic_area IS NOT NULL\n"
        "    ),\n"
        "    all_weeks AS (\n"
        "        SELECT DISTINCT week_start FROM all_weekly WHERE week_start IS NOT NULL\n"
        "    ),\n"
        "    grid AS (\n"
        "        SELECT w.week_start, d.topic_area\n"
        "        FROM all_weeks w CROSS JOIN all_topic_areas d\n"
        "    )"
    )


def test_weekly_grid_cte_with_extra_filter():
    sql = dc._weekly_grid_cte("narrative_id", "narratives", extra_filter="narrative_id != ''")
    assert "WHERE narrative_id IS NOT NULL\n      AND narrative_id != ''" in sql


def test_table_builds_fully_qualified_reference():
    assert dc._table("amazon_2026_trad") == "`native-analytics-486522.amazon_2026.amazon_2026_trad`"


def test_resolve_dataset_uses_client_bq_dataset_override(monkeypatch):
    from tenancy import users as users_mod
    from tenancy.models import Client

    class _Store:
        def get_client(self, cid):
            assert cid == dc.AMAZON_CLIENT_ID
            return Client(id=cid, name="Amazon", bq_dataset="amazon_2026_eu")

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    assert dc._resolve_dataset() == (dc._FALLBACK_PROJECT_ID, "amazon_2026_eu")


def test_resolve_dataset_falls_back_when_no_client_record(monkeypatch):
    from tenancy import users as users_mod

    class _Store:
        def get_client(self, cid):
            return None

    monkeypatch.setattr(users_mod, "get_user_store", lambda: _Store())
    assert dc._resolve_dataset() == (dc._FALLBACK_PROJECT_ID, dc._FALLBACK_DATASET_ID)


def test_resolve_dataset_falls_back_when_store_unreachable(monkeypatch):
    from tenancy import users as users_mod

    def _boom():
        raise RuntimeError("Firestore unavailable")

    monkeypatch.setattr(users_mod, "get_user_store", _boom)
    assert dc._resolve_dataset() == (dc._FALLBACK_PROJECT_ID, dc._FALLBACK_DATASET_ID)
