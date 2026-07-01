from dashboards.amazon_2026.charts_discover import (
    _normalize_text,
    _stem_token,
    discover_records,
    discover_search_rank,
    filter_discover_records,
)
import pandas as pd


def _record(**overrides):
    base = {
        "_id": 0,
        "Date": "2026-01-01",
        "Source": "Trad",
        "Sentiment": "Neutral",
        "Publisher": "Reuters",
        "Topic_Area": "Logistics",
        "Narrative": "Antitrust",
        "Media_Type": "News",
        "Title": "Amazon faces new logistics inquiry",
        "Summary": "Regulators are reviewing Amazon's warehouse practices.",
        "URL": "",
        "Reach": 0,
        "Journalist": "Jane Doe",
        "Full_Text": "The full article body about competition concerns in retail.",
        "_date_index": 0,
    }
    base.update(overrides)
    return base


def test_normalize_text_strips_punctuation_case_and_diacritics():
    assert _normalize_text("Café—Müller, Inc.") == "cafe muller inc"
    assert _normalize_text("  multiple   spaces  ") == "multiple spaces"


def test_stem_token_handles_plurals_without_overreaching():
    assert _stem_token("campaigns") == "campaign"
    assert _stem_token("companies") == "company"
    assert _stem_token("press") == "press"  # double-s guard
    assert _stem_token("this") == "this"  # too short to strip


def test_rank_title_hit_beats_summary_and_metadata():
    title_hit = _record(Title="Amazon logistics probe widens")
    summary_hit = _record(Title="Quarterly roundup", Summary="A probe into logistics widens further")
    metadata_hit = _record(Title="Quarterly roundup", Summary="Nothing relevant", Topic_Area="logistics probe")

    # exact phrase in the title is the top tier
    assert discover_search_rank(title_hit, "logistics probe") == 0
    # both tokens present across title+summary, but not as one phrase
    assert discover_search_rank(summary_hit, "logistics probe") == 1
    assert discover_search_rank(metadata_hit, "logistics probe") == 2
    assert discover_search_rank(title_hit, "logistics probe") < discover_search_rank(metadata_hit, "logistics probe")


def test_rank_fulltext_only_hit_requires_fulltext_flag():
    fulltext_hit = _record(Title="Roundup", Summary="Nothing", Topic_Area="", Full_Text="merger antitrust filing today")

    assert discover_search_rank(fulltext_hit, "merger antitrust", fulltext=False) is None
    assert discover_search_rank(fulltext_hit, "merger antitrust", fulltext=True) == 3


def test_rank_handles_inflected_query_terms():
    record = _record(Title="Company faces new campaign backlash")
    assert discover_search_rank(record, "campaigns") == 1


def test_fuzzy_typo_tolerance_is_lowest_tier_and_restrained():
    record = _record(Title="Amazon logistics probe widens", Summary="", Topic_Area="", Full_Text="")
    # one-letter typo on a long-enough word should still match, at the lowest tier
    assert discover_search_rank(record, "logisitcs") == 4
    # short terms never get fuzzy-matched, to avoid broadening common short words
    assert discover_search_rank(record, "pro") is None


def test_metadata_fields_are_searchable():
    journalist_hit = _record(Title="Roundup", Summary="Nothing", Journalist="Alice Smith")
    narrative_hit = _record(Title="Roundup", Summary="Nothing", Narrative="Worker Safety")
    media_hit = _record(Title="Roundup", Summary="Nothing", Media_Type="Podcast")
    source_hit = _record(Title="Roundup", Summary="Nothing", Source="SoMe")

    assert discover_search_rank(journalist_hit, "alice smith") == 2
    assert discover_search_rank(narrative_hit, "worker safety") == 2
    assert discover_search_rank(media_hit, "podcast") == 2
    assert discover_search_rank(source_hit, "some") == 2


def test_filter_discover_records_ranks_search_results_without_breaking_hard_filters():
    records = [
        _record(_id=1, Source="Trad", Title="Roundup", Summary="Nothing", Topic_Area="logistics probe"),
        _record(_id=2, Source="Trad", Title="Amazon logistics probe widens"),
        _record(_id=3, Source="SoMe", Title="Amazon logistics probe widens"),
    ]

    filtered = filter_discover_records(
        records,
        source_filter=["Trad"],
        sentiment_filter=None,
        publisher_filter=None,
        topic_area_filter=None,
        narrative_filter=None,
        date_range=None,
        search_text="logistics probe",
        search_fulltext=False,
    )

    # the SoMe record is excluded by the hard source filter even though it matches the search
    assert [r["_id"] for r in filtered] == [2, 1]


def test_discover_records_precomputes_search_index():
    frame = pd.DataFrame([_record()])
    records = discover_records(frame)
    assert records[0]["_search_index"]["title_tokens"]
