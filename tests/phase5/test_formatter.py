"""Unit tests for Phase 5: Output Display Formatter."""

from __future__ import annotations

import pytest
from phase5.formatter import format_recommendation_response


class TestDisplayFormatter:
    def test_format_recommendation_response(self):
        raw_result = {
            "recommendations": [
                {
                    "rank": 1,
                    "restaurant_id": "rest_123",
                    "name": "Cafe Coffee Day",
                    "location": "Btm",
                    "area": "BTM Layout",
                    "cuisines": ["Cafe", "Fast Food"],
                    "rating": 4.1,
                    "votes": 200,
                    "cost_for_two": 300,
                    "budget_tier": "low",
                    "attributes": ["online-order"],
                    "explanation": "Perfect budget-friendly cafe."
                },
                {
                    "rank": 2,
                    "restaurant_id": "rest_456",
                    "name": "New Palace",
                    "location": "Btm",
                    "area": "BTM Layout",
                    "cuisines": ["Mughlai"],
                    "rating": None,
                    "votes": 0,
                    "cost_for_two": None,
                    "budget_tier": "medium",
                    "attributes": [],
                    "explanation": "A new restaurant option."
                }
            ],
            "summary": "Check out these options.",
            "fallback": False
        }

        formatted = format_recommendation_response(raw_result)
        
        assert formatted["fallback"] is False
        assert formatted["summary"] == "Check out these options."
        assert len(formatted["recommendations"]) == 2

        # Check first recommendation
        rec1 = formatted["recommendations"][0]
        assert rec1["rating_text"] == "4.1 ★"
        assert rec1["cost_text"] == "₹300 for two"
        assert rec1["rating_class"] == "rating-high"

        # Check second recommendation (with None/NEW rating and cost)
        rec2 = formatted["recommendations"][1]
        assert rec2["rating_text"] == "NEW"
        assert rec2["cost_text"] == "Approx cost unknown"
        assert rec2["rating_class"] == "rating-new"
