---
name: apify-google-trends
description: Query Google Trends data (interest over time, regional interest, related topics/queries) via the Apify Google Trends Scraper actor. Requires APIFY_API_TOKEN env var.
allowed-tools: Bash(python:) Bash(uv:) Read
metadata:
  author: cownose
  version: 0.1.0
  tags: [google-trends, apify, market-research, seo, trend-analysis]
---

# Google Trends Skill

Query Google Trends data for any search term using the Apify Google Trends Scraper.

## Prerequisites

- `APIFY_API_TOKEN` environment variable set with a valid Apify API token
- Python 3.12+ with dependencies installed (`uv sync` in this skill's directory)

## Capabilities

- **Interest over time**: Weekly/daily trend data for search terms
- **Regional interest**: Interest by country, subregion, city, or metro area
- **Related topics**: Top and rising related topics
- **Related queries**: Top and rising related search queries
- **Multi-term comparison**: Compare multiple search terms in one query
- **Custom filters**: Time range, geo area, category, Google Trends URLs

## Usage

Run the query script with JSON input:

```bash
echo '{"search_terms": ["web scraping", "data mining"], "time_range": "today 3-m", "geo": "US"}' | \
  uv run python scripts/query_trends.py
```

### Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_terms` | list[str] | required | Search terms to query |
| `time_range` | str | `""` (past 12 months) | Time range: `now 1-H`, `now 4-H`, `now 1-d`, `now 7-d`, `today 1-m`, `today 3-m`, `today 5-y`, `all` |
| `geo` | str | `""` (worldwide) | Country code (e.g., `US`, `GB`, `DE`) |
| `category` | str | `""` (all) | Category ID for filtering |
| `is_multiple` | bool | `false` | If true, commas in terms create separate queries |
| `max_items` | int | `0` (no limit) | Maximum results to return |
| `custom_time_range` | str | `""` | Custom date range: `YYYY-MM-DD YYYY-MM-DD` |
| `viewed_from` | str | `""` | Proxy country code for residential proxies |
| `skip_debug_screen` | bool | `true` | Skip saving KV snapshots (saves credits) |

### Output

Returns JSON array of trend results, one per search term. Each result contains:

- `search_term`: The queried term
- `interest_over_time`: Array of `{time, formatted_time, value, has_data}`
- `interest_by_region`: Regional breakdown (subregion, city, or country-level depending on geo)
- `related_topics_top` / `related_topics_rising`: Related topics with title, type, value, link
- `related_queries_top` / `related_queries_rising`: Related queries with query, value, link

## References

- [scripts/query_trends.py](scripts/query_trends.py) — Main query script
- [src/apify_google_trends_skill/](src/apify_google_trends_skill/) — Python package with client and models
