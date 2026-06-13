---
name: bq-data-sources
description: BigQuery table alias mapping for the amazon_2026 dashboard — use these aliases when the user references bqtrad, bqsome, bqnarr, bqang, or bqpub
metadata:
  type: project
---

BigQuery table aliases for the amazon_2026 dashboard:

| Alias | BQ table name (within dataset amazon_2026) | Content |
|---|---|---|
| bqtrad | amazon_2026_trad | Traditional media publications |
| bqsome | amazon_2026_some | Social media posts |
| bqnarr | amazon_2026_narratives | Narratives aggregate data |
| bqang | amazon_2026_angles | Angles data |
| bqpub | amazon_2026_publishers | Publishers data |

**Why:** User uses these short aliases when specifying data sources for new charts or KPIs.
**How to apply:** When the user writes e.g. "bqtrad" in a chart/KPI spec, resolve it to `amazon_2026_trad` and use `_table('amazon_2026_trad')` in SQL.
