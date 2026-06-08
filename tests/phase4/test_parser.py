"""Unit tests for Phase 4: Response Parsing and Fallback Ranking."""

from __future__ import annotations

import pytest
from phase1.models import Restaurant, BudgetTier, UserPreferences
from phase4.parser import parse_llm_response


@pytest.fixture
def sample_restaurants() -> list[Restaurant]:
    return [
        Restaurant(
            id="rest_1",
            name="The Burger Place",
            location="Btm",
            area="BTM Layout",
            cuisines=["Burgers", "Fast Food"],
            cost_for_two=400,
            budget_tier=BudgetTier.LOW,
            rating=4.2,
            votes=150,
            attributes=["online-order"]
        ),
    ]


class TestResponseParser:
    def test_parse_valid_response(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW
        )
        raw_response = """
        {
            "recommendations": [
                {
                    "rank": 1,
                    "restaurant_id": "rest_1",
                    "name": "The Burger Place",
                    "explanation": "Great cheap burgers."
                }
            ],
            "summary": "AI summary."
        }
        """
        result = parse_llm_response(raw_response, sample_restaurants, prefs)
        assert result["fallback"] is False
        assert len(result["recommendations"]) == 1
        rec = result["recommendations"][0]
        assert rec["restaurant_id"] == "rest_1"
        assert rec["name"] == "The Burger Place"
        assert rec["explanation"] == "Great cheap burgers."
        assert rec["rating"] == 4.2
        assert rec["cost_for_two"] == 400

    def test_parse_markdown_fence(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW
        )
        raw_response = """```json
        {
            "recommendations": [
                {
                    "rank": 1,
                    "restaurant_id": "rest_1",
                    "name": "The Burger Place",
                    "explanation": "Great burgers."
                }
            ],
            "summary": "AI summary."
        }
        ```"""
        result = parse_llm_response(raw_response, sample_restaurants, prefs)
        assert result["fallback"] is False
        assert len(result["recommendations"]) == 1
        assert result["recommendations"][0]["restaurant_id"] == "rest_1"

    def test_parse_malformed_json_triggers_fallback(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW
        )
        # Malformed JSON
        raw_response = "{ recommendations: [ { name: ... } ]"
        result = parse_llm_response(raw_response, sample_restaurants, prefs)
        assert result["fallback"] is True
        assert len(result["recommendations"]) > 0
        assert "AI recommendations are temporarily unavailable" in result["summary"]
