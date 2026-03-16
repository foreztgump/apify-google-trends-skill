"""Apify Google Trends client with sync/async-fallback strategy."""

from __future__ import annotations

import os
from typing import Any, Self, cast

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

        if isinstance(body, list):
            return cast("list[dict[str, Any]]", body)

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
