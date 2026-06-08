"""Unit tests for Phase 3: Candidate Filtering and Prompt Construction."""

from __future__ import annotations

import pytest
from phase1.models import Restaurant, BudgetTier, UserPreferences
from phase3.filter import filter_candidates
from phase3.prompt_builder import build_prompt_payload


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
        Restaurant(
            id="rest_2",
            name="Siam Kitchen",
            location="Btm",
            area="BTM Layout",
            cuisines=["Thai", "Asian"],
            cost_for_two=800,
            budget_tier=BudgetTier.MEDIUM,
            rating=4.5,
            votes=300,
            attributes=["table-booking"]
        ),
        Restaurant(
            id="rest_3",
            name="Tandoori Treat",
            location="Btm",
            area="BTM Layout",
            cuisines=["North Indian"],
            cost_for_two=450,
            budget_tier=BudgetTier.LOW,
            rating=3.9,
            votes=50,
            attributes=["online-order"]
        ),
        Restaurant(
            id="rest_4",
            name="Gourmet Hub",
            location="Indiranagar",
            area="100 Feet Road",
            cuisines=["Continental", "Italian"],
            cost_for_two=1200,
            budget_tier=BudgetTier.HIGH,
            rating=4.7,
            votes=500,
            attributes=["table-booking", "online-order"]
        ),
    ]


class TestCandidateFiltering:
    def test_filter_by_location_and_budget(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW
        )
        candidates, stats = filter_candidates(sample_restaurants, prefs)
        assert len(candidates) == 2
        assert {c.id for c in candidates} == {"rest_1", "rest_3"}
        # Check sort order: rest_1 (rating=4.2) before rest_3 (rating=3.9)
        assert candidates[0].id == "rest_1"

    def test_filter_by_cuisine(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW,
            cuisine="Burgers"
        )
        candidates, stats = filter_candidates(sample_restaurants, prefs)
        assert len(candidates) == 1
        assert candidates[0].id == "rest_1"

    def test_zero_candidates_relaxation_suggestions(self, sample_restaurants):
        # Over-constrained search: Btm, Low, Rating=4.8
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW,
            min_rating=4.8
        )
        candidates, stats = filter_candidates(sample_restaurants, prefs)
        assert len(candidates) == 0
        assert len(stats["suggestions"]) > 0
        # Suggest lowering rating
        assert any("Lower your minimum rating" in s for s in stats["suggestions"])


class TestPromptBuilder:
    def test_build_prompt(self, sample_restaurants):
        prefs = UserPreferences(
            location="Btm",
            budget=BudgetTier.LOW,
            cuisine="Burgers"
        )
        prompt = build_prompt_payload(sample_restaurants[:2], prefs)
        assert "Candidates" in prompt or "candidates" in prompt
        assert "rest_1" in prompt
        assert "The Burger Place" in prompt
        assert "low" in prompt
