# Apify Google Trends Skill

An [Agent Skill](https://agentskills.io) that queries Google Trends data via the [Apify Google Trends Scraper](https://apify.com/apify/google-trends-scraper) actor.

Provides AI agents with interest over time, regional interest, related topics, and related queries for any search term.

## Install as Agent Skill

```bash
git clone https://github.com/foreztgump/apify-google-trends-skill.git ~/.claude/skills/apify-google-trends
cd ~/.claude/skills/apify-google-trends && uv sync
```

Set the `APIFY_API_TOKEN` environment variable with your [Apify API token](https://console.apify.com/account/integrations).

Once installed, Claude Code auto-discovers the skill from `SKILL.md`. Invoke it with `/apify-google-trends` or let Claude use it when you ask about trends, keyword popularity, or market research.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- An [Apify API token](https://console.apify.com/account/integrations)

## Usage

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
    query = TrendsQuery(search_terms=["AI", "machine learning"], geo="US", time_range="today 3-m")
    async with ApifyTrendsClient() as client:
        results = await client.query(query)
    for r in results:
        print(f"{r.search_term}: {len(r.interest_over_time)} data points, {len(r.interest_by_region)} regions")

asyncio.run(main())
```

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_terms` | `list[str]` | **required** | Search terms to query |
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

See [reference.md](reference.md) for the full output schema, time range options, category IDs, and error types.

## Project Structure

```
apify-google-trends-skill/
├── SKILL.md                          # Agent Skill entry point
├── reference.md                      # Detailed API reference (loaded on demand)
├── scripts/query_trends.py           # Agent-executable script (stdin/stdout)
├── src/apify_google_trends_skill/    # Python package
│   ├── client.py                     # ApifyTrendsClient (sync/async-fallback)
│   ├── models.py                     # Pydantic input/output models
│   ├── constants.py                  # API configuration
│   └── exceptions.py                 # Error hierarchy
├── tests/                            # 24 tests (pytest + respx)
├── pyproject.toml                    # Dependencies
└── README.md
```

## Development

```bash
uv sync                                    # install deps
APIFY_API_TOKEN=test uv run pytest -v      # run 24 tests
uv run ruff check src/ tests/ scripts/     # lint
uv run pyright src/                        # type check
```

## License

MIT
