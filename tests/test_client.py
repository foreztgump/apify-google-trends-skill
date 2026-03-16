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
        respx_mock.post(SYNC_URL).mock(
            return_value=httpx.Response(200, json={"data": {"id": run_id, "status": "RUNNING"}})
        )
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
        assert client._api_token == "test-token-123"
        await client.close()
