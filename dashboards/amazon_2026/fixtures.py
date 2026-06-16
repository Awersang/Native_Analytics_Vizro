from __future__ import annotations

import itertools
import random

import pandas as pd


def _overview_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"tml_group": "TML", "base_metric": "publications", "metric_value": 43},
            {"tml_group": "non-TML", "base_metric": "publications", "metric_value": 57},
            {"tml_group": "TML", "base_metric": "reach", "metric_value": 721000},
            {"tml_group": "non-TML", "base_metric": "reach", "metric_value": 279000},
        ]
    )


def _narratives_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "narrative_id": "n1",
                "narrative_label": "Prime value and convenience",
                "row_count": 640,
                "total_mentions": 8100,
                "total_popularity": 230000.0,
                "avg_popularity": 359.4,
                "positive_pct": 0.49,
                "neutral_pct": 0.33,
                "negative_pct": 0.18,
                "campaign_pct": 0.41,
                "paid_pct": 0.09,
                "first_seen": pd.Timestamp("2026-01-05").date(),
                "last_seen": pd.Timestamp("2026-05-24").date(),
                "description": (
                    "Coverage centers on Amazon Prime's value proposition — fast, free shipping, "
                    "bundled streaming perks, and everyday convenience for members."
                ),
                "takeaway_1": "Prime membership growth is consistently framed as a win for customer convenience.",
                "takeaway_2": "Free same-day and next-day delivery remains the most cited driver of positive sentiment.",
                "takeaway_3": "Bundled perks (video, music, grocery discounts) are increasingly central to the narrative.",
            },
            {
                "narrative_id": "n2",
                "narrative_label": "Seller experience and fees",
                "row_count": 520,
                "total_mentions": 7400,
                "total_popularity": 180000.0,
                "avg_popularity": 346.1,
                "positive_pct": 0.22,
                "neutral_pct": 0.42,
                "negative_pct": 0.36,
                "campaign_pct": 0.28,
                "paid_pct": 0.06,
                "first_seen": pd.Timestamp("2026-01-08").date(),
                "last_seen": pd.Timestamp("2026-05-30").date(),
                "description": (
                    "Coverage focuses on third-party seller fees, marketplace policies, and the "
                    "balance of power between Amazon and the sellers who depend on its platform."
                ),
                "takeaway_1": "Rising referral and fulfillment fees are the dominant complaint among sellers.",
                "takeaway_2": "Sellers describe limited recourse when accounts are suspended or restricted.",
                "takeaway_3": "Some coverage highlights Amazon programs aimed at supporting small business sellers.",
            },
        ]
    )


def _media_type_monthly_fixture() -> pd.DataFrame:
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    media_types = ["Online", "Radio", "Newswire", "Print", "TV", "Podcast", "Blog", "Newsletter", "Video"]
    rows: list[dict[str, object]] = []
    for month_num, month_label in enumerate(month_labels, start=1):
        for media_type in media_types:
            pub = 8
            reach = 150000
            if media_type == "Online":
                pub = 120
                reach = 9800000
            elif media_type == "Radio":
                pub = 14
                reach = 1100000
            elif media_type == "Print":
                pub = 10
                reach = 650000
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "media_type": media_type,
                    "base_metric": "publications",
                    "metric_value": pub,
                }
            )
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "media_type": media_type,
                    "base_metric": "reach",
                    "metric_value": reach,
                }
            )
    return pd.DataFrame(rows)


def _media_type_period_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"media_type": "Online", "base_metric": "publications", "metric_value": 1440},
            {"media_type": "Radio", "base_metric": "publications", "metric_value": 168},
            {"media_type": "Newswire", "base_metric": "publications", "metric_value": 96},
            {"media_type": "Print", "base_metric": "publications", "metric_value": 120},
            {"media_type": "TV", "base_metric": "publications", "metric_value": 84},
            {"media_type": "Podcast", "base_metric": "publications", "metric_value": 72},
            {"media_type": "Blog", "base_metric": "publications", "metric_value": 60},
            {"media_type": "Newsletter", "base_metric": "publications", "metric_value": 48},
            {"media_type": "Video", "base_metric": "publications", "metric_value": 36},
            {"media_type": "Online", "base_metric": "reach", "metric_value": 117600000},
            {"media_type": "Radio", "base_metric": "reach", "metric_value": 13200000},
            {"media_type": "Newswire", "base_metric": "reach", "metric_value": 5400000},
            {"media_type": "Print", "base_metric": "reach", "metric_value": 7800000},
            {"media_type": "TV", "base_metric": "reach", "metric_value": 6900000},
            {"media_type": "Podcast", "base_metric": "reach", "metric_value": 3300000},
            {"media_type": "Blog", "base_metric": "reach", "metric_value": 2700000},
            {"media_type": "Newsletter", "base_metric": "reach", "metric_value": 2100000},
            {"media_type": "Video", "base_metric": "reach", "metric_value": 1800000},
        ]
    )


def _sentiment_monthly_fixture() -> pd.DataFrame:
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sentiments = ["Positive", "Neutral", "Negative"]
    rows: list[dict[str, object]] = []
    for month_num, month_label in enumerate(month_labels, start=1):
        for sentiment in sentiments:
            pub = 10
            reach = 1000000
            if sentiment == "Positive":
                pub = 54
                reach = 6800000
            elif sentiment == "Neutral":
                pub = 40
                reach = 5200000
            elif sentiment == "Negative":
                pub = 6
                reach = 900000
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "sentiment": sentiment,
                    "base_metric": "publications",
                    "metric_value": pub,
                }
            )
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "sentiment": sentiment,
                    "base_metric": "reach",
                    "metric_value": reach,
                }
            )
    return pd.DataFrame(rows)


def _sentiment_period_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"sentiment": "Positive", "base_metric": "publications", "metric_value": 648},
            {"sentiment": "Neutral", "base_metric": "publications", "metric_value": 480},
            {"sentiment": "Negative", "base_metric": "publications", "metric_value": 72},
            {"sentiment": "Positive", "base_metric": "reach", "metric_value": 81600000},
            {"sentiment": "Neutral", "base_metric": "reach", "metric_value": 62400000},
            {"sentiment": "Negative", "base_metric": "reach", "metric_value": 10800000},
        ]
    )


def _sentiment_source_monthly_fixture() -> pd.DataFrame:
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    rows: list[dict[str, object]] = []
    for month_num, month_label in enumerate(month_labels, start=1):
        for base_metric, trad_val, some_val in [
            ("publications", 94, 130),
            ("reach", 18500000, 9200),
        ]:
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "source_group": "Trad",
                    "base_metric": base_metric,
                    "metric_value": trad_val,
                }
            )
            rows.append(
                {
                    "month_num": month_num,
                    "month_label": month_label,
                    "source_group": "Some",
                    "base_metric": base_metric,
                    "metric_value": some_val,
                }
            )
    return pd.DataFrame(rows)


def _source_sentiment_monthly_fixture() -> pd.DataFrame:
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    sentiments = ["Positive", "Neutral", "Negative"]
    pubs_values = {
        "Trad": {"Positive": 54, "Neutral": 30, "Negative": 10},
        "Some": {"Positive": 46, "Neutral": 58, "Negative": 26},
        "Engagement": {"Positive": 5200, "Neutral": 3100, "Negative": 1400},
    }
    reach_values = {
        "Trad": {"Positive": 1200000, "Neutral": 680000, "Negative": 240000},
        "Some": {"Positive": 38000, "Neutral": 48000, "Negative": 22000},
        "Engagement": {"Positive": 5200, "Neutral": 3100, "Negative": 1400},
    }
    rows: list[dict[str, object]] = []
    for base_metric, val_map in (("publications", pubs_values), ("reach", reach_values)):
        for month_num, month_label in enumerate(month_labels, start=1):
            for source_group in ("Trad", "Some", "Engagement"):
                for sentiment in sentiments:
                    rows.append(
                        {
                            "month_num": month_num,
                            "month_label": month_label,
                            "source_group": source_group,
                            "sentiment": sentiment,
                            "base_metric": base_metric,
                            "metric_value": val_map[source_group][sentiment],
                        }
                    )
    return pd.DataFrame(rows)


def _overview_kpi_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "total_publications": 24600,
                "total_reach": 275900000,
                "total_posts": 1803,
                "total_engagement": 210751,
                "linked_publishers": 905,
                "trad_with_some": 42,
            }
        ]
    )


def _some_platform_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"platform": "twitter", "base_metric": "publications", "metric_value": 862},
            {"platform": "facebook", "base_metric": "publications", "metric_value": 803},
            {"platform": "instagram", "base_metric": "publications", "metric_value": 138},
            {"platform": "twitter", "base_metric": "reach", "metric_value": 55757},
            {"platform": "facebook", "base_metric": "reach", "metric_value": 89857},
            {"platform": "instagram", "base_metric": "reach", "metric_value": 65137},
        ]
    )


def _top_posts_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": "2026-02-09",
                "Platform": "facebook",
                "Author": "Bezprawnik",
                "Post_Content": "FedEx w InPost to jest bardzo...",
                "Sentiment": "Neutral",
                "Reach": 0,
                "Engagement": 33915,
            },
            {
                "Date": "2026-01-13",
                "Platform": "twitter",
                "Author": "Weronika",
                "Post_Content": "koniec ery Amazon Prime za ...",
                "Sentiment": "Negative",
                "Reach": 0,
                "Engagement": 3228,
            },
            {
                "Date": "2026-03-16",
                "Platform": "twitter",
                "Author": "Krzysztof Stanowski",
                "Post_Content": "Albo @RBrzoska przed chwila...",
                "Sentiment": "Neutral",
                "Reach": 0,
                "Engagement": 2863,
            },
        ]
    )


def _top_articles_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": "2025-10-20",
                "Media_Type": "Radio",
                "Publication": "Polskie Radio",
                "Title": "Wiadomosci",
                "Summary": "This radio report mentions a major global outage affecting Amazon services.",
                "URL": "https://example.com/article-1",
                "Sentiment": "Neutral",
                "Reach": 2195000,
            },
            {
                "Date": "2025-03-26",
                "Media_Type": "Radio",
                "Publication": "Polskie Radio",
                "Title": "Wstawaj, szkoda dnia",
                "Summary": "Broadcast coverage discusses announcements connected to Amazon MGM Studios.",
                "URL": "https://example.com/article-2",
                "Sentiment": "Neutral",
                "Reach": 2164000,
            },
            {
                "Date": "2025-04-04",
                "Media_Type": "Radio",
                "Publication": "Polskie Radio",
                "Title": "Wiadomosci",
                "Summary": "The broadcast includes criticism tied to policy discussions around Amazon.",
                "URL": "https://example.com/article-3",
                "Sentiment": "Neutral",
                "Reach": 2131000,
            },
            {
                "Date": "2025-06-30",
                "Media_Type": "Radio",
                "Publication": "TVN",
                "Title": "Wstawaj, szkoda dnia",
                "Summary": "Coverage references high-profile public events and Amazon leadership.",
                "URL": "https://example.com/article-4",
                "Sentiment": "Negative",
                "Reach": 1426000,
            },
        ]
    )


def _discover_items_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": "2026-03-16",
                "Source": "Trad",
                "Sentiment": "Neutral",
                "Publisher": "Polskie Radio",
                "Topic_Area": "Logistics",
                "Narrative": "Delivery Speed",
                "Media_Type": "Radio",
                "Title": "Wiadomosci",
                "Summary": "This radio report mentions a major global outage affecting Amazon services.",
                "URL": "https://example.com/article-1",
                "Reach": 2195000,
                "Engagement": 0,
                "Engagement_Positive": 0,
                "Engagement_Negative": 0,
                "Engagement_Neutral": 0,
                "Followers": 0,
                "Journalist": "Anna Kowalska",
                "Full_Text": (
                    "Polskie Radio reports that a major global cloud outage disrupted Amazon Web "
                    "Services for several hours overnight, affecting retail, streaming, and "
                    "logistics platforms worldwide. The broadcast notes that Amazon engineers "
                    "restored service gradually and issued a statement attributing the disruption "
                    "to a configuration error in one of its European data centres."
                ),
                "umap_x": 1.2,
                "umap_y": 3.4,
            },
            {
                "Date": "2026-03-10",
                "Source": "Trad",
                "Sentiment": "Negative",
                "Publisher": "TVN",
                "Topic_Area": "Workplace",
                "Narrative": "Worker Conditions",
                "Media_Type": "TV",
                "Title": "Wstawaj, szkoda dnia",
                "Summary": "Coverage references high-profile public events and Amazon leadership.",
                "URL": "https://example.com/article-4",
                "Reach": 1426000,
                "Engagement": 0,
                "Engagement_Positive": 0,
                "Engagement_Negative": 0,
                "Engagement_Neutral": 0,
                "Followers": 0,
                "Journalist": "Piotr Zalewski",
                "Full_Text": (
                    "TVN's morning show discusses recent public appearances by Amazon leadership, "
                    "framing the segment around how executives are responding to ongoing scrutiny "
                    "of workplace conditions at fulfillment centres across Poland. Guests debate "
                    "whether recently announced benefits go far enough to address worker concerns."
                ),
                "umap_x": -2.6,
                "umap_y": 0.8,
            },
            {
                "Date": "2026-02-09",
                "Source": "SoMe",
                "Sentiment": "Neutral",
                "Publisher": "Bezprawnik",
                "Topic_Area": "Logistics",
                "Narrative": "Delivery Speed",
                "Media_Type": "facebook",
                "Title": "FedEx w InPost to jest bardzo szybka opcja dostawy.",
                "Summary": "",
                "URL": "https://example.com/post-1",
                "Reach": 45000,
                "Engagement": 33915,
                "Engagement_Positive": 18200,
                "Engagement_Negative": 4100,
                "Engagement_Neutral": 11615,
                "Followers": 128000,
                "Journalist": "",
                "Full_Text": "FedEx w InPost to jest bardzo szybka opcja dostawy.",
                "umap_x": 1.5,
                "umap_y": 3.1,
            },
            {
                "Date": "2026-01-13",
                "Source": "SoMe",
                "Sentiment": "Negative",
                "Publisher": "Weronika",
                "Topic_Area": "Pricing",
                "Narrative": "Prime Subscription Value",
                "Media_Type": "twitter",
                "Title": "koniec ery Amazon Prime za darmo, podwyzki cen.",
                "Summary": "",
                "URL": "https://example.com/post-2",
                "Reach": 5200,
                "Engagement": 3228,
                "Engagement_Positive": 410,
                "Engagement_Negative": 2190,
                "Engagement_Neutral": 628,
                "Followers": 12400,
                "Journalist": "",
                "Full_Text": "koniec ery Amazon Prime za darmo, podwyzki cen.",
                "umap_x": -3.0,
                "umap_y": -1.5,
            },
            {
                "Date": "2025-12-16",
                "Source": "SoMe",
                "Sentiment": "Neutral",
                "Publisher": "Krzysztof Stanowski",
                "Topic_Area": "Brand",
                "Narrative": "Public Perception",
                "Media_Type": "twitter",
                "Title": "Albo @RBrzoska przed chwila ogloszenia o ekspansji.",
                "Summary": "",
                "URL": "https://example.com/post-3",
                "Reach": 89000,
                "Engagement": 2863,
                "Engagement_Positive": 1540,
                "Engagement_Negative": 320,
                "Engagement_Neutral": 1003,
                "Followers": 310000,
                "Journalist": "",
                "Full_Text": "Albo @RBrzoska przed chwila ogloszenia o ekspansji.",
                "umap_x": -2.4,
                "umap_y": 1.2,
            },
        ]
    )


def _publishers_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "publisher_uid": "p1",
                "display_name": "TechPulse",
                "total_items": 220,
                "trad_article_count": 92,
                "trad_total_reach": 830000,
                "trad_positive_pct": 0.48,
                "trad_negative_pct": 0.16,
                "some_post_count": 128,
                "some_total_reach": 620000,
                "some_total_engagement": 195000,
                "some_avg_engagement": 1523.4,
                "some_positive_pct": 0.51,
                "some_negative_pct": 0.18,
                "some_engagement_positive": 98000,
                "some_engagement_negative": 35000,
                "some_engagement_neutral": 62000,
                "tml_values": "TML, non-TML",
                "media_types": "Online, Print",
                "trad_dominant_media_type": "Online",
                "some_dominant_platform": "Instagram",
                "publisher_type": "Trad+SoMe",
                "platforms_url": "https://social.example.com/techpulse",
                "website_url": "https://techpulse.example.com",
                "combined_top_narratives": "Prime value and convenience",
                "trad_top_narratives": '[{"label":"Prime value and convenience","narrative_id":"n1","count":46,"value":420000},{"label":"Marketplace reliability","narrative_id":"n3","count":28,"value":260000}]',
                "some_top_narratives": '[{"label":"Prime value and convenience","narrative_id":"n1","count":61,"value":195000},{"label":"Amazon\'s AI Investment and Market Reactions","narrative_id":"n4","count":37,"value":148000}]',
            },
            {
                "publisher_uid": "p2",
                "display_name": "RetailWatch",
                "total_items": 170,
                "trad_article_count": 80,
                "trad_total_reach": 650000,
                "trad_positive_pct": 0.29,
                "trad_negative_pct": 0.34,
                "some_post_count": 90,
                "some_total_reach": 280000,
                "some_total_engagement": 121000,
                "some_avg_engagement": 1344.4,
                "some_positive_pct": 0.33,
                "some_negative_pct": 0.30,
                "some_engagement_positive": 38000,
                "some_engagement_negative": 41000,
                "some_engagement_neutral": 42000,
                "tml_values": "non-TML",
                "media_types": "Online, Radio",
                "trad_dominant_media_type": "Radio",
                "some_dominant_platform": "Facebook",
                "publisher_type": "Trad+SoMe",
                "platforms_url": "https://social.example.com/retailwatch",
                "website_url": "https://retailwatch.example.com",
                "combined_top_narratives": "Seller experience and fees",
                "trad_top_narratives": '[{"label":"Seller experience and fees","narrative_id":"n2","count":39,"value":298000},{"label":"Marketplace reliability","narrative_id":"n3","count":24,"value":181000}]',
                "some_top_narratives": '[{"label":"Seller experience and fees","narrative_id":"n2","count":42,"value":126000},{"label":"Europe\'s Digital Taxation Debate","narrative_id":"n5","count":19,"value":57000}]',
            },
            {
                "publisher_uid": "p3",
                "display_name": "Polskie Radio",
                "total_items": 64,
                "trad_article_count": 64,
                "trad_total_reach": 2140000,
                "trad_positive_pct": 0.12,
                "trad_negative_pct": 0.08,
                "some_post_count": 0,
                "some_total_reach": 0,
                "some_total_engagement": 0,
                "some_avg_engagement": 0,
                "some_positive_pct": 0,
                "some_negative_pct": 0,
                "some_engagement_positive": 0,
                "some_engagement_negative": 0,
                "some_engagement_neutral": 0,
                "tml_values": "TML",
                "media_types": "Radio",
                "trad_dominant_media_type": "Radio",
                "some_dominant_platform": "",
                "publisher_type": "Trad",
                "platforms_url": "",
                "website_url": "https://polskieradio.pl",
                "combined_top_narratives": "Marketplace reliability",
                "trad_top_narratives": '[{"label":"Marketplace reliability","narrative_id":"n3","count":41,"value":1310000},{"label":"Prime value and convenience","narrative_id":"n1","count":13,"value":482000}]',
                "some_top_narratives": "",
            },
            {
                "publisher_uid": "p4",
                "display_name": "Weronika",
                "total_items": 44,
                "trad_article_count": 0,
                "trad_total_reach": 0,
                "trad_positive_pct": 0,
                "trad_negative_pct": 0,
                "some_post_count": 44,
                "some_total_reach": 98000,
                "some_total_engagement": 35600,
                "some_avg_engagement": 809.1,
                "some_positive_pct": 0.18,
                "some_negative_pct": 0.42,
                "some_engagement_positive": 6400,
                "some_engagement_negative": 18900,
                "some_engagement_neutral": 10300,
                "tml_values": "",
                "media_types": "",
                "trad_dominant_media_type": "",
                "some_dominant_platform": "X",
                "publisher_type": "SoMe",
                "platforms_url": "https://x.example.com/weronika",
                "website_url": "",
                "combined_top_narratives": "Seller experience and fees",
                "trad_top_narratives": "",
                "some_top_narratives": '[{"label":"Seller experience and fees","narrative_id":"n2","count":21,"value":62000},{"label":"Controversial Documentary on Melania Trump","narrative_id":"c001","count":9,"value":21000}]',
            },
        ]
    )


def _publisher_trad_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    publisher_values = {
        ("p1", "TechPulse"): {
            "Positive": [(18, 210000), (12, 160000), (20, 190000), (16, 170000)],
            "Neutral": [(10, 90000), (13, 120000), (8, 85000), (7, 76000)],
            "Negative": [(4, 36000), (5, 48000), (2, 18000), (3, 26000)],
        },
        ("p2", "RetailWatch"): {
            "Positive": [(8, 70000), (9, 76000), (11, 82000), (7, 64000)],
            "Neutral": [(14, 115000), (12, 99000), (10, 88000), (13, 107000)],
            "Negative": [(7, 72000), (9, 85000), (5, 52000), (6, 61000)],
        },
        ("p3", "Polskie Radio"): {
            "Positive": [(2, 140000), (3, 180000), (1, 90000), (2, 130000)],
            "Neutral": [(11, 620000), (9, 540000), (13, 710000), (10, 590000)],
            "Negative": [(1, 60000), (2, 120000), (1, 55000), (1, 65000)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for (publisher_uid, display_name), sentiment_values in publisher_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (publications, reach) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "publisher_uid": publisher_uid,
                        "display_name": display_name,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "publications",
                        "metric_value": publications,
                    }
                )
                rows.append(
                    {
                        "publisher_uid": publisher_uid,
                        "display_name": display_name,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "reach",
                        "metric_value": reach,
                    }
                )
    return pd.DataFrame(rows)


def _publisher_some_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    publisher_values = {
        ("p1", "TechPulse"): {
            "Positive": [(22, 44000), (18, 39000), (24, 52000), (20, 47000)],
            "Neutral": [(16, 24000), (17, 26000), (13, 21000), (15, 23000)],
            "Negative": [(6, 9000), (8, 13000), (5, 7200), (7, 10100)],
        },
        ("p2", "RetailWatch"): {
            "Positive": [(9, 16000), (12, 21000), (10, 18000), (8, 14000)],
            "Neutral": [(12, 19000), (11, 17000), (14, 22000), (13, 20500)],
            "Negative": [(10, 15500), (9, 14300), (8, 12900), (11, 17100)],
        },
        ("p4", "Weronika"): {
            "Positive": [(3, 1400), (4, 2600), (2, 900), (5, 3800)],
            "Neutral": [(8, 5200), (7, 4300), (6, 3600), (9, 6100)],
            "Negative": [(9, 7100), (10, 8400), (7, 5600), (8, 6800)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for (publisher_uid, display_name), sentiment_values in publisher_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (posts, engagement) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "publisher_uid": publisher_uid,
                        "display_name": display_name,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "posts",
                        "metric_value": posts,
                    }
                )
                rows.append(
                    {
                        "publisher_uid": publisher_uid,
                        "display_name": display_name,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "engagement",
                        "metric_value": engagement,
                    }
                )
    return pd.DataFrame(rows)


def _publisher_topic_areas_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"publisher_uid": "p1", "topic_area": "Prime", "publication_count": 18},
            {"publisher_uid": "p1", "topic_area": "Marketplace", "publication_count": 11},
            {"publisher_uid": "p1", "topic_area": "Logistics", "publication_count": 7},
            {"publisher_uid": "p2", "topic_area": "Marketplace", "publication_count": 14},
            {"publisher_uid": "p2", "topic_area": "Advertising", "publication_count": 9},
            {"publisher_uid": "p3", "topic_area": "Technology", "publication_count": 10},
        ]
    )


def _publisher_some_topic_areas_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"publisher_uid": "p1", "topic_area": "Prime", "post_count": 15},
            {"publisher_uid": "p1", "topic_area": "Deals", "post_count": 9},
            {"publisher_uid": "p1", "topic_area": "Marketplace", "post_count": 6},
            {"publisher_uid": "p2", "topic_area": "Advertising", "post_count": 12},
            {"publisher_uid": "p2", "topic_area": "Marketplace", "post_count": 8},
            {"publisher_uid": "p4", "topic_area": "Technology", "post_count": 7},
        ]
    )

def _topic_area_breakdown_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"topic_area": "Prime", "theme": "Membership Value", "source": "Trad", "publications": 24, "reach": 4_200_000},
            {"topic_area": "Prime", "theme": "Delivery Speed", "source": "Trad", "publications": 16, "reach": 2_900_000},
            {"topic_area": "Marketplace", "theme": "Seller Policies", "source": "Trad", "publications": 19, "reach": 3_100_000},
            {"topic_area": "Marketplace", "theme": "Counterfeit Goods", "source": "Trad", "publications": 9, "reach": 1_400_000},
            {"topic_area": "Logistics", "theme": "Warehouse Operations", "source": "Trad", "publications": 12, "reach": 1_800_000},
            {"topic_area": "Advertising", "theme": "Sponsored Listings", "source": "Trad", "publications": 8, "reach": 1_100_000},
            {"topic_area": "Technology", "theme": "AI and Automation", "source": "Trad", "publications": 11, "reach": 1_600_000},
            {"topic_area": "Prime", "theme": "Membership Value", "source": "SoMe", "publications": 31, "reach": 540_000},
            {"topic_area": "Prime", "theme": "Deals and Promotions", "source": "SoMe", "publications": 22, "reach": 410_000},
            {"topic_area": "Marketplace", "theme": "Seller Policies", "source": "SoMe", "publications": 14, "reach": 260_000},
            {"topic_area": "Marketplace", "theme": "Counterfeit Goods", "source": "SoMe", "publications": 10, "reach": 180_000},
            {"topic_area": "Deals", "theme": "Flash Sales", "source": "SoMe", "publications": 18, "reach": 320_000},
            {"topic_area": "Advertising", "theme": "Sponsored Listings", "source": "SoMe", "publications": 7, "reach": 150_000},
            {"topic_area": "Technology", "theme": "AI and Automation", "source": "SoMe", "publications": 9, "reach": 210_000},
        ]
    )


def _topic_area_media_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"media_label": "Online", "topic_area": "Prime", "source": "Trad", "publications": 22, "reach": 3_900_000},
            {"media_label": "Online", "topic_area": "Marketplace", "source": "Trad", "publications": 14, "reach": 2_400_000},
            {"media_label": "Print", "topic_area": "Prime", "source": "Trad", "publications": 8, "reach": 1_500_000},
            {"media_label": "Print", "topic_area": "Logistics", "source": "Trad", "publications": 7, "reach": 1_300_000},
            {"media_label": "TV", "topic_area": "Advertising", "source": "Trad", "publications": 6, "reach": 2_100_000},
            {"media_label": "Newswire", "topic_area": "Marketplace", "source": "Trad", "publications": 5, "reach": 900_000},
            {"media_label": "Radio", "topic_area": "Technology", "source": "Trad", "publications": 4, "reach": 600_000},
            {"media_label": "twitter", "topic_area": "Prime", "source": "SoMe", "publications": 28, "reach": 480_000},
            {"media_label": "twitter", "topic_area": "Deals", "source": "SoMe", "publications": 16, "reach": 260_000},
            {"media_label": "instagram", "topic_area": "Prime", "source": "SoMe", "publications": 18, "reach": 390_000},
            {"media_label": "instagram", "topic_area": "Marketplace", "source": "SoMe", "publications": 9, "reach": 170_000},
            {"media_label": "facebook", "topic_area": "Advertising", "source": "SoMe", "publications": 7, "reach": 140_000},
            {"media_label": "facebook", "topic_area": "Technology", "source": "SoMe", "publications": 6, "reach": 110_000},
        ]
    )


def _publisher_top_publications_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "publisher_uid": "p1",
                "Date": "2026-01-15",
                "Source": "Trad",
                "Type": "Online",
                "Title": "Amazon Announces New Prime Benefits",
                "URL": "https://example.com/pub-1",
                "Sentiment": "Positive",
                "Reach": 450000,
                "Engagement": 0,
            },
            {
                "publisher_uid": "p1",
                "Date": "2026-02-20",
                "Source": "SoMe",
                "Type": "Twitter",
                "Title": "Big updates coming to Prime membership - stay tuned!",
                "URL": "https://example.com/pub-2",
                "Sentiment": "Positive",
                "Reach": 320000,
                "Engagement": 15800,
            },
            {
                "publisher_uid": "p1",
                "Date": "2026-03-10",
                "Source": "Trad",
                "Type": "Print",
                "Title": "Behind Amazon's Logistics Expansion",
                "URL": "https://example.com/pub-3",
                "Sentiment": "Neutral",
                "Reach": 210000,
                "Engagement": 0,
            },
            {
                "publisher_uid": "p1",
                "Date": "2026-01-28",
                "Source": "SoMe",
                "Type": "Instagram",
                "Title": "Unboxing the latest Amazon devices",
                "URL": "https://example.com/pub-4",
                "Sentiment": "Positive",
                "Reach": 180000,
                "Engagement": 9200,
            },
            {
                "publisher_uid": "p1",
                "Date": "2026-04-05",
                "Source": "Trad",
                "Type": "Radio",
                "Title": "Amazon faces scrutiny over warehouse conditions",
                "URL": "https://example.com/pub-5",
                "Sentiment": "Negative",
                "Reach": 165000,
                "Engagement": 0,
            },
        ]
    )


def _narrative_overview_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "narrative_label": "Prime value and convenience",
                "trad_publications": 640,
                "trad_reach": 12_400_000,
                "trad_positive_share_of_reach": 0.49,
                "trad_negative_share_of_reach": 0.18,
                "some_posts": 820,
                "some_reach": 9_800_000,
                "some_engagement": 430_000,
                "some_average_engagement": 524.4,
                "some_positive_share_of_reach": 0.52,
                "some_negative_share_of_reach": 0.12,
            },
            {
                "narrative_label": "Seller experience and fees",
                "trad_publications": 520,
                "trad_reach": 8_700_000,
                "trad_positive_share_of_reach": 0.22,
                "trad_negative_share_of_reach": 0.36,
                "some_posts": 610,
                "some_reach": 5_200_000,
                "some_engagement": 220_000,
                "some_average_engagement": 360.7,
                "some_positive_share_of_reach": 0.19,
                "some_negative_share_of_reach": 0.41,
            },
            {
                "narrative_label": "Warehouse working conditions",
                "trad_publications": 310,
                "trad_reach": 5_100_000,
                "trad_positive_share_of_reach": 0.08,
                "trad_negative_share_of_reach": 0.62,
                "some_posts": 450,
                "some_reach": 3_900_000,
                "some_engagement": 310_000,
                "some_average_engagement": 688.9,
                "some_positive_share_of_reach": 0.07,
                "some_negative_share_of_reach": 0.68,
            },
            {
                "narrative_label": "AI and job displacement",
                "trad_publications": 280,
                "trad_reach": 4_600_000,
                "trad_positive_share_of_reach": 0.15,
                "trad_negative_share_of_reach": 0.55,
                "some_posts": 380,
                "some_reach": 2_900_000,
                "some_engagement": 185_000,
                "some_average_engagement": 487.0,
                "some_positive_share_of_reach": 0.12,
                "some_negative_share_of_reach": 0.60,
            },
        ]
    )


def _angles_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "narrative_id": "n2",
                "narrative_label": "Seller experience and fees",
                "angle_id": "a-seller-pricing",
                "angle_label": "Prime Day pricing debate",
                "target_sentiment": "Negative",
                "publications": 34,
                "trad_publications": 28,
                "some_posts": 6,
                "reach": 3_400_000,
                "popularity": 81.7,
            },
            {
                "narrative_id": "n2",
                "narrative_label": "Seller experience and fees",
                "angle_id": "a-seller-fee-transparency",
                "angle_label": "Fee transparency complaints",
                "target_sentiment": "Negative",
                "publications": 22,
                "trad_publications": 16,
                "some_posts": 6,
                "reach": 1_900_000,
                "popularity": 54.5,
            },
            {
                "narrative_id": "n2",
                "narrative_label": "Seller experience and fees",
                "angle_id": "a-seller-policy-updates",
                "angle_label": "Marketplace policy updates",
                "target_sentiment": "Neutral",
                "publications": 14,
                "trad_publications": 9,
                "some_posts": 5,
                "reach": 980_000,
                "popularity": 33.5,
            },
            {
                "narrative_id": "n1",
                "narrative_label": "Prime value and convenience",
                "angle_id": "a-prime-delivery",
                "angle_label": "Fast delivery reliability",
                "target_sentiment": "Positive",
                "publications": 29,
                "trad_publications": 22,
                "some_posts": 7,
                "reach": 2_900_000,
                "popularity": 63.0,
            },
            {
                "narrative_id": "n1",
                "narrative_label": "Prime value and convenience",
                "angle_id": "a-prime-membership",
                "angle_label": "Membership value perception",
                "target_sentiment": "Positive",
                "publications": 18,
                "trad_publications": 5,
                "some_posts": 13,
                "reach": 1_560_000,
                "popularity": 51.7,
            },
            {
                "narrative_id": "n1",
                "narrative_label": "Prime value and convenience",
                "angle_label": "Subscription cost concerns",
                "target_sentiment": "Negative",
                "publications": 9,
                "trad_publications": 4,
                "some_posts": 5,
                "reach": 410_000,
                "popularity": 23.0,
            },
        ]
    )


def _narrative_weekly_reach_fixture() -> pd.DataFrame:
    narratives = [
        "Prime value and convenience",
        "Seller experience and fees",
        "Logistics and delivery",
        "AWS and cloud services",
    ]
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_reach = [9_200_000, 5_800_000, 3_400_000, 2_100_000]
    rows = []
    for (narrative, base), week in itertools.product(zip(narratives, base_reach), weeks):
        random.seed(hash((narrative, str(week))))
        rows.append(
            {
                "week_start": str(week.date()),
                "dominant_narrative": narrative,
                "weekly_reach": int(base * random.uniform(0.7, 1.3)),
                "weekly_publications": random.randint(10, 120),
            }
        )
    return pd.DataFrame(rows)


def _narratives_kpi_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "total_narratives": 4,
                "total_angles": 2,
                "pubs_in_narrative": 1750,
                "total_pubs": 2100,
                "posts_in_narrative": 2260,
                "total_posts": 2700,
                "campaign_items": 650,
                "total_items_campaign": 4800,
                "paid_items": 420,
                "top_some_heavy_narrative": "Prime value and convenience",
                "top_some_dominant_narrative": "Warehouse working conditions",
            }
        ]
    )


def _narrative_detail_kpi_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "narrative_label": "Prime value and convenience",
                "trad_publications": 640,
                "some_posts": 890,
                "some_engagement": 1_240_000,
                "campaign_items": 214,
                "total_items": 1530,
                "paid_items": 138,
            },
            {
                "narrative_label": "Seller experience and fees",
                "trad_publications": 520,
                "some_posts": 680,
                "some_engagement": 870_000,
                "campaign_items": 95,
                "total_items": 1200,
                "paid_items": 62,
            },
            {
                "narrative_label": "Logistics and delivery",
                "trad_publications": 380,
                "some_posts": 510,
                "some_engagement": 620_000,
                "campaign_items": 71,
                "total_items": 890,
                "paid_items": 43,
            },
            {
                "narrative_label": "AWS and cloud services",
                "trad_publications": 210,
                "some_posts": 330,
                "some_engagement": 410_000,
                "campaign_items": 38,
                "total_items": 540,
                "paid_items": 27,
            },
        ]
    )


def _narrative_some_weekly_engagement_fixture() -> pd.DataFrame:
    narratives = [
        "Prime value and convenience",
        "Seller experience and fees",
        "Logistics and delivery",
        "AWS and cloud services",
    ]
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_engagement = [1_400_000, 870_000, 520_000, 310_000]
    rows = []
    for (narrative, base), week in itertools.product(zip(narratives, base_engagement), weeks):
        random.seed(hash((narrative, str(week), "some")))
        rows.append(
            {
                "week_start": str(week.date()),
                "dominant_narrative": narrative,
                "weekly_engagement": int(base * random.uniform(0.6, 1.4)),
                "weekly_posts": random.randint(5, 80),
            }
        )
    return pd.DataFrame(rows)


def _narrative_trad_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    narrative_values = {
        "Prime value and convenience": {
            "Positive": [(18, 210000), (12, 160000), (20, 190000), (16, 170000)],
            "Neutral": [(10, 90000), (13, 120000), (8, 85000), (7, 76000)],
            "Negative": [(4, 36000), (5, 48000), (2, 18000), (3, 26000)],
        },
        "Seller experience and fees": {
            "Positive": [(8, 70000), (9, 76000), (11, 82000), (7, 64000)],
            "Neutral": [(14, 115000), (12, 99000), (10, 88000), (13, 107000)],
            "Negative": [(7, 72000), (9, 85000), (5, 52000), (6, 61000)],
        },
        "Logistics and delivery": {
            "Positive": [(2, 140000), (3, 180000), (1, 90000), (2, 130000)],
            "Neutral": [(11, 620000), (9, 540000), (13, 710000), (10, 590000)],
            "Negative": [(1, 60000), (2, 120000), (1, 55000), (1, 65000)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for narrative_label, sentiment_values in narrative_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (publications, reach) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "publications",
                        "metric_value": publications,
                    }
                )
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "reach",
                        "metric_value": reach,
                    }
                )
    return pd.DataFrame(rows)


def _narrative_trad_media_type_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    narrative_values = {
        "Prime value and convenience": {
            "Online": [20, 18, 24, 22],
            "Print": [6, 5, 7, 6],
            "TV": [3, 4, 2, 3],
        },
        "Seller experience and fees": {
            "Online": [14, 16, 12, 15],
            "Newswire": [5, 6, 4, 5],
            "Radio": [2, 3, 2, 3],
        },
        "Logistics and delivery": {
            "Online": [9, 11, 8, 10],
            "Print": [3, 2, 4, 3],
            "Podcast": [1, 2, 1, 2],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for narrative_label, media_values in narrative_values.items():
        for media_type, weekly_values in media_values.items():
            for week_start, publications in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "media_type": media_type,
                        "publications": publications,
                    }
                )
    return pd.DataFrame(rows)


def _narrative_some_platform_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    narrative_values = {
        "Prime value and convenience": {
            "twitter": [28, 24, 30, 26],
            "facebook": [10, 12, 9, 11],
            "instagram": [6, 7, 5, 8],
        },
        "Seller experience and fees": {
            "twitter": [16, 18, 14, 17],
            "facebook": [9, 8, 10, 9],
            "instagram": [4, 5, 3, 4],
        },
        "AWS and cloud services": {
            "twitter": [8, 7, 9, 10],
            "facebook": [3, 4, 2, 3],
            "instagram": [2, 3, 2, 3],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for narrative_label, platform_values in narrative_values.items():
        for platform, weekly_values in platform_values.items():
            for week_start, posts in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "platform": platform,
                        "posts": posts,
                    }
                )
    return pd.DataFrame(rows)


def _archive_scatter_fixture() -> pd.DataFrame:
    narratives = [
        "Prime value and convenience",
        "Seller experience and fees",
        "Logistics and delivery",
        "AWS and cloud services",
        "Noise",
    ]
    centers = [(2, 2), (-3, 1), (0, -3), (4, -2), (-1, -1)]
    rows: list[dict[str, object]] = []
    for source, n_per_cluster in (("Trad", 60), ("SoMe", 40)):
        for narrative, (cx, cy) in zip(narratives, centers):
            random.seed(hash((narrative, source)))
            spread = 2.5 if narrative == "Noise" else 0.9
            for _ in range(n_per_cluster):
                rows.append(
                    {
                        "umap_x": cx + random.gauss(0, spread),
                        "umap_y": cy + random.gauss(0, spread),
                        "narrative_label": narrative,
                        "source": source,
                    }
                )
    return pd.DataFrame(rows)


def _narrative_some_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    narrative_values = {
        "Prime value and convenience": {
            "Positive": [(22, 44000), (18, 39000), (24, 52000), (20, 47000)],
            "Neutral": [(16, 24000), (17, 26000), (13, 21000), (15, 23000)],
            "Negative": [(6, 9000), (8, 13000), (5, 7200), (7, 10100)],
        },
        "Seller experience and fees": {
            "Positive": [(9, 16000), (12, 21000), (10, 18000), (8, 14000)],
            "Neutral": [(12, 19000), (11, 17000), (14, 22000), (13, 20500)],
            "Negative": [(10, 15500), (9, 14300), (8, 12900), (11, 17100)],
        },
        "AWS and cloud services": {
            "Positive": [(3, 1400), (4, 2600), (2, 900), (5, 3800)],
            "Neutral": [(8, 5200), (7, 4300), (6, 3600), (9, 6100)],
            "Negative": [(9, 7100), (10, 8400), (7, 5600), (8, 6800)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for narrative_label, sentiment_values in narrative_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (posts, engagement) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "posts",
                        "metric_value": posts,
                    }
                )
                rows.append(
                    {
                        "narrative_label": narrative_label,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "engagement",
                        "metric_value": engagement,
                    }
                )
    return pd.DataFrame(rows)


def _narrative_top_publishers_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "Trad", "narrative_label": "Prime value and convenience", "publisher": "Reuters", "media_type_platform": "Online", "reach": 2_400_000, "publications": 5},
            {"source": "Trad", "narrative_label": "Prime value and convenience", "publisher": "The Verge", "media_type_platform": "Online", "reach": 1_650_000, "publications": 3},
            {"source": "Trad", "narrative_label": "Prime value and convenience", "publisher": "CNBC", "media_type_platform": "TV", "reach": 980_000, "publications": 2},
            {"source": "SoMe", "narrative_label": "Prime value and convenience", "publisher": "Krzysztof Stanowski", "media_type_platform": "twitter", "reach": 540_000, "publications": 4},
            {"source": "SoMe", "narrative_label": "Prime value and convenience", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 310_000, "publications": 2},
            {"source": "Trad", "narrative_label": "Seller experience and fees", "publisher": "Bloomberg", "media_type_platform": "Online", "reach": 1_900_000, "publications": 4},
            {"source": "Trad", "narrative_label": "Seller experience and fees", "publisher": "Forbes", "media_type_platform": "Online", "reach": 870_000, "publications": 2},
            {"source": "SoMe", "narrative_label": "Seller experience and fees", "publisher": "Weronika", "media_type_platform": "twitter", "reach": 420_000, "publications": 3},
            {"source": "Trad", "narrative_label": "Warehouse working conditions", "publisher": "The Guardian", "media_type_platform": "Online", "reach": 2_100_000, "publications": 6},
            {"source": "Trad", "narrative_label": "Warehouse working conditions", "publisher": "BBC", "media_type_platform": "TV", "reach": 1_400_000, "publications": 3},
            {"source": "SoMe", "narrative_label": "Warehouse working conditions", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 760_000, "publications": 5},
        ]
    )


def _narrative_top_journalists_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"narrative_label": "Prime value and convenience", "journalist": "Anna Kowalska", "publications": 14, "reach": 3_200_000},
            {"narrative_label": "Prime value and convenience", "journalist": "James Patterson", "publications": 9, "reach": 1_750_000},
            {"narrative_label": "Prime value and convenience", "journalist": "Marek Nowak", "publications": 6, "reach": 980_000},
            {"narrative_label": "Seller experience and fees", "journalist": "Sarah Connolly", "publications": 11, "reach": 2_400_000},
            {"narrative_label": "Seller experience and fees", "journalist": "Tomasz Wisniewski", "publications": 7, "reach": 1_100_000},
            {"narrative_label": "Warehouse working conditions", "journalist": "Emily Carter", "publications": 17, "reach": 4_300_000},
            {"narrative_label": "Warehouse working conditions", "journalist": "Piotr Zalewski", "publications": 8, "reach": 1_550_000},
        ]
    )


def _narrative_top_publications_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "narrative_label": "Prime value and convenience",
                "Date": "2026-01-15",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Reuters",
                "Author": None,
                "Title": "Amazon Announces New Prime Benefits",
                "Summary": "Amazon expands Prime membership perks for 2026.",
                "URL": "https://example.com/narrative-pub-1",
                "Sentiment": "Positive",
                "Reach": 2_400_000,
                "Engagement": 0,
                "Angle_ID": "a-prime-delivery",
                "Angle": "Fast delivery reliability",
            },
            {
                "narrative_label": "Prime value and convenience",
                "Date": "2026-02-20",
                "Source": "SoMe",
                "Type": "Twitter",
                "Publication": None,
                "Author": "Krzysztof Stanowski",
                "Title": "",
                "Summary": "Big updates coming to Prime membership - stay tuned!",
                "URL": "https://example.com/narrative-pub-2",
                "Sentiment": "Positive",
                "Reach": 540_000,
                "Engagement": 15_800,
                "Angle_ID": "a-prime-membership",
                "Angle": "Membership value perception",
            },
            {
                "narrative_label": "Seller experience and fees",
                "Date": "2026-03-10",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Bloomberg",
                "Author": None,
                "Title": "Sellers Push Back on Amazon Fee Increases",
                "Summary": "Marketplace sellers raise concerns over rising fees.",
                "URL": "https://example.com/narrative-pub-3",
                "Sentiment": "Negative",
                "Reach": 1_900_000,
                "Engagement": 0,
                "Angle_ID": "a-seller-pricing",
                "Angle": "Prime Day pricing debate",
            },
            {
                "narrative_label": "Warehouse working conditions",
                "Date": "2026-04-05",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "The Guardian",
                "Author": None,
                "Title": "Amazon Faces Scrutiny Over Warehouse Conditions",
                "Summary": "Investigation highlights working conditions at fulfillment centers.",
                "URL": "https://example.com/narrative-pub-4",
                "Sentiment": "Negative",
                "Reach": 2_100_000,
                "Engagement": 0,
                "Angle_ID": "",
                "Angle": "",
            },
            {
                "narrative_label": "Warehouse working conditions",
                "Date": "2026-04-08",
                "Source": "SoMe",
                "Type": "Facebook",
                "Publication": None,
                "Author": "Bezprawnik",
                "Title": "",
                "Summary": "Reaction to the latest warehouse conditions report.",
                "URL": "https://example.com/narrative-pub-5",
                "Sentiment": "Negative",
                "Reach": 760_000,
                "Engagement": 22_400,
                "Angle_ID": "",
                "Angle": "",
            },
        ]
    )


def _campaign_timeline_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"campaign": "Prime Day 2025", "start_date": "2026-01-15", "end_date": "2026-02-10",
             "total_reach": 6_935_285, "trad_reach": 5_200_000, "some_reach": 1_735_285, "items": 184},
            {"campaign": "(Un)aware Consumer", "start_date": "2026-01-20", "end_date": "2026-03-02",
             "total_reach": 2_447_855, "trad_reach": 2_100_000, "some_reach": 347_855, "items": 96},
            {"campaign": "Unboxing", "start_date": "2026-02-12", "end_date": "2026-03-28",
             "total_reach": 2_378_119, "trad_reach": 1_400_000, "some_reach": 978_119, "items": 132},
            {"campaign": "EFNI 2025", "start_date": "2026-02-25", "end_date": "2026-04-18",
             "total_reach": 1_015_546, "trad_reach": 820_000, "some_reach": 195_546, "items": 58},
            {"campaign": "Amazon Fund", "start_date": "2026-03-05", "end_date": "2026-05-30",
             "total_reach": 602_610, "trad_reach": 410_000, "some_reach": 192_610, "items": 41},
            {"campaign": "RNCF & Kampinos National Park", "start_date": "2026-09-22", "end_date": "2026-10-12",
             "total_reach": 2_580_955, "trad_reach": 2_200_000, "some_reach": 380_955, "items": 77},
            {"campaign": "Black Friday Week", "start_date": "2026-11-18", "end_date": "2026-11-30",
             "total_reach": 3_510_136, "trad_reach": 2_650_000, "some_reach": 860_136, "items": 142},
            {"campaign": "HOL25", "start_date": "2026-12-01", "end_date": "2026-12-22",
             "total_reach": 206_833, "trad_reach": 120_000, "some_reach": 86_833, "items": 19},
        ]
    )


_CAMPAIGN_NAMES = [
    "Prime Day 2025",
    "(Un)aware Consumer",
    "Unboxing",
    "EFNI 2025",
    "Amazon Fund",
    "RNCF & Kampinos National Park",
    "Black Friday Week",
    "HOL25",
]


def _topic_area_campaigns_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign": "Prime Day 2025",
                "trad_article_count": 112,
                "trad_total_reach": 5_200_000,
                "trad_positive_pct": 0.46,
                "trad_negative_pct": 0.12,
                "some_post_count": 72,
                "some_total_reach": 1_735_285,
                "some_total_engagement": 412_000,
                "some_avg_engagement": 5722.2,
                "some_positive_pct": 0.52,
                "some_negative_pct": 0.10,
                "some_engagement_positive": 214_240,
                "some_engagement_negative": 41_200,
                "some_engagement_neutral": 156_560,
            },
            {
                "campaign": "(Un)aware Consumer",
                "trad_article_count": 64,
                "trad_total_reach": 2_100_000,
                "trad_positive_pct": 0.21,
                "trad_negative_pct": 0.31,
                "some_post_count": 32,
                "some_total_reach": 347_855,
                "some_total_engagement": 88_400,
                "some_avg_engagement": 2762.5,
                "some_positive_pct": 0.24,
                "some_negative_pct": 0.29,
                "some_engagement_positive": 21_216,
                "some_engagement_negative": 25_636,
                "some_engagement_neutral": 41_548,
            },
            {
                "campaign": "Unboxing",
                "trad_article_count": 38,
                "trad_total_reach": 1_400_000,
                "trad_positive_pct": 0.58,
                "trad_negative_pct": 0.05,
                "some_post_count": 94,
                "some_total_reach": 978_119,
                "some_total_engagement": 256_300,
                "some_avg_engagement": 2726.6,
                "some_positive_pct": 0.61,
                "some_negative_pct": 0.04,
                "some_engagement_positive": 156_343,
                "some_engagement_negative": 10_252,
                "some_engagement_neutral": 89_705,
            },
            {
                "campaign": "EFNI 2025",
                "trad_article_count": 41,
                "trad_total_reach": 820_000,
                "trad_positive_pct": 0.35,
                "trad_negative_pct": 0.09,
                "some_post_count": 17,
                "some_total_reach": 195_546,
                "some_total_engagement": 41_200,
                "some_avg_engagement": 2423.5,
                "some_positive_pct": 0.39,
                "some_negative_pct": 0.07,
                "some_engagement_positive": 16_068,
                "some_engagement_negative": 2_884,
                "some_engagement_neutral": 22_248,
            },
            {
                "campaign": "Amazon Fund",
                "trad_article_count": 26,
                "trad_total_reach": 410_000,
                "trad_positive_pct": 0.52,
                "trad_negative_pct": 0.06,
                "some_post_count": 15,
                "some_total_reach": 192_610,
                "some_total_engagement": 38_900,
                "some_avg_engagement": 2593.3,
                "some_positive_pct": 0.55,
                "some_negative_pct": 0.05,
                "some_engagement_positive": 21_395,
                "some_engagement_negative": 1_945,
                "some_engagement_neutral": 15_560,
            },
            {
                "campaign": "RNCF & Kampinos National Park",
                "trad_article_count": 53,
                "trad_total_reach": 2_200_000,
                "trad_positive_pct": 0.61,
                "trad_negative_pct": 0.04,
                "some_post_count": 24,
                "some_total_reach": 380_955,
                "some_total_engagement": 71_500,
                "some_avg_engagement": 2979.2,
                "some_positive_pct": 0.64,
                "some_negative_pct": 0.03,
                "some_engagement_positive": 45_760,
                "some_engagement_negative": 2_145,
                "some_engagement_neutral": 23_595,
            },
            {
                "campaign": "Black Friday Week",
                "trad_article_count": 89,
                "trad_total_reach": 2_650_000,
                "trad_positive_pct": 0.43,
                "trad_negative_pct": 0.14,
                "some_post_count": 53,
                "some_total_reach": 860_136,
                "some_total_engagement": 198_700,
                "some_avg_engagement": 3749.1,
                "some_positive_pct": 0.47,
                "some_negative_pct": 0.12,
                "some_engagement_positive": 93_389,
                "some_engagement_negative": 23_844,
                "some_engagement_neutral": 81_467,
            },
            {
                "campaign": "HOL25",
                "trad_article_count": 12,
                "trad_total_reach": 120_000,
                "trad_positive_pct": 0.50,
                "trad_negative_pct": 0.08,
                "some_post_count": 7,
                "some_total_reach": 86_833,
                "some_total_engagement": 19_400,
                "some_avg_engagement": 2771.4,
                "some_positive_pct": 0.53,
                "some_negative_pct": 0.07,
                "some_engagement_positive": 10_282,
                "some_engagement_negative": 1_358,
                "some_engagement_neutral": 7_760,
            },
        ]
    )


def _campaign_weekly_reach_fixture() -> pd.DataFrame:
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_reach = [9_200_000, 5_800_000, 3_400_000, 2_100_000, 1_400_000, 2_600_000, 3_900_000, 950_000]
    rows = []
    for (campaign, base), week in itertools.product(zip(_CAMPAIGN_NAMES, base_reach), weeks):
        random.seed(hash((campaign, str(week))))
        rows.append(
            {
                "week_start": str(week.date()),
                "campaign": campaign,
                "weekly_reach": int(base * random.uniform(0.7, 1.3)),
                "weekly_publications": random.randint(10, 120),
            }
        )
    return pd.DataFrame(rows)


def _campaign_some_weekly_engagement_fixture() -> pd.DataFrame:
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_engagement = [1_400_000, 870_000, 520_000, 310_000, 210_000, 380_000, 640_000, 145_000]
    rows = []
    for (campaign, base), week in itertools.product(zip(_CAMPAIGN_NAMES, base_engagement), weeks):
        random.seed(hash((campaign, str(week), "some")))
        rows.append(
            {
                "week_start": str(week.date()),
                "campaign": campaign,
                "weekly_engagement": int(base * random.uniform(0.6, 1.4)),
                "weekly_posts": random.randint(5, 80),
            }
        )
    return pd.DataFrame(rows)


def _campaign_trad_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    campaign_values = {
        "Prime Day 2025": {
            "Positive": [(18, 210000), (12, 160000), (20, 190000), (16, 170000)],
            "Neutral": [(10, 90000), (13, 120000), (8, 85000), (7, 76000)],
            "Negative": [(4, 36000), (5, 48000), (2, 18000), (3, 26000)],
        },
        "(Un)aware Consumer": {
            "Positive": [(8, 70000), (9, 76000), (11, 82000), (7, 64000)],
            "Neutral": [(14, 115000), (12, 99000), (10, 88000), (13, 107000)],
            "Negative": [(7, 72000), (9, 85000), (5, 52000), (6, 61000)],
        },
        "Unboxing": {
            "Positive": [(2, 140000), (3, 180000), (1, 90000), (2, 130000)],
            "Neutral": [(11, 620000), (9, 540000), (13, 710000), (10, 590000)],
            "Negative": [(1, 60000), (2, 120000), (1, 55000), (1, 65000)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for campaign, sentiment_values in campaign_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (publications, reach) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "campaign": campaign,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "publications",
                        "metric_value": publications,
                    }
                )
                rows.append(
                    {
                        "campaign": campaign,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "reach",
                        "metric_value": reach,
                    }
                )
    return pd.DataFrame(rows)


def _campaign_some_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    campaign_values = {
        "Prime Day 2025": {
            "Positive": [(22, 44000), (18, 39000), (24, 52000), (20, 47000)],
            "Neutral": [(16, 24000), (17, 26000), (13, 21000), (15, 23000)],
            "Negative": [(6, 9000), (8, 13000), (5, 7200), (7, 10100)],
        },
        "(Un)aware Consumer": {
            "Positive": [(9, 16000), (12, 21000), (10, 18000), (8, 14000)],
            "Neutral": [(12, 19000), (11, 17000), (14, 22000), (13, 20500)],
            "Negative": [(10, 15500), (9, 14300), (8, 12900), (11, 17100)],
        },
        "Unboxing": {
            "Positive": [(3, 1400), (4, 2600), (2, 900), (5, 3800)],
            "Neutral": [(8, 5200), (7, 4300), (6, 3600), (9, 6100)],
            "Negative": [(9, 7100), (10, 8400), (7, 5600), (8, 6800)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for campaign, sentiment_values in campaign_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (posts, engagement) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "campaign": campaign,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "posts",
                        "metric_value": posts,
                    }
                )
                rows.append(
                    {
                        "campaign": campaign,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "engagement",
                        "metric_value": engagement,
                    }
                )
    return pd.DataFrame(rows)


def _campaign_top_publishers_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "Trad", "campaign": "Prime Day 2025", "publisher": "Reuters", "media_type_platform": "Online", "reach": 2_400_000, "publications": 5},
            {"source": "Trad", "campaign": "Prime Day 2025", "publisher": "The Verge", "media_type_platform": "Online", "reach": 1_650_000, "publications": 3},
            {"source": "Trad", "campaign": "Prime Day 2025", "publisher": "CNBC", "media_type_platform": "TV", "reach": 980_000, "publications": 2},
            {"source": "SoMe", "campaign": "Prime Day 2025", "publisher": "Krzysztof Stanowski", "media_type_platform": "twitter", "reach": 540_000, "publications": 4},
            {"source": "SoMe", "campaign": "Prime Day 2025", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 310_000, "publications": 2},
            {"source": "Trad", "campaign": "(Un)aware Consumer", "publisher": "Bloomberg", "media_type_platform": "Online", "reach": 1_900_000, "publications": 4},
            {"source": "Trad", "campaign": "(Un)aware Consumer", "publisher": "Forbes", "media_type_platform": "Online", "reach": 870_000, "publications": 2},
            {"source": "SoMe", "campaign": "(Un)aware Consumer", "publisher": "Weronika", "media_type_platform": "twitter", "reach": 420_000, "publications": 3},
            {"source": "Trad", "campaign": "Unboxing", "publisher": "The Guardian", "media_type_platform": "Online", "reach": 2_100_000, "publications": 6},
            {"source": "Trad", "campaign": "Unboxing", "publisher": "BBC", "media_type_platform": "TV", "reach": 1_400_000, "publications": 3},
            {"source": "SoMe", "campaign": "Unboxing", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 760_000, "publications": 5},
        ]
    )


def _campaign_top_journalists_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"campaign": "Prime Day 2025", "journalist": "Anna Kowalska", "publications": 14, "reach": 3_200_000},
            {"campaign": "Prime Day 2025", "journalist": "James Patterson", "publications": 9, "reach": 1_750_000},
            {"campaign": "Prime Day 2025", "journalist": "Marek Nowak", "publications": 6, "reach": 980_000},
            {"campaign": "(Un)aware Consumer", "journalist": "Sarah Connolly", "publications": 11, "reach": 2_400_000},
            {"campaign": "(Un)aware Consumer", "journalist": "Tomasz Wisniewski", "publications": 7, "reach": 1_100_000},
            {"campaign": "Unboxing", "journalist": "Emily Carter", "publications": 17, "reach": 4_300_000},
            {"campaign": "Unboxing", "journalist": "Piotr Zalewski", "publications": 8, "reach": 1_550_000},
        ]
    )


def _campaign_top_publications_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign": "Prime Day 2025",
                "Date": "2026-01-15",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Reuters",
                "Author": None,
                "Title": "Amazon Announces New Prime Benefits",
                "Summary": "Amazon expands Prime membership perks for 2026.",
                "URL": "https://example.com/campaign-pub-1",
                "Sentiment": "Positive",
                "Reach": 2_400_000,
                "Engagement": 0,
                "Angle": "Fast delivery reliability",
            },
            {
                "campaign": "Prime Day 2025",
                "Date": "2026-02-20",
                "Source": "SoMe",
                "Type": "Twitter",
                "Publication": None,
                "Author": "Krzysztof Stanowski",
                "Title": "",
                "Summary": "Big updates coming to Prime Day - stay tuned!",
                "URL": "https://example.com/campaign-pub-2",
                "Sentiment": "Positive",
                "Reach": 540_000,
                "Engagement": 15_800,
                "Angle": "Membership value perception",
            },
            {
                "campaign": "(Un)aware Consumer",
                "Date": "2026-03-10",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Bloomberg",
                "Author": None,
                "Title": "Consumers Push Back on Pricing Transparency",
                "Summary": "Shoppers raise concerns over pricing clarity.",
                "URL": "https://example.com/campaign-pub-3",
                "Sentiment": "Negative",
                "Reach": 1_900_000,
                "Engagement": 0,
                "Angle": "Pricing transparency debate",
            },
            {
                "campaign": "Unboxing",
                "Date": "2026-04-05",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "The Guardian",
                "Author": None,
                "Title": "Unboxing Trend Drives Engagement",
                "Summary": "Unboxing content drives strong engagement across channels.",
                "URL": "https://example.com/campaign-pub-4",
                "Sentiment": "Neutral",
                "Reach": 2_100_000,
                "Engagement": 0,
                "Angle": "",
            },
            {
                "campaign": "Unboxing",
                "Date": "2026-04-08",
                "Source": "SoMe",
                "Type": "Facebook",
                "Publication": None,
                "Author": "Bezprawnik",
                "Title": "",
                "Summary": "Reaction to the latest unboxing video.",
                "URL": "https://example.com/campaign-pub-5",
                "Sentiment": "Positive",
                "Reach": 760_000,
                "Engagement": 22_400,
                "Angle": "",
            },
        ]
    )


_TOPIC_AREA_NAMES = ["Prime", "Marketplace", "Logistics", "Advertising", "Technology", "Deals"]


def _topic_area_overview_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "topic_area": "Prime",
                "trad_article_count": 128,
                "trad_total_reach": 6_100_000,
                "trad_positive_pct": 0.48,
                "trad_negative_pct": 0.11,
                "some_post_count": 86,
                "some_total_reach": 1_950_000,
                "some_total_engagement": 470_000,
                "some_avg_engagement": 5465.1,
                "some_positive_pct": 0.53,
                "some_negative_pct": 0.09,
                "some_engagement_positive": 249_100,
                "some_engagement_negative": 42_300,
                "some_engagement_neutral": 178_600,
            },
            {
                "topic_area": "Marketplace",
                "trad_article_count": 94,
                "trad_total_reach": 4_300_000,
                "trad_positive_pct": 0.38,
                "trad_negative_pct": 0.18,
                "some_post_count": 61,
                "some_total_reach": 1_210_000,
                "some_total_engagement": 305_000,
                "some_avg_engagement": 5000.0,
                "some_positive_pct": 0.40,
                "some_negative_pct": 0.20,
                "some_engagement_positive": 122_000,
                "some_engagement_negative": 61_000,
                "some_engagement_neutral": 122_000,
            },
            {
                "topic_area": "Logistics",
                "trad_article_count": 71,
                "trad_total_reach": 3_100_000,
                "trad_positive_pct": 0.55,
                "trad_negative_pct": 0.08,
                "some_post_count": 39,
                "some_total_reach": 690_000,
                "some_total_engagement": 158_000,
                "some_avg_engagement": 4051.3,
                "some_positive_pct": 0.58,
                "some_negative_pct": 0.07,
                "some_engagement_positive": 91_640,
                "some_engagement_negative": 11_060,
                "some_engagement_neutral": 55_300,
            },
            {
                "topic_area": "Advertising",
                "trad_article_count": 52,
                "trad_total_reach": 2_300_000,
                "trad_positive_pct": 0.42,
                "trad_negative_pct": 0.14,
                "some_post_count": 47,
                "some_total_reach": 920_000,
                "some_total_engagement": 214_000,
                "some_avg_engagement": 4553.2,
                "some_positive_pct": 0.45,
                "some_negative_pct": 0.13,
                "some_engagement_positive": 96_300,
                "some_engagement_negative": 27_820,
                "some_engagement_neutral": 89_880,
            },
            {
                "topic_area": "Technology",
                "trad_article_count": 63,
                "trad_total_reach": 2_700_000,
                "trad_positive_pct": 0.50,
                "trad_negative_pct": 0.06,
                "some_post_count": 55,
                "some_total_reach": 1_040_000,
                "some_total_engagement": 248_000,
                "some_avg_engagement": 4509.1,
                "some_positive_pct": 0.54,
                "some_negative_pct": 0.05,
                "some_engagement_positive": 133_920,
                "some_engagement_negative": 12_400,
                "some_engagement_neutral": 101_680,
            },
            {
                "topic_area": "Deals",
                "trad_article_count": 105,
                "trad_total_reach": 4_800_000,
                "trad_positive_pct": 0.44,
                "trad_negative_pct": 0.13,
                "some_post_count": 78,
                "some_total_reach": 1_620_000,
                "some_total_engagement": 398_000,
                "some_avg_engagement": 5102.6,
                "some_positive_pct": 0.49,
                "some_negative_pct": 0.11,
                "some_engagement_positive": 195_020,
                "some_engagement_negative": 43_780,
                "some_engagement_neutral": 159_200,
            },
        ]
    )


def _topic_area_weekly_reach_fixture() -> pd.DataFrame:
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_reach = [7_600_000, 5_400_000, 3_900_000, 2_900_000, 3_400_000, 6_000_000]
    rows = []
    for (topic_area, base), week in itertools.product(zip(_TOPIC_AREA_NAMES, base_reach), weeks):
        random.seed(hash((topic_area, str(week))))
        rows.append(
            {
                "week_start": str(week.date()),
                "topic_area": topic_area,
                "weekly_reach": int(base * random.uniform(0.7, 1.3)),
                "weekly_publications": random.randint(10, 120),
            }
        )
    return pd.DataFrame(rows)


def _topic_area_some_weekly_engagement_fixture() -> pd.DataFrame:
    weeks = pd.date_range("2026-01-06", periods=20, freq="W-MON")
    base_engagement = [1_200_000, 760_000, 480_000, 690_000, 580_000, 1_000_000]
    rows = []
    for (topic_area, base), week in itertools.product(zip(_TOPIC_AREA_NAMES, base_engagement), weeks):
        random.seed(hash((topic_area, str(week), "some")))
        rows.append(
            {
                "week_start": str(week.date()),
                "topic_area": topic_area,
                "weekly_engagement": int(base * random.uniform(0.6, 1.4)),
                "weekly_posts": random.randint(5, 80),
            }
        )
    return pd.DataFrame(rows)


def _topic_area_trad_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    topic_area_values = {
        "Prime": {
            "Positive": [(20, 230000), (14, 180000), (22, 210000), (18, 190000)],
            "Neutral": [(11, 95000), (14, 125000), (9, 90000), (8, 80000)],
            "Negative": [(4, 38000), (5, 50000), (2, 19000), (3, 27000)],
        },
        "Marketplace": {
            "Positive": [(9, 75000), (10, 81000), (12, 88000), (8, 70000)],
            "Neutral": [(15, 120000), (13, 104000), (11, 92000), (14, 112000)],
            "Negative": [(8, 78000), (10, 91000), (6, 58000), (7, 67000)],
        },
        "Logistics": {
            "Positive": [(12, 110000), (10, 95000), (14, 125000), (11, 102000)],
            "Neutral": [(9, 70000), (8, 62000), (10, 76000), (9, 71000)],
            "Negative": [(2, 18000), (3, 24000), (1, 12000), (2, 17000)],
        },
        "Advertising": {
            "Positive": [(6, 60000), (7, 68000), (8, 74000), (6, 62000)],
            "Neutral": [(10, 88000), (9, 80000), (11, 96000), (10, 89000)],
            "Negative": [(5, 47000), (6, 53000), (4, 41000), (5, 46000)],
        },
        "Technology": {
            "Positive": [(13, 120000), (11, 104000), (15, 132000), (12, 110000)],
            "Neutral": [(7, 58000), (6, 50000), (8, 64000), (7, 59000)],
            "Negative": [(1, 10000), (2, 16000), (1, 9000), (1, 11000)],
        },
        "Deals": {
            "Positive": [(19, 200000), (15, 170000), (21, 215000), (17, 185000)],
            "Neutral": [(12, 105000), (14, 118000), (10, 92000), (11, 99000)],
            "Negative": [(5, 45000), (6, 55000), (3, 28000), (4, 36000)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for topic_area, sentiment_values in topic_area_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (publications, reach) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "topic_area": topic_area,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "publications",
                        "metric_value": publications,
                    }
                )
                rows.append(
                    {
                        "topic_area": topic_area,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "reach",
                        "metric_value": reach,
                    }
                )
    return pd.DataFrame(rows)


def _topic_area_some_sentiment_timeline_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    topic_area_values = {
        "Prime": {
            "Positive": [(24, 48000), (20, 43000), (26, 56000), (22, 51000)],
            "Neutral": [(17, 26000), (18, 28000), (14, 22000), (16, 24000)],
            "Negative": [(6, 9500), (8, 13500), (5, 7500), (7, 10500)],
        },
        "Marketplace": {
            "Positive": [(10, 17000), (13, 22000), (11, 19000), (9, 15000)],
            "Neutral": [(13, 20000), (12, 18000), (15, 23000), (14, 21500)],
            "Negative": [(11, 16500), (10, 15300), (9, 13900), (12, 18100)],
        },
        "Logistics": {
            "Positive": [(14, 24000), (12, 20000), (16, 28000), (13, 22500)],
            "Neutral": [(8, 12000), (7, 10500), (9, 13500), (8, 12500)],
            "Negative": [(2, 3000), (3, 4500), (1, 1800), (2, 3200)],
        },
        "Advertising": {
            "Positive": [(7, 11000), (8, 12500), (9, 14000), (7, 11500)],
            "Neutral": [(11, 17000), (10, 15500), (12, 18500), (11, 17200)],
            "Negative": [(6, 9000), (7, 10500), (5, 7800), (6, 9200)],
        },
        "Technology": {
            "Positive": [(15, 26000), (13, 22500), (17, 30000), (14, 24500)],
            "Neutral": [(9, 14000), (8, 12500), (10, 15500), (9, 14200)],
            "Negative": [(1, 1500), (2, 2800), (1, 1400), (1, 1700)],
        },
        "Deals": {
            "Positive": [(21, 44000), (17, 37000), (23, 49000), (19, 41000)],
            "Neutral": [(14, 22000), (16, 25500), (12, 19000), (13, 20800)],
            "Negative": [(7, 11000), (8, 13000), (5, 8200), (6, 9800)],
        },
    }
    week_starts = pd.date_range("2026-01-05", periods=4, freq="W-MON")
    for topic_area, sentiment_values in topic_area_values.items():
        for sentiment, weekly_values in sentiment_values.items():
            for week_start, (posts, engagement) in zip(week_starts, weekly_values):
                rows.append(
                    {
                        "topic_area": topic_area,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "posts",
                        "metric_value": posts,
                    }
                )
                rows.append(
                    {
                        "topic_area": topic_area,
                        "week_start": week_start.date().isoformat(),
                        "sentiment": sentiment,
                        "base_metric": "engagement",
                        "metric_value": engagement,
                    }
                )
    return pd.DataFrame(rows)


def _topic_area_top_publishers_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"source": "Trad", "topic_area": "Prime", "publisher": "Reuters", "media_type_platform": "Online", "reach": 2_600_000, "publications": 6},
            {"source": "Trad", "topic_area": "Prime", "publisher": "The Verge", "media_type_platform": "Online", "reach": 1_750_000, "publications": 3},
            {"source": "Trad", "topic_area": "Prime", "publisher": "CNBC", "media_type_platform": "TV", "reach": 1_050_000, "publications": 2},
            {"source": "SoMe", "topic_area": "Prime", "publisher": "Krzysztof Stanowski", "media_type_platform": "twitter", "reach": 580_000, "publications": 4},
            {"source": "SoMe", "topic_area": "Prime", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 330_000, "publications": 2},
            {"source": "Trad", "topic_area": "Marketplace", "publisher": "Bloomberg", "media_type_platform": "Online", "reach": 2_000_000, "publications": 4},
            {"source": "Trad", "topic_area": "Marketplace", "publisher": "Forbes", "media_type_platform": "Online", "reach": 920_000, "publications": 2},
            {"source": "SoMe", "topic_area": "Marketplace", "publisher": "Weronika", "media_type_platform": "twitter", "reach": 450_000, "publications": 3},
            {"source": "Trad", "topic_area": "Logistics", "publisher": "The Guardian", "media_type_platform": "Online", "reach": 1_600_000, "publications": 4},
            {"source": "Trad", "topic_area": "Logistics", "publisher": "BBC", "media_type_platform": "TV", "reach": 1_100_000, "publications": 2},
            {"source": "SoMe", "topic_area": "Logistics", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 520_000, "publications": 3},
            {"source": "Trad", "topic_area": "Advertising", "publisher": "Adweek", "media_type_platform": "Online", "reach": 980_000, "publications": 3},
            {"source": "SoMe", "topic_area": "Advertising", "publisher": "Weronika", "media_type_platform": "twitter", "reach": 410_000, "publications": 2},
            {"source": "Trad", "topic_area": "Technology", "publisher": "The Verge", "media_type_platform": "Online", "reach": 1_300_000, "publications": 3},
            {"source": "SoMe", "topic_area": "Technology", "publisher": "Krzysztof Stanowski", "media_type_platform": "twitter", "reach": 470_000, "publications": 2},
            {"source": "Trad", "topic_area": "Deals", "publisher": "Reuters", "media_type_platform": "Online", "reach": 2_100_000, "publications": 5},
            {"source": "SoMe", "topic_area": "Deals", "publisher": "Bezprawnik", "media_type_platform": "facebook", "reach": 690_000, "publications": 4},
        ]
    )


def _topic_area_top_journalists_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"topic_area": "Prime", "journalist": "Anna Kowalska", "publications": 15, "reach": 3_400_000},
            {"topic_area": "Prime", "journalist": "James Patterson", "publications": 10, "reach": 1_850_000},
            {"topic_area": "Marketplace", "journalist": "Sarah Connolly", "publications": 12, "reach": 2_500_000},
            {"topic_area": "Marketplace", "journalist": "Tomasz Wisniewski", "publications": 8, "reach": 1_200_000},
            {"topic_area": "Logistics", "journalist": "Marek Nowak", "publications": 7, "reach": 1_050_000},
            {"topic_area": "Advertising", "journalist": "Emily Carter", "publications": 9, "reach": 1_650_000},
            {"topic_area": "Technology", "journalist": "Piotr Zalewski", "publications": 11, "reach": 2_050_000},
            {"topic_area": "Deals", "journalist": "Anna Kowalska", "publications": 13, "reach": 2_900_000},
        ]
    )


def _topic_area_top_publications_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "topic_area": "Prime",
                "Date": "2026-01-15",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Reuters",
                "Author": None,
                "Title": "Amazon Expands Prime Benefits",
                "Summary": "Amazon expands Prime membership perks for 2026.",
                "URL": "https://example.com/topic-area-pub-1",
                "Sentiment": "Positive",
                "Reach": 2_600_000,
                "Engagement": 0,
                "Angle": "Membership value perception",
            },
            {
                "topic_area": "Prime",
                "Date": "2026-02-20",
                "Source": "SoMe",
                "Type": "Twitter",
                "Publication": None,
                "Author": "Krzysztof Stanowski",
                "Title": "",
                "Summary": "Big updates coming to Prime - stay tuned!",
                "URL": "https://example.com/topic-area-pub-2",
                "Sentiment": "Positive",
                "Reach": 580_000,
                "Engagement": 16_200,
                "Angle": "Membership value perception",
            },
            {
                "topic_area": "Marketplace",
                "Date": "2026-03-10",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "Bloomberg",
                "Author": None,
                "Title": "Sellers Push Back on Marketplace Policies",
                "Summary": "Sellers raise concerns over marketplace fee changes.",
                "URL": "https://example.com/topic-area-pub-3",
                "Sentiment": "Negative",
                "Reach": 2_000_000,
                "Engagement": 0,
                "Angle": "Seller policies",
            },
            {
                "topic_area": "Logistics",
                "Date": "2026-04-05",
                "Source": "Trad",
                "Type": "Online",
                "Publication": "The Guardian",
                "Author": None,
                "Title": "Delivery Speed Improvements Drive Engagement",
                "Summary": "Faster delivery times drive strong engagement across channels.",
                "URL": "https://example.com/topic-area-pub-4",
                "Sentiment": "Neutral",
                "Reach": 1_600_000,
                "Engagement": 0,
                "Angle": "Delivery speed",
            },
            {
                "topic_area": "Deals",
                "Date": "2026-04-08",
                "Source": "SoMe",
                "Type": "Facebook",
                "Publication": None,
                "Author": "Bezprawnik",
                "Title": "",
                "Summary": "Reaction to the latest flash sale event.",
                "URL": "https://example.com/topic-area-pub-5",
                "Sentiment": "Positive",
                "Reach": 690_000,
                "Engagement": 21_400,
                "Angle": "Flash sales",
            },
        ]
    )


def _campaign_profile_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign": "Prime Day 2025",
                "profile": "Prime Day 2025 is Amazon's flagship shopping event, driving large-scale traffic and media coverage across traditional and social media with a focus on deals and membership value.",
                "takeaway_1": "Strong positive sentiment around Prime membership perks reinforced loyalty messaging.",
                "takeaway_2": "Peak coverage coincided with the main event dates, generating high reach across publishers.",
                "takeaway_3": "Social media amplification highlighted fast delivery and exclusive deals.",
            },
            {
                "campaign": "(Un)aware Consumer",
                "profile": "(Un)aware Consumer explores online shopping behaviours among Polish consumers, positioning Amazon as attentive to price-conscious shoppers.",
                "takeaway_1": "Coverage emphasised price-consciousness and strategic purchasing habits among consumers.",
                "takeaway_2": "Positive sentiment dominated traditional media coverage of the study.",
                "takeaway_3": "Findings reinforced Amazon's positioning in the growing Polish e-commerce market.",
            },
        ]
    )


def _campaign_narratives_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "campaign": "Prime Day 2025",
                "narrative_id": "C012",
                "narrative_label": "Amazon Under Labor Scrutiny in Poland",
                "connection": "Negative",
                "rationale": "The campaign's promotional messaging contrasts with ongoing scrutiny of Amazon's labor practices, highlighting potential issues that undermine the positive narrative.",
            },
            {
                "campaign": "(Un)aware Consumer",
                "narrative_id": "C023",
                "narrative_label": "Amazon's Pricing Practices Under Scrutiny",
                "connection": "Negative",
                "rationale": "The campaign's focus on price-consciousness may draw attention to pricing practices, potentially reinforcing scrutiny if consumers feel pressured by promotional offers.",
            },
        ]
    )


