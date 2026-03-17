# Apify Google Trends Skill

An [Agent Skill](https://agentskills.io) that queries Google Trends data via the [Apify Google Trends Scraper](https://apify.com/apify/google-trends-scraper) actor.

Provides AI agents with interest over time, regional interest, related topics, and related queries for any search term.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- An [Apify API token](https://console.apify.com/account/integrations)

## Setup

```bash
git clone https://github.com/foreztgump/apify-google-trends-skill.git
cd apify-google-trends-skill
uv sync
export APIFY_API_TOKEN=your_token_here
```

## Usage

### As an Agent Skill

Install the skill folder into any compatible agent's skills directory. The agent reads `SKILL.md` for capabilities and invokes `scripts/query_trends.py`.

### From the command line

```bash
echo '{"search_terms": ["web scraping"], "time_range": "today 3-m", "geo": "US"}' | \
  uv run python scripts/query_trends.py
```

### As a Python library

```python
import asyncio
from apify_google_trends_skill import ApifyTrendsClient, TrendsQuery

async def main():
    query = TrendsQuery(search_terms=["AI", "machine learning"], geo="US")
    async with ApifyTrendsClient() as client:
        results = await client.query(query)
    for r in results:
        print(f"{r.search_term}: {len(r.interest_over_time)} data points")

asyncio.run(main())
```

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_terms` | `list[str]` | required | Search terms to query |
| `time_range` | `str` | `""` (past 12 months) | `now 1-H`, `now 4-H`, `now 1-d`, `now 7-d`, `today 1-m`, `today 3-m`, `today 5-y`, `all` |
| `geo` | `str` | `""` (worldwide) | Country code (`US`, `GB`, `DE`, etc.) |
| `category` | `str` | `""` (all) | Category ID for filtering |
| `is_multiple` | `bool` | `false` | Treat commas as separate queries |
| `max_items` | `int` | `0` (no limit) | Max results to return |
| `custom_time_range` | `str` | `""` | Custom range: `YYYY-MM-DD YYYY-MM-DD` |

## Output

JSON array with one result per search term:

- `search_term` — the queried term
- `interest_over_time` — timeline of `{time, formatted_time, value, has_data}`
- `interest_by_region` — regional breakdown by subregion, city, or country
- `related_topics_top` / `related_topics_rising` — related topics with scores
- `related_queries_top` / `related_queries_rising` — related queries with scores

## Development

```bash
uv sync                                    # install deps
APIFY_API_TOKEN=test uv run pytest -v      # run tests
uv run ruff check src/ tests/ scripts/     # lint
uv run pyright src/                        # type check
```

## License

MIT
