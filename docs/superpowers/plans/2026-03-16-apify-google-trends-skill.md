# Apify Google Trends Skill Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Python Agent Skill that queries Google Trends data via the Apify REST API, with typed models, sync/async-fallback client, and an agent-executable script.

**Architecture:** Layered modules — constants.py (config), exceptions.py (error types), models.py (Pydantic input/output), client.py (orchestrator with sync/async-fallback), query_trends.py (stdin/stdout script). TDD throughout.

**Tech Stack:** Python 3.12, httpx 0.28.1, pydantic 2.12.5, pytest 9.0.2, respx 0.22.0, ruff, pyright

**Spec:** `docs/superpowers/specs/2026-03-16-apify-google-trends-skill-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/apify_google_trends_skill/constants.py` | Create | API URLs, actor ID, timeouts, run statuses |
| `src/apify_google_trends_skill/exceptions.py` | Create | ApifyError hierarchy (4 exception classes) |
| `src/apify_google_trends_skill/models.py` | Create | TrendsQuery, TrendResult, nested models, conversion methods |
| `src/apify_google_trends_skill/client.py` | Create | ApifyTrendsClient with sync/async-fallback query() |
| `src/apify_google_trends_skill/__init__.py` | Modify | Re-export public API |
| `scripts/query_trends.py` | Create | Agent-executable: stdin JSON → client → stdout JSON |
| `tests/conftest.py` | Create | Shared fixtures for all tests |
| `tests/test_models.py` | Create | Model validation and conversion tests |
| `tests/test_client.py` | Create | Client tests with respx mocking |

---

## Chunk 1: Foundation (constants, exceptions, input model)

### Task 1: Constants

**Files:**
- Create: `src/apify_google_trends_skill/constants.py`

- [ ] **Step 1: Create constants module**

```python
# src/apify_google_trends_skill/constants.py
"""Apify API configuration constants."""

APIFY_BASE_URL = "https://api.apify.com/v2"
ACTOR_ID = "apify~google-trends-scraper"

SYNC_TIMEOUT_SECONDS = 300.0
SYNC_HTTP_TIMEOUT_SECONDS = 330.0
ASYNC_POLL_WAIT_SECONDS = 60
ASYNC_MAX_POLL_ATTEMPTS = 10
ASYNC_HTTP_TIMEOUT_SECONDS = 90.0

APIFY_TOKEN_ENV_VAR = "APIFY_API_TOKEN"

TERMINAL_STATUSES = frozenset({"FAILED", "TIMED-OUT", "ABORTED"})
TRANSITIONAL_STATUSES = frozenset({"RUNNING", "TIMING-OUT", "ABORTING"})
SUCCESS_STATUS = "SUCCEEDED"
```

- [ ] **Step 2: Verify with ruff and pyright**

Run: `uv run ruff check src/apify_google_trends_skill/constants.py && uv run pyright src/apify_google_trends_skill/constants.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/apify_google_trends_skill/constants.py
git commit -m "feat(constants): add Apify API configuration constants"
```

---

### Task 2: Exceptions

**Files:**
- Create: `src/apify_google_trends_skill/exceptions.py`

- [ ] **Step 1: Create exceptions module**

```python
# src/apify_google_trends_skill/exceptions.py
"""Custom exception hierarchy for Apify API errors."""


class ApifyError(Exception):
    """Base exception for all Apify-related errors."""


class ApifyAuthError(ApifyError):
    """Raised when the API token is missing or invalid (401/403)."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApifyAPIError(ApifyError):
    """Raised for non-2xx API responses not covered by other exceptions."""

    def __init__(self, message: str, status_code: int, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ApifyTimeoutError(ApifyError):
    """Raised when both sync and async polling are exhausted."""


class ApifyActorError(ApifyError):
    """Raised when the actor run reaches a terminal failure status."""

    def __init__(self, message: str, run_status: str, run_id: str = "") -> None:
        super().__init__(message)
        self.run_status = run_status
        self.run_id = run_id
```

- [ ] **Step 2: Verify with ruff and pyright**

Run: `uv run ruff check src/apify_google_trends_skill/exceptions.py && uv run pyright src/apify_google_trends_skill/exceptions.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add src/apify_google_trends_skill/exceptions.py
git commit -m "feat(exceptions): add Apify error hierarchy"
```

---

### Task 3: Input model (TrendsQuery) with tests

**Files:**
- Create: `src/apify_google_trends_skill/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for TrendsQuery**

```python
# tests/test_models.py
"""Tests for Pydantic input/output models."""

import pytest
from pydantic import ValidationError

from apify_google_trends_skill.models import TrendsQuery


class TestTrendsQuery:
    def test_minimal_query_uses_defaults(self) -> None:
        query = TrendsQuery(search_terms=["web scraping"])
        assert query.search_terms == ["web scraping"]
        assert query.time_range == ""
        assert query.geo == ""
        assert query.category == ""
        assert query.is_multiple is False
        assert query.max_items == 0
        assert query.custom_time_range == ""
        assert query.viewed_from == ""
        assert query.skip_debug_screen is True

    def test_all_fields_populated(self) -> None:
        query = TrendsQuery(
            search_terms=["AI", "ML"],
            time_range="today 3-m",
            geo="US",
            category="5",
            is_multiple=True,
            max_items=10,
            custom_time_range="2025-01-01 2025-06-01",
            viewed_from="us",
            skip_debug_screen=False,
        )
        assert query.search_terms == ["AI", "ML"]
        assert query.time_range == "today 3-m"
        assert query.geo == "US"

    def test_empty_search_terms_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            TrendsQuery(search_terms=[])

    def test_to_actor_input_maps_to_camel_case(self) -> None:
        query = TrendsQuery(
            search_terms=["web scraping"],
            time_range="today 3-m",
            geo="US",
            is_multiple=True,
            max_items=5,
            viewed_from="us",
            skip_debug_screen=False,
        )
        actor_input = query.to_actor_input()
        assert actor_input["searchTerms"] == ["web scraping"]
        assert actor_input["timeRange"] == "today 3-m"
        assert actor_input["geo"] == "US"
        assert actor_input["isMultiple"] is True
        assert actor_input["maxItems"] == 5
        assert actor_input["viewedFrom"] == "us"
        assert actor_input["skipDebugScreen"] is False

    def test_to_actor_input_omits_empty_defaults(self) -> None:
        query = TrendsQuery(search_terms=["test"])
        actor_input = query.to_actor_input()
        assert actor_input["searchTerms"] == ["test"]
        assert "timeRange" not in actor_input
        assert "geo" not in actor_input
        assert "category" not in actor_input
        assert "customTimeRange" not in actor_input
        assert "viewedFrom" not in actor_input
        # These have non-empty defaults so they're always included
        assert actor_input["isMultiple"] is False
        assert actor_input["maxItems"] == 0
        assert actor_input["skipDebugScreen"] is True

    def test_frozen_model_is_immutable(self) -> None:
        query = TrendsQuery(search_terms=["test"])
        with pytest.raises(ValidationError):
            query.search_terms = ["changed"]  # type: ignore[misc]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL (import error — models.py doesn't exist yet)

- [ ] **Step 3: Write TrendsQuery model**

```python
# src/apify_google_trends_skill/models.py
"""Pydantic models for Google Trends query input and result output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class TrendsQuery(BaseModel, frozen=True):
    """Input parameters for a Google Trends query."""

    search_terms: list[str]
    time_range: str = ""
    geo: str = ""
    category: str = ""
    is_multiple: bool = False
    max_items: int = 0
    custom_time_range: str = ""
    viewed_from: str = ""
    skip_debug_screen: bool = True

    @field_validator("search_terms")
    @classmethod
    def search_terms_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            msg = "search_terms must contain at least one term"
            raise ValueError(msg)
        return v

    def to_actor_input(self) -> dict[str, Any]:
        """Convert to Apify actor input format (camelCase keys, omit empty defaults)."""
        actor_input: dict[str, Any] = {"searchTerms": self.search_terms}

        # Only include optional string fields when non-empty
        _optional_strings = {
            "timeRange": self.time_range,
            "geo": self.geo,
            "category": self.category,
            "customTimeRange": self.custom_time_range,
            "viewedFrom": self.viewed_from,
        }
        for key, value in _optional_strings.items():
            if value:
                actor_input[key] = value

        # Always include non-string fields (they have meaningful defaults)
        actor_input["isMultiple"] = self.is_multiple
        actor_input["maxItems"] = self.max_items
        actor_input["skipDebugScreen"] = self.skip_debug_screen

        return actor_input
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Run ruff and pyright**

Run: `uv run ruff check src/apify_google_trends_skill/models.py && uv run pyright src/apify_google_trends_skill/models.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add src/apify_google_trends_skill/models.py tests/test_models.py
git commit -m "feat(models): add TrendsQuery input model with validation and camelCase conversion"
```

---

## Chunk 2: Output models and fixtures

### Task 4: Output models (TrendResult and nested types) with tests

**Files:**
- Modify: `src/apify_google_trends_skill/models.py`
- Modify: `tests/test_models.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest.py with realistic Apify response fixture**

```python
# tests/conftest.py
"""Shared test fixtures."""

from typing import Any

import pytest


@pytest.fixture()
def sample_actor_output() -> list[dict[str, Any]]:
    """Realistic Apify Google Trends Scraper output for 'web scraping'."""
    return [
        {
            "inputUrlOrTerm": "web scraping",
            "searchTerm": "web scraping",
            "interestOverTime_timelineData": [
                {
                    "time": "1673136000",
                    "formattedTime": "Jan 8 – 14, 2023",
                    "formattedAxisTime": "Jan 8, 2023",
                    "value": [99],
                    "hasData": [True],
                    "formattedValue": ["99"],
                },
                {
                    "time": "1673740800",
                    "formattedTime": "Jan 15 – 21, 2023",
                    "formattedAxisTime": "Jan 15, 2023",
                    "value": [96],
                    "hasData": [True],
                    "formattedValue": ["96"],
                },
            ],
            "interestOverTime_averages": [],
            "interestBySubregion": [
                {
                    "geoCode": "US-CA",
                    "geoName": "California",
                    "value": [100],
                    "formattedValue": ["100"],
                    "maxValueIndex": 0,
                    "hasData": [True],
                },
            ],
            "interestByCity": [],
            "relatedTopics_top": [
                {
                    "topic": {"mid": "/m/07ykbs", "title": "Web scraping", "type": "Topic"},
                    "value": 100,
                    "formattedValue": "100",
                    "hasData": True,
                    "link": "/trends/explore?q=/m/07ykbs&date=today+12-m",
                },
                {
                    "topic": {"mid": "/m/05z1_", "title": "Python", "type": "Programming language"},
                    "value": 29,
                    "formattedValue": "29",
                    "hasData": True,
                    "link": "/trends/explore?q=/m/05z1_&date=today+12-m",
                },
            ],
            "relatedTopics_rising": [
                {
                    "topic": {"mid": "/m/0g57xn", "title": "Sentiment analysis", "type": "Field of study"},
                    "value": 50,
                    "formattedValue": "+50%",
                    "link": "/trends/explore?q=/m/0g57xn&date=today+12-m",
                },
            ],
            "relatedQueries_top": [
                {
                    "query": "python scraping",
                    "value": 100,
                    "formattedValue": "100",
                    "hasData": True,
                    "link": "/trends/explore?q=python+scraping&date=today+12-m",
                },
            ],
            "relatedQueries_rising": [
                {
                    "query": "chatgpt web scraping",
                    "value": 4250,
                    "formattedValue": "+4,250%",
                    "link": "/trends/explore?q=chatgpt+web+scraping&date=today+12-m",
                },
            ],
            "interestBy": [],
        }
    ]


@pytest.fixture()
def sample_actor_output_worldwide() -> list[dict[str, Any]]:
    """Apify output with interestBy (worldwide, no subregion/city)."""
    return [
        {
            "searchTerm": "web scraping",
            "interestOverTime_timelineData": [],
            "interestOverTime_averages": [],
            "interestBySubregion": [],
            "interestByCity": [],
            "relatedTopics_top": [],
            "relatedTopics_rising": [],
            "relatedQueries_top": [],
            "relatedQueries_rising": [],
            "interestBy": [
                {
                    "geoCode": "TN",
                    "geoName": "Tunisia",
                    "value": [60],
                    "formattedValue": ["60"],
                    "maxValueIndex": 0,
                    "hasData": [True],
                },
            ],
        }
    ]


@pytest.fixture()
def sample_actor_run_response() -> dict[str, Any]:
    """Apify actor run metadata response."""
    return {
        "data": {
            "id": "run123abc",
            "actId": "apify~google-trends-scraper",
            "status": "SUCCEEDED",
            "defaultDatasetId": "dataset456def",
        }
    }


@pytest.fixture()
def sample_trends_query_dict() -> dict[str, Any]:
    """Sample input JSON as an agent would send it."""
    return {
        "search_terms": ["web scraping", "data mining"],
        "time_range": "today 3-m",
        "geo": "US",
    }
```

- [ ] **Step 2: Write failing tests for output models**

Add to `tests/test_models.py`:

```python
from apify_google_trends_skill.models import (
    RegionInterest,
    RelatedQuery,
    RelatedTopic,
    TimelinePoint,
    TrendResult,
)


class TestTrendResult:
    def test_from_actor_output_parses_full_payload(self, sample_actor_output: list[dict]) -> None:
        raw = sample_actor_output[0]
        result = TrendResult.from_actor_output(raw)

        assert result.search_term == "web scraping"
        assert len(result.interest_over_time) == 2
        assert result.interest_over_time[0].time == "1673136000"
        assert result.interest_over_time[0].value == [99]
        assert result.interest_over_time[0].has_data == [True]

    def test_from_actor_output_parses_related_topics(self, sample_actor_output: list[dict]) -> None:
        raw = sample_actor_output[0]
        result = TrendResult.from_actor_output(raw)

        assert len(result.related_topics_top) == 2
        assert result.related_topics_top[0].title == "Web scraping"
        assert result.related_topics_top[0].topic_type == "Topic"
        assert result.related_topics_top[1].title == "Python"
        assert result.related_topics_top[1].topic_type == "Programming language"

        assert len(result.related_topics_rising) == 1
        assert result.related_topics_rising[0].formatted_value == "+50%"

    def test_from_actor_output_parses_related_queries(self, sample_actor_output: list[dict]) -> None:
        raw = sample_actor_output[0]
        result = TrendResult.from_actor_output(raw)

        assert len(result.related_queries_top) == 1
        assert result.related_queries_top[0].query == "python scraping"

        assert len(result.related_queries_rising) == 1
        assert result.related_queries_rising[0].query == "chatgpt web scraping"
        assert result.related_queries_rising[0].value == 4250

    def test_from_actor_output_uses_subregion_for_region(self, sample_actor_output: list[dict]) -> None:
        raw = sample_actor_output[0]
        result = TrendResult.from_actor_output(raw)

        assert len(result.interest_by_region) == 1
        assert result.interest_by_region[0].geo_code == "US-CA"
        assert result.interest_by_region[0].geo_name == "California"

    def test_from_actor_output_uses_interest_by_for_worldwide(
        self, sample_actor_output_worldwide: list[dict]
    ) -> None:
        raw = sample_actor_output_worldwide[0]
        result = TrendResult.from_actor_output(raw)

        assert len(result.interest_by_region) == 1
        assert result.interest_by_region[0].geo_code == "TN"
        assert result.interest_by_region[0].geo_name == "Tunisia"

    def test_from_actor_output_handles_empty_fields(self) -> None:
        raw = {
            "searchTerm": "niche topic",
            "interestOverTime_timelineData": [],
            "interestBySubregion": [],
            "interestByCity": [],
            "interestBy": [],
            "relatedTopics_top": [],
            "relatedTopics_rising": [],
            "relatedQueries_top": [],
            "relatedQueries_rising": [],
        }
        result = TrendResult.from_actor_output(raw)
        assert result.search_term == "niche topic"
        assert result.interest_over_time == []
        assert result.interest_by_region == []
        assert result.related_topics_top == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_models.py::TestTrendResult -v`
Expected: FAIL (TrendResult not defined yet)

- [ ] **Step 4: Implement output models in models.py**

Append to `src/apify_google_trends_skill/models.py`:

```python
class TimelinePoint(BaseModel, frozen=True):
    """A single data point in the interest-over-time timeline."""

    time: str
    formatted_time: str
    value: list[int]
    has_data: list[bool]


class RegionInterest(BaseModel, frozen=True):
    """Interest score for a geographic region."""

    geo_code: str
    geo_name: str
    value: list[int]
    has_data: list[bool]


class RelatedTopic(BaseModel, frozen=True):
    """A topic related to the search term."""

    title: str
    topic_type: str
    value: int
    formatted_value: str
    link: str = ""


class RelatedQuery(BaseModel, frozen=True):
    """A query related to the search term."""

    query: str
    value: int
    formatted_value: str
    link: str = ""


class TrendResult(BaseModel, frozen=True):
    """Normalized result for a single search term from Google Trends."""

    search_term: str
    interest_over_time: list[TimelinePoint]
    interest_by_region: list[RegionInterest]
    related_topics_top: list[RelatedTopic]
    related_topics_rising: list[RelatedTopic]
    related_queries_top: list[RelatedQuery]
    related_queries_rising: list[RelatedQuery]

    @classmethod
    def from_actor_output(cls, raw: dict[str, Any]) -> TrendResult:
        """Parse raw Apify actor output into a normalized TrendResult."""
        interest_over_time = [
            TimelinePoint(
                time=point["time"],
                formatted_time=point["formattedTime"],
                value=point["value"],
                has_data=point["hasData"],
            )
            for point in raw.get("interestOverTime_timelineData", [])
        ]

        interest_by_region = _parse_region_interest(raw)

        related_topics_top = [
            _parse_related_topic(topic) for topic in raw.get("relatedTopics_top", [])
        ]
        related_topics_rising = [
            _parse_related_topic(topic) for topic in raw.get("relatedTopics_rising", [])
        ]
        related_queries_top = [
            _parse_related_query(q) for q in raw.get("relatedQueries_top", [])
        ]
        related_queries_rising = [
            _parse_related_query(q) for q in raw.get("relatedQueries_rising", [])
        ]

        return cls(
            search_term=raw.get("searchTerm", raw.get("inputUrlOrTerm", "")),
            interest_over_time=interest_over_time,
            interest_by_region=interest_by_region,
            related_topics_top=related_topics_top,
            related_topics_rising=related_topics_rising,
            related_queries_top=related_queries_top,
            related_queries_rising=related_queries_rising,
        )


def _parse_region_interest(raw: dict[str, Any]) -> list[RegionInterest]:
    """Extract regional interest from whichever field the actor populated.

    Priority: interestBySubregion > interestByCity > interestBy.
    The actor populates different fields depending on the geo scope.
    """
    for field in ("interestBySubregion", "interestByCity", "interestBy"):
        regions = raw.get(field, [])
        if regions:
            return [
                RegionInterest(
                    geo_code=r["geoCode"],
                    geo_name=r["geoName"],
                    value=r["value"],
                    has_data=r.get("hasData", [False]),
                )
                for r in regions
            ]
    return []


def _parse_related_topic(raw_topic: dict[str, Any]) -> RelatedTopic:
    """Parse a single related topic entry from actor output."""
    topic_info = raw_topic.get("topic", {})
    return RelatedTopic(
        title=topic_info.get("title", ""),
        topic_type=topic_info.get("type", ""),
        value=raw_topic["value"],
        formatted_value=raw_topic["formattedValue"],
        link=raw_topic.get("link", ""),
    )


def _parse_related_query(raw_query: dict[str, Any]) -> RelatedQuery:
    """Parse a single related query entry from actor output."""
    return RelatedQuery(
        query=raw_query["query"],
        value=raw_query["value"],
        formatted_value=raw_query["formattedValue"],
        link=raw_query.get("link", ""),
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_models.py -v`
Expected: All 12 tests PASS (6 TrendsQuery + 6 TrendResult)

- [ ] **Step 6: Run ruff and pyright**

Run: `uv run ruff check src/apify_google_trends_skill/models.py && uv run pyright src/apify_google_trends_skill/models.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add src/apify_google_trends_skill/models.py tests/conftest.py tests/test_models.py
git commit -m "feat(models): add TrendResult output models with from_actor_output parser"
```

---

## Chunk 3: Client implementation

### Task 5: ApifyTrendsClient with tests

**Files:**
- Create: `src/apify_google_trends_skill/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write failing tests for client**

```python
# tests/test_client.py
"""Tests for ApifyTrendsClient with respx mocking."""

from typing import Any

import httpx
import pytest
import respx

from apify_google_trends_skill.client import ApifyTrendsClient
from apify_google_trends_skill.constants import ACTOR_ID, APIFY_BASE_URL
from apify_google_trends_skill.exceptions import (
    ApifyActorError,
    ApifyAPIError,
    ApifyAuthError,
    ApifyTimeoutError,
)
from apify_google_trends_skill.models import TrendsQuery

SYNC_URL = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/run-sync-get-dataset-items"
RUNS_URL = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"


def _run_url(run_id: str) -> str:
    return f"{APIFY_BASE_URL}/actor-runs/{run_id}"


def _dataset_url(run_id: str) -> str:
    return f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"


@pytest.fixture()
def query() -> TrendsQuery:
    return TrendsQuery(search_terms=["web scraping"])


class TestClientHappyPath:
    async def test_sync_success_returns_parsed_results(
        self, query: TrendsQuery, sample_actor_output: list[dict[str, Any]], respx_mock: respx.MockRouter
    ) -> None:
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(200, json=sample_actor_output))

        async with ApifyTrendsClient() as client:
            results = await client.query(query)

        assert len(results) == 1
        assert results[0].search_term == "web scraping"
        assert len(results[0].interest_over_time) == 2


class TestClientTimeoutFallback:
    async def test_408_triggers_async_fallback(
        self, query: TrendsQuery, sample_actor_output: list[dict[str, Any]], respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_408_fallback"
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(408))
        respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        respx_mock.get(_run_url(run_id)).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "SUCCEEDED", "defaultDatasetId": "ds1"}})
        )
        respx_mock.get(_dataset_url(run_id)).mock(
            return_value=httpx.Response(200, json=sample_actor_output)
        )

        async with ApifyTrendsClient() as client:
            results = await client.query(query)

        assert len(results) == 1
        assert results[0].search_term == "web scraping"

    async def test_run_object_response_reuses_run_id(
        self, query: TrendsQuery, sample_actor_output: list[dict[str, Any]], respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_reuse_id"
        # Sync returns a run object instead of dataset items
        respx_mock.post(SYNC_URL).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        # Register RUNS_URL but it should NOT be called
        new_run_route = respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": "should_not_call", "status": "RUNNING"}})
        )
        respx_mock.get(_run_url(run_id)).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "SUCCEEDED", "defaultDatasetId": "ds1"}})
        )
        respx_mock.get(_dataset_url(run_id)).mock(
            return_value=httpx.Response(200, json=sample_actor_output)
        )

        async with ApifyTrendsClient() as client:
            results = await client.query(query)

        assert len(results) == 1
        assert new_run_route.call_count == 0

    async def test_httpx_timeout_triggers_async_fallback(
        self, query: TrendsQuery, sample_actor_output: list[dict[str, Any]], respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_httpx_timeout"
        respx_mock.post(SYNC_URL).mock(side_effect=httpx.ReadTimeout("Connection timed out"))
        respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        respx_mock.get(_run_url(run_id)).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "SUCCEEDED", "defaultDatasetId": "ds1"}})
        )
        respx_mock.get(_dataset_url(run_id)).mock(
            return_value=httpx.Response(200, json=sample_actor_output)
        )

        async with ApifyTrendsClient() as client:
            results = await client.query(query)

        assert len(results) == 1


class TestClientErrors:
    async def test_401_raises_auth_error(self, query: TrendsQuery, respx_mock: respx.MockRouter) -> None:
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(401, text="Unauthorized"))

        async with ApifyTrendsClient() as client:
            with pytest.raises(ApifyAuthError):
                await client.query(query)

    async def test_500_raises_api_error(self, query: TrendsQuery, respx_mock: respx.MockRouter) -> None:
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(500, text="Internal Server Error"))

        async with ApifyTrendsClient() as client:
            with pytest.raises(ApifyAPIError) as exc_info:
                await client.query(query)
            assert exc_info.value.status_code == 500

    async def test_actor_failure_raises_actor_error(
        self, query: TrendsQuery, respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_failed"
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(408))
        respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        respx_mock.get(_run_url(run_id)).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "FAILED"}})
        )

        async with ApifyTrendsClient() as client:
            with pytest.raises(ApifyActorError) as exc_info:
                await client.query(query)
            assert exc_info.value.run_status == "FAILED"

    async def test_transitional_status_continues_polling(
        self, query: TrendsQuery, respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_timing_out"
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(408))
        respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        # First poll: TIMING-OUT, second poll: TIMED-OUT
        respx_mock.get(_run_url(run_id)).mock(
            side_effect=[
                httpx.Response(200, json={"data": {"id": run_id, "status": "TIMING-OUT"}}),
                httpx.Response(200, json={"data": {"id": run_id, "status": "TIMED-OUT"}}),
            ]
        )

        async with ApifyTrendsClient() as client:
            with pytest.raises(ApifyActorError) as exc_info:
                await client.query(query)
            assert exc_info.value.run_status == "TIMED-OUT"

    async def test_poll_exhaustion_raises_timeout_error(
        self, query: TrendsQuery, respx_mock: respx.MockRouter
    ) -> None:
        run_id = "run_exhausted"
        respx_mock.post(SYNC_URL).mock(return_value=httpx.Response(408))
        respx_mock.post(RUNS_URL).mock(
            return_value=httpx.Response(201, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
        # All polls return RUNNING
        respx_mock.get(_run_url(run_id)).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "RUNNING"}})
        )

        async with ApifyTrendsClient() as client:
            with pytest.raises(ApifyTimeoutError):
                await client.query(query)

    async def test_missing_token_raises_auth_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
        with pytest.raises(ApifyAuthError):
            ApifyTrendsClient()

    async def test_token_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APIFY_API_TOKEN", "test-token-123")
        client = ApifyTrendsClient()
        # Verify token is used in auth header (check internal state)
        assert client._api_token == "test-token-123"
        await client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_client.py -v`
Expected: FAIL (client.py doesn't exist yet)

- [ ] **Step 3: Implement the client**

```python
# src/apify_google_trends_skill/client.py
"""Apify Google Trends client with sync/async-fallback strategy."""

from __future__ import annotations

import os
from typing import Any, Self

import httpx

from apify_google_trends_skill.constants import (
    ACTOR_ID,
    APIFY_BASE_URL,
    APIFY_TOKEN_ENV_VAR,
    ASYNC_HTTP_TIMEOUT_SECONDS,
    ASYNC_MAX_POLL_ATTEMPTS,
    ASYNC_POLL_WAIT_SECONDS,
    SUCCESS_STATUS,
    SYNC_HTTP_TIMEOUT_SECONDS,
    SYNC_TIMEOUT_SECONDS,
    TERMINAL_STATUSES,
)
from apify_google_trends_skill.exceptions import (
    ApifyActorError,
    ApifyAPIError,
    ApifyAuthError,
    ApifyTimeoutError,
)
from apify_google_trends_skill.models import TrendResult, TrendsQuery

AUTH_ERROR_STATUSES = frozenset({401, 403})
REQUEST_TIMEOUT_STATUS = 408


class ApifyTrendsClient:
    """Client for querying Google Trends via the Apify REST API.

    Uses sync endpoint first, falls back to async polling on timeout.
    """

    def __init__(self, timeout: float = SYNC_TIMEOUT_SECONDS) -> None:
        self._api_token = self._read_token()
        self._timeout = timeout
        self._http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._api_token}"},
            timeout=httpx.Timeout(ASYNC_HTTP_TIMEOUT_SECONDS),
        )

    async def query(self, trends_query: TrendsQuery) -> list[TrendResult]:
        """Run the Google Trends actor and return parsed results."""
        actor_input = trends_query.to_actor_input()
        raw_items = await self._run_actor(actor_input)
        return [TrendResult.from_actor_output(item) for item in raw_items]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http_client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def _run_actor(self, actor_input: dict[str, Any]) -> list[dict[str, Any]]:
        """Try sync endpoint, fall back to async polling on timeout."""
        sync_result = await self._try_sync_run(actor_input)

        if isinstance(sync_result, list):
            return sync_result

        # sync_result is either a run_id (from run object response) or None (408/timeout)
        run_id = sync_result if isinstance(sync_result, str) else await self._start_async_run(actor_input)
        return await self._poll_and_fetch(run_id)

    async def _try_sync_run(self, actor_input: dict[str, Any]) -> list[dict[str, Any]] | str | None:
        """Attempt sync run. Returns dataset items, run_id, or None."""
        url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        try:
            response = await self._http_client.post(
                url,
                json=actor_input,
                params={"timeout": int(self._timeout)},
                timeout=httpx.Timeout(SYNC_HTTP_TIMEOUT_SECONDS),
            )
        except httpx.TimeoutException:
            return None

        if response.status_code in AUTH_ERROR_STATUSES:
            raise ApifyAuthError(
                f"Authentication failed: {response.status_code}", status_code=response.status_code
            )

        if response.status_code == REQUEST_TIMEOUT_STATUS:
            return None

        if response.status_code >= 400:
            raise ApifyAPIError(
                f"API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        body = response.json()

        # Dataset items come as a JSON array
        if isinstance(body, list):
            return body

        # Run object comes as {"data": {"id": ..., "status": ...}}
        run_data = body.get("data", body)
        run_id = run_data.get("id")
        if run_id is None:
            raise ApifyAPIError(
                "Unexpected sync response: not a dataset array and no run ID found",
                status_code=response.status_code,
                response_body=response.text,
            )
        return run_id

    async def _start_async_run(self, actor_input: dict[str, Any]) -> str:
        """Start an async actor run and return the run ID."""
        url = f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs"
        response = await self._http_client.post(url, json=actor_input)
        self._check_response_errors(response)
        run_data = response.json().get("data", {})
        return run_data["id"]

    async def _poll_and_fetch(self, run_id: str) -> list[dict[str, Any]]:
        """Poll until the run completes, then fetch dataset items."""
        for _ in range(ASYNC_MAX_POLL_ATTEMPTS):
            status = await self._poll_run_status(run_id)

            if status == SUCCESS_STATUS:
                return await self._fetch_dataset_items(run_id)

            if status in TERMINAL_STATUSES:
                raise ApifyActorError(
                    f"Actor run {run_id} ended with status: {status}",
                    run_status=status,
                    run_id=run_id,
                )

        raise ApifyTimeoutError(
            f"Actor run {run_id} did not complete after {ASYNC_MAX_POLL_ATTEMPTS} polls"
        )

    async def _poll_run_status(self, run_id: str) -> str:
        """Poll the run status once with waitForFinish."""
        url = f"{APIFY_BASE_URL}/actor-runs/{run_id}"
        response = await self._http_client.get(
            url, params={"waitForFinish": ASYNC_POLL_WAIT_SECONDS}
        )
        self._check_response_errors(response)
        run_data = response.json().get("data", {})
        return run_data.get("status", "RUNNING")

    async def _fetch_dataset_items(self, run_id: str) -> list[dict[str, Any]]:
        """Fetch dataset items from a completed run."""
        url = f"{APIFY_BASE_URL}/actor-runs/{run_id}/dataset/items"
        response = await self._http_client.get(url)
        self._check_response_errors(response)
        return response.json()

    def _check_response_errors(self, response: httpx.Response) -> None:
        """Raise appropriate exceptions for error status codes."""
        if response.status_code in AUTH_ERROR_STATUSES:
            raise ApifyAuthError(
                f"Authentication failed: {response.status_code}", status_code=response.status_code
            )
        if response.status_code >= 400:
            raise ApifyAPIError(
                f"API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

    @staticmethod
    def _read_token() -> str:
        """Read API token from environment variable."""
        token = os.environ.get(APIFY_TOKEN_ENV_VAR, "")
        if not token:
            raise ApifyAuthError(
                f"Missing {APIFY_TOKEN_ENV_VAR} environment variable. "
                "Set it to your Apify API token."
            )
        return token
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `APIFY_API_TOKEN=test-token uv run pytest tests/test_client.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Run ruff and pyright**

Run: `uv run ruff check src/apify_google_trends_skill/client.py && uv run pyright src/apify_google_trends_skill/client.py`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add src/apify_google_trends_skill/client.py tests/test_client.py
git commit -m "feat(client): add ApifyTrendsClient with sync/async-fallback"
```

---

## Chunk 4: Public API, script, and final verification

### Task 6: Update __init__.py with public API re-exports

**Files:**
- Modify: `src/apify_google_trends_skill/__init__.py`

- [ ] **Step 1: Update __init__.py**

```python
# src/apify_google_trends_skill/__init__.py
"""Apify Google Trends Skill — query Google Trends data via Apify REST API."""

from apify_google_trends_skill.client import ApifyTrendsClient
from apify_google_trends_skill.exceptions import (
    ApifyActorError,
    ApifyAPIError,
    ApifyAuthError,
    ApifyError,
    ApifyTimeoutError,
)
from apify_google_trends_skill.models import TrendResult, TrendsQuery

__all__ = [
    "ApifyActorError",
    "ApifyAPIError",
    "ApifyAuthError",
    "ApifyError",
    "ApifyTimeoutError",
    "ApifyTrendsClient",
    "TrendResult",
    "TrendsQuery",
]
```

- [ ] **Step 2: Verify imports work**

Run: `APIFY_API_TOKEN=test uv run python -c "from apify_google_trends_skill import ApifyTrendsClient, TrendsQuery, TrendResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/apify_google_trends_skill/__init__.py
git commit -m "feat: re-export public API from package __init__"
```

---

### Task 7: Agent-executable script

**Files:**
- Create: `scripts/query_trends.py`

- [ ] **Step 1: Create the script**

```python
#!/usr/bin/env python3
"""Agent-executable script: reads TrendsQuery JSON from stdin, outputs results to stdout.

Usage:
    echo '{"search_terms": ["AI"]}' | uv run python scripts/query_trends.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from apify_google_trends_skill.client import ApifyTrendsClient
from apify_google_trends_skill.exceptions import ApifyError
from apify_google_trends_skill.models import TrendsQuery


def _read_input() -> dict[str, Any]:
    """Read JSON input from stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        msg = "No input provided on stdin. Provide JSON with at least {\"search_terms\": [...]}"
        raise ValueError(msg)
    return json.loads(raw)


def _write_error(error_type: str, message: str) -> None:
    """Write structured error JSON to stderr."""
    json.dump({"error": error_type, "message": message}, sys.stderr)
    sys.stderr.write("\n")


async def _run(input_data: dict[str, Any]) -> None:
    """Validate input, query trends, and write results to stdout."""
    query = TrendsQuery.model_validate(input_data)

    async with ApifyTrendsClient() as client:
        results = await client.query(query)

    output = [result.model_dump(mode="json") for result in results]
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")


def main() -> None:
    """Entry point for the agent-executable script."""
    try:
        input_data = _read_input()
        asyncio.run(_run(input_data))
    except ApifyError as exc:
        _write_error(type(exc).__name__, str(exc))
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as exc:
        _write_error("ValidationError", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify ruff and pyright**

Run: `uv run ruff check scripts/query_trends.py && uv run pyright scripts/query_trends.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add scripts/query_trends.py
git commit -m "feat(scripts): add agent-executable query_trends.py"
```

---

### Task 8: Full test suite run and final verification

- [ ] **Step 1: Run full test suite**

Run: `APIFY_API_TOKEN=test-token uv run pytest tests/ -v --tb=short`
Expected: All tests PASS (6 TrendsQuery + 6 TrendResult + 11 client = 23 tests)

- [ ] **Step 2: Run linters on entire project**

Run: `uv run ruff check src/ tests/ scripts/ && uv run pyright src/`
Expected: No errors

- [ ] **Step 3: Run ruff format check**

Run: `uv run ruff format --check src/ tests/ scripts/`
Expected: All files formatted correctly (or run `uv run ruff format src/ tests/ scripts/` to fix)

- [ ] **Step 4: Commit any formatting fixes**

```bash
git add -A
git commit -m "style: apply ruff formatting"
```

(Skip if no changes.)

- [ ] **Step 5: Final commit — update __init__.py docstring version**

Verify the final project structure matches the spec:
```bash
find src/ tests/ scripts/ -name '*.py' | sort
```

Expected:
```
scripts/query_trends.py
src/apify_google_trends_skill/__init__.py
src/apify_google_trends_skill/client.py
src/apify_google_trends_skill/constants.py
src/apify_google_trends_skill/exceptions.py
src/apify_google_trends_skill/models.py
tests/__init__.py
tests/conftest.py
tests/test_client.py
tests/test_models.py
```
