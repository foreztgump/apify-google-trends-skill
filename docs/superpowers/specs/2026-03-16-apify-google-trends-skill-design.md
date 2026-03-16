# Apify Google Trends Skill — Design Spec

**Date**: 2026-03-16
**Status**: Approved
**Actor**: `apify/google-trends-scraper` (URL path form: `apify~google-trends-scraper`)

## Overview

Agent Skill (agentskills.io standard) that wraps the Apify Google Trends Scraper actor, providing AI agents a typed Python interface to query Google Trends data. Uses direct Apify REST API calls via httpx (no SDK).

## Architecture: Layered Modules

```
src/apify_google_trends_skill/
├── __init__.py          # Re-exports: ApifyTrendsClient, TrendsQuery, TrendResult
├── client.py            # ApifyTrendsClient — single public entry point
├── models.py            # Pydantic input/output models
├── constants.py         # API URLs, timeouts, actor ID, defaults
├── exceptions.py        # Custom exception hierarchy

scripts/
├── query_trends.py      # Agent-executable: JSON stdin → client → JSON stdout

tests/
├── conftest.py          # Shared fixtures: mock responses, sample queries
├── test_client.py       # Client tests with respx mocking
├── test_models.py       # Model validation tests
```

### Design Rationale

- **Why layered over flat**: SRP — each module stays under 100 lines with one clear job. client.py orchestrates, models.py validates, constants.py configures, exceptions.py categorizes errors.
- **Why layered over protocol abstraction**: YAGNI — we have one transport (httpx), no plan to swap. Adding a protocol interface would be premature abstraction.
- **Deep module principle**: `ApifyTrendsClient` exposes one method (`query()`) hiding sync/async-fallback, retry, parsing, and validation complexity.

## Data Flow

```
Agent JSON input → scripts/query_trends.py (stdin)
  → TrendsQuery validation (pydantic)
  → ApifyTrendsClient.query()
    → POST /v2/acts/apify~google-trends-scraper/run-sync-get-dataset-items
      ├─ 200/201 with dataset items → parse JSON → list[TrendResult]
      ├─ 200/201 with run object (status RUNNING) → extract runId → async fallback
      ├─ 408 Timeout → async fallback (start new run)
      └─ httpx.TimeoutException → async fallback (start new run)
           ↓
       Async fallback:
           POST /v2/acts/apify~google-trends-scraper/runs (skip if runId from sync)
           → Poll GET /v2/actor-runs/{runId}?waitForFinish=60
             ├─ SUCCEEDED → GET /v2/actor-runs/{runId}/dataset/items → list[TrendResult]
             ├─ RUNNING / TIMING-OUT / ABORTING → continue polling
             └─ FAILED / TIMED-OUT / ABORTED → raise ApifyActorError
  → JSON stdout (results) or JSON stderr (error) + exit code
```

**Note on sync response**: The sync endpoint may return *either* a 408 status *or* a 200/201
with a run object (status `RUNNING`) if the actor exceeds the timeout. The client detects
this by checking whether the response body is a JSON array (dataset items) or a JSON object
with a `status` field (run object). When a run object is returned, its `id` is reused for
async polling without starting a new run.

## Models

### Input: TrendsQuery

```python
class TrendsQuery(BaseModel, frozen=True):
    search_terms: list[str]              # required, min 1 item
    time_range: str = ""                 # "", "now 1-H", "now 4-H", "now 1-d",
                                         # "now 7-d", "today 1-m", "today 3-m",
                                         # "today 5-y", "all"
    geo: str = ""                        # ISO country code or ""
    category: str = ""                   # category ID string
    is_multiple: bool = False            # comma = separate queries
    max_items: int = 0                   # 0 = no limit
    custom_time_range: str = ""          # "YYYY-MM-DD YYYY-MM-DD"
    viewed_from: str = ""                # proxy country code
    skip_debug_screen: bool = True       # don't save KV snapshots

    # Deliberately omitted: startUrls, spreadsheetId. These are advanced actor inputs
    # not needed for the primary use case (query by search terms). Can be added later
    # if agents need URL-based queries. See YAGNI principle.
```

Provides `to_actor_input() -> dict` that maps snake_case to camelCase for the Apify actor.

### Output: TrendResult

```python
class TimelinePoint(BaseModel, frozen=True):
    time: str                            # unix timestamp string
    formatted_time: str
    value: list[int]
    has_data: list[bool]

class RegionInterest(BaseModel, frozen=True):
    geo_code: str
    geo_name: str
    value: list[int]
    has_data: list[bool]

class RelatedTopic(BaseModel, frozen=True):
    title: str
    topic_type: str                      # e.g. "Topic", "Programming language"
    value: int
    formatted_value: str
    link: str = ""

class RelatedQuery(BaseModel, frozen=True):
    query: str
    value: int
    formatted_value: str
    link: str = ""

class TrendResult(BaseModel, frozen=True):
    search_term: str
    interest_over_time: list[TimelinePoint]
    interest_by_region: list[RegionInterest]
    related_topics_top: list[RelatedTopic]
    related_topics_rising: list[RelatedTopic]
    related_queries_top: list[RelatedQuery]
    related_queries_rising: list[RelatedQuery]
```

`TrendResult` provides `from_actor_output(raw: dict) -> TrendResult` classmethod that normalizes the actor's verbose field names into clean Python names. Handles all three regional variants (`interestBySubregion`, `interestByCity`, `interestBy`) into unified `interest_by_region`.

### Design Choice: Normalized Output

We parse and validate raw Apify JSON into typed models rather than passing through raw dicts. This gives agents a stable, documented interface even if the actor's output format changes.

## Client Interface

```python
class ApifyTrendsClient:
    def __init__(self, timeout: float = SYNC_TIMEOUT_SECONDS):
        """Read token from APIFY_API_TOKEN env var. Raises ApifyAuthError if missing."""

    async def query(self, trends_query: TrendsQuery) -> list[TrendResult]:
        """Run the Google Trends actor and return parsed results.

        1. Try sync endpoint (up to timeout seconds)
        2. On 408, run object with RUNNING status, or httpx timeout → async fallback
        3. Parse and validate results
        """

    async def close(self) -> None:
        """Close the underlying httpx client."""

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, *exc) -> None: ...
```

### Sync/Async Fallback Strategy

1. **Sync attempt**: POST to `/run-sync-get-dataset-items` with `timeout={timeout}` query param. httpx timeout set to `SYNC_TIMEOUT_SECONDS + 30` for this request specifically (buffer for network overhead). If the actor finishes within the timeout, the response body is the dataset items directly (a JSON array).
2. **Sync response detection**: If the response is a JSON array → dataset items (success). If the response is a JSON object with a `status` field → run object. Extract `id` for async polling without starting a new run.
3. **Async fallback triggers**: (a) HTTP 408 status, (b) response is a run object with status `RUNNING`, (c) `httpx.TimeoutException`. For (a) and (c), start a new run via POST `/runs`. For (b), reuse the run ID from the sync response.
4. **Async polling**: Poll GET `/actor-runs/{runId}?waitForFinish=60` in a loop. Max iterations: `ASYNC_MAX_POLL_ATTEMPTS`. On `SUCCEEDED`, fetch items from `/actor-runs/{runId}/dataset/items`.
5. **Status handling**: `RUNNING`, `TIMING-OUT`, `ABORTING` → continue polling (transitional). `SUCCEEDED` → fetch results. `FAILED`, `TIMED-OUT`, `ABORTED` → raise `ApifyActorError`.

## Constants

```python
APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "apify~google-trends-scraper"  # tilde-separated for URL paths
SYNC_TIMEOUT_SECONDS = 300.0              # 5 min Apify server-side timeout
SYNC_HTTP_TIMEOUT_SECONDS = 330.0         # httpx timeout for sync request (300 + 30 buffer)
ASYNC_POLL_WAIT_SECONDS = 60              # waitForFinish param per poll
ASYNC_MAX_POLL_ATTEMPTS = 10              # max polls before giving up (10 min total)
ASYNC_HTTP_TIMEOUT_SECONDS = 90.0         # httpx timeout for poll/fetch requests
```

## Error Handling

```
ApifyError (base, inherits Exception)
├── ApifyAuthError        — 401/403 (bad/missing token)
├── ApifyAPIError         — other non-2xx responses
├── ApifyTimeoutError     — sync + async polling both exhausted
└── ApifyActorError       — actor run FAILED / TIMED-OUT / ABORTED (terminal statuses)
```

All exceptions include the HTTP status code and response body where available. The script layer catches these and outputs structured error JSON to stderr with exit code 1.

## Script: query_trends.py

```python
#!/usr/bin/env python3
"""Agent-executable script: reads TrendsQuery JSON from stdin, outputs results to stdout."""

# 1. Read JSON from stdin
# 2. Validate into TrendsQuery
# 3. Create ApifyTrendsClient (token from env)
# 4. await client.query(trends_query)
# 5. Serialize list[TrendResult] to JSON stdout
# 6. On error: write {"error": "...", "message": "..."} to stderr, exit 1
```

Invocation: `echo '{"search_terms": ["AI"]}' | uv run python scripts/query_trends.py`

## Testing Strategy

### test_models.py
- Valid TrendsQuery with all defaults
- TrendsQuery with all fields populated
- TrendsQuery validation error: empty search_terms
- TrendsQuery.to_actor_input() camelCase mapping
- TrendResult.from_actor_output() with full realistic payload
- TrendResult.from_actor_output() with minimal/missing optional fields
- Regional variant handling (interestBySubregion vs interestByCity vs interestBy)

### test_client.py (respx mocking)
- **Happy path**: sync endpoint returns 200 with JSON array → parsed TrendResult list
- **Timeout fallback (408)**: sync returns 408 → new async run starts → poll succeeds → items fetched
- **Timeout fallback (run object)**: sync returns 200 with run object (status RUNNING) → reuses runId → poll succeeds
- **Timeout fallback (httpx timeout)**: sync raises httpx.TimeoutException → new async run starts → poll succeeds
- **Auth error**: sync returns 401 → ApifyAuthError raised
- **API error**: sync returns 500 → ApifyAPIError raised
- **Actor failure**: async poll returns status FAILED → ApifyActorError raised
- **Transitional statuses**: poll returns TIMING-OUT → continues polling → TIMED-OUT → ApifyActorError
- **Poll exhaustion**: all polls return RUNNING → ApifyTimeoutError raised
- **Token from env**: client reads APIFY_API_TOKEN env var
- **Missing token**: raises ApifyAuthError immediately

### conftest.py
- `sample_trends_query` fixture
- `sample_actor_output` fixture (realistic JSON based on actor docs)
- `sample_actor_run_response` fixture (run metadata with ID, status)
