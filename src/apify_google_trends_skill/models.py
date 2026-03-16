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

        actor_input["isMultiple"] = self.is_multiple
        actor_input["maxItems"] = self.max_items
        actor_input["skipDebugScreen"] = self.skip_debug_screen

        return actor_input
