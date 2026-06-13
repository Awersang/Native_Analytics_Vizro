import dashboards.amazon_2026 as amz
amz._register_data_sources()
import dashboards.amazon_2026.charts_campaigns as cc
import dashboards.amazon_2026.pages.campaigns as pc
from vizro.managers import data_manager

df = data_manager["amazon_2026_campaign_timeline"].load()
campaign = df["campaign"].iloc[0] if "campaign" in df.columns else df.iloc[0, 0]
print("campaign:", campaign)

section = cc._campaign_sentiment_timeline_section(campaign, narratives_key="amazon_2026_campaign_narratives")
# find the dcc.Store data
import dash
store_data = None
def find_store(node):
    global store_data
    if isinstance(node, dash.dcc.Store):
        store_data = node.data
        return
    children = getattr(node, "children", None)
    if children is None:
        return
    if isinstance(children, list):
        for c in children:
            find_store(c)
    else:
        find_store(children)

find_store(section)
print("narrative_labels:", store_data.get("narrative_labels"))
print("has narrative_trad_timeline records:", len(store_data.get("narrative_trad_timeline", [])))
print("has narrative_some_timeline records:", len(store_data.get("narrative_some_timeline", [])))

fig, height = pc._update_campaign_sentiment_timeline(["Trad", "SoMe", "Narratives"], "publications", store_data)[:2]
print("traces:", len(fig.data))
print("height:", height)
print("num rows (yaxes):", len([k for k in fig.layout if str(k).startswith("yaxis")]))
