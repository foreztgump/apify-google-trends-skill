# Google Trends Skill — Reference

## Output Schema

Each item in the output array has this structure:

```json
{
  "search_term": "web scraping",
  "interest_over_time": [
    {
      "time": "1673136000",
      "formatted_time": "Jan 8 - 14, 2023",
      "value": [99],
      "has_data": [true]
    }
  ],
  "interest_by_region": [
    {
      "geo_code": "US-CA",
      "geo_name": "California",
      "value": [100],
      "has_data": [true]
    }
  ],
  "related_topics_top": [
    {
      "title": "Python",
      "topic_type": "Programming language",
      "value": 29,
      "formatted_value": "29",
      "link": "/trends/explore?q=/m/05z1_&date=today+12-m"
    }
  ],
  "related_topics_rising": [],
  "related_queries_top": [
    {
      "query": "python scraping",
      "value": 100,
      "formatted_value": "100",
      "link": "/trends/explore?q=python+scraping&date=today+12-m"
    }
  ],
  "related_queries_rising": [
    {
      "query": "chatgpt web scraping",
      "value": 4250,
      "formatted_value": "+4,250%",
      "link": "/trends/explore?q=chatgpt+web+scraping&date=today+12-m"
    }
  ]
}
```

## Regional Interest Behavior

The `interest_by_region` field unifies three different Apify actor output fields depending on the `geo` scope:

| Geo Scope | Actor Field | Example |
|-----------|-------------|---------|
| Worldwide (`""`) | `interestBy` | Countries ranked by interest |
| Country (`"US"`) | `interestBySubregion` | States/regions within the country |
| Small country (`"GR"`) | `interestByCity` | Cities within the country |

The skill normalizes all three into `interest_by_region` with `geo_code` and `geo_name` fields.

## Time Range Options

| Value | Period |
|-------|--------|
| `""` (default) | Past 12 months |
| `now 1-H` | Past hour |
| `now 4-H` | Past 4 hours |
| `now 1-d` | Past day |
| `now 7-d` | Past 7 days |
| `today 1-m` | Past month |
| `today 3-m` | Past 3 months |
| `today 5-y` | Past 5 years |
| `all` | Since 2004 |

## Custom Time Range

Format: `YYYY-MM-DD YYYY-MM-DD` (start end).

```json
{"search_terms": ["bitcoin"], "custom_time_range": "2025-01-01 2025-06-01"}
```

When `custom_time_range` is set, it takes precedence over `time_range`.

## Category IDs

Common category IDs for filtering:

| ID | Category |
|----|----------|
| `3` | Arts & Entertainment |
| `5` | Computers & Electronics |
| `7` | Finance |
| `12` | Business & Industrial |
| `44` | Internet & Telecom |
| `71` | Food & Drink |
| `174` | Sports |
| `299` | Science |

## Error Types

| Error | Cause |
|-------|-------|
| `ApifyAuthError` | Missing or invalid `APIFY_API_TOKEN` |
| `ApifyAPIError` | Non-2xx response from Apify API |
| `ApifyTimeoutError` | Actor run exceeded polling limit |
| `ApifyActorError` | Actor run failed (`FAILED`, `TIMED-OUT`, `ABORTED`) |
| `ValidationError` | Invalid input JSON or missing required fields |

## Apify Actor

- **Actor**: `apify/google-trends-scraper`
- **API**: Apify REST API v2 (`https://api.apify.com/v2`)
- **Strategy**: Sync endpoint first (`/run-sync-get-dataset-items`, 5min timeout), falls back to async polling on timeout
