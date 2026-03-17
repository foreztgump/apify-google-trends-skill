"""Tests for Pydantic input/output models."""

import pytest
from pydantic import ValidationError

from apify_google_trends_skill.models import (
    TrendResult,
    TrendsQuery,
)


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
        assert actor_input["isMultiple"] is False
        assert actor_input["maxItems"] == 0
        assert actor_input["skipDebugScreen"] is True

    def test_frozen_model_is_immutable(self) -> None:
        query = TrendsQuery(search_terms=["test"])
        with pytest.raises(ValidationError):
            query.search_terms = ["changed"]  # type: ignore[misc]


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
