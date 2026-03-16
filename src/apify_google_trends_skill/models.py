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

        return cls(
            search_term=raw.get("searchTerm", raw.get("inputUrlOrTerm", "")),
            interest_over_time=interest_over_time,
            interest_by_region=_parse_region_interest(raw),
            related_topics_top=[_parse_related_topic(t) for t in raw.get("relatedTopics_top", [])],
            related_topics_rising=[_parse_related_topic(t) for t in raw.get("relatedTopics_rising", [])],
            related_queries_top=[_parse_related_query(q) for q in raw.get("relatedQueries_top", [])],
            related_queries_rising=[_parse_related_query(q) for q in raw.get("relatedQueries_rising", [])],
        )


def _parse_region_interest(raw: dict[str, Any]) -> list[RegionInterest]:
    """Extract regional interest from whichever field the actor populated."""
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
