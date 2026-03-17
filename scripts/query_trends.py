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
