---
name: apify-google-trends
description: Query Google Trends data (interest over time, regional interest, related topics/queries) for any search term via the Apify Google Trends Scraper. Use when the user needs trend data, market research, SEO analysis, or keyword popularity over time. Requires APIFY_API_TOKEN env var.
allowed-tools: Bash(uv run *) Bash(cd *) Read
---

# Google Trends Skill

Query Google Trends data for any search term using the Apify Google Trends Scraper actor.

## Setup (first time only)

```bash
(cd ${CLAUDE_SKILL_DIR} && uv sync)
```

Requires `APIFY_API_TOKEN` environment variable set with a valid [Apify API token](https://console.apify.com/account/integrations).

## Usage

```bash
echo '{"search_terms": ["AI", "machine learning"], "time_range": "today 3-m", "geo": "US"}' | \
  (cd ${CLAUDE_SKILL_DIR} && uv run python scripts/query_trends.py)
```

### Input (JSON on stdin)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_terms` | list[str] | **required** | Search terms to query |
| `time_range` | str | `""` (past 12mo) | `now 1-H`, `now 4-H`, `now 1-d`, `now 7-d`, `today 1-m`, `today 3-m`, `today 5-y`, `all` |
| `geo` | str | `""` (worldwide) | Country code: `US`, `GB`, `DE`, etc. |
| `category` | str | `""` (all) | Category ID for filtering |
| `is_multiple` | bool | `false` | Treat commas in terms as separate queries |
| `max_items` | int | `0` (no limit) | Max results to return |
| `custom_time_range` | str | `""` | Custom range: `YYYY-MM-DD YYYY-MM-DD` |

### Output (JSON on stdout)

JSON array with one object per search term containing:
- `search_term`, `interest_over_time`, `interest_by_region`
- `related_topics_top`, `related_topics_rising`
- `related_queries_top`, `related_queries_rising`

Errors go to stderr as `{"error": "...", "message": "..."}` with exit code 1.

## Python API

```python
from apify_google_trends_skill import ApifyTrendsClient, TrendsQuery

query = TrendsQuery(search_terms=["AI"], geo="US", time_range="today 3-m")
async with ApifyTrendsClient() as client:
    results = await client.query(query)
```

## References

- For full output schema and field details, see [reference.md](reference.md)
- For the Python package source, see [src/apify_google_trends_skill/](src/apify_google_trends_skill/)
