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
