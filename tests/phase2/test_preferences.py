"""Unit tests for Phase 2: User preferences validation and normalization."""

from __future__ import annotations

import pytest
from phase1.models import BudgetTier, UserPreferences
from phase2.preferences import validate_and_normalize_preferences, normalize_budget


@pytest.fixture
def sample_cities() -> list[str]:
    return ["Btm", "Hsr", "Indiranagar", "Koramangala 5Th Block"]


class TestPreferencesValidation:
    def test_valid_preferences(self, sample_cities):
        data = {
            "location": "btm",
            "budget": "low",
            "cuisine": "Burgers",
            "min_rating": "4.0",
            "additional_context": "Quick service restaurant"
        }
        prefs = validate_and_normalize_preferences(data, sample_cities)
        assert prefs.location == "Btm"
        assert prefs.budget == BudgetTier.LOW
        assert prefs.cuisine == "Burgers"
        assert prefs.min_rating == 4.0
        assert prefs.additional_context == "Quick service restaurant"

    def test_missing_location(self, sample_cities):
        data = {
            "budget": "low"
        }
        with pytest.raises(ValueError, match="Location is required"):
            validate_and_normalize_preferences(data, sample_cities)

    def test_invalid_location(self, sample_cities):
        data = {
            "location": "Delhi",
            "budget": "low"
        }
        with pytest.raises(ValueError, match="Delhi.*is not available"):
            validate_and_normalize_preferences(data, sample_cities)

    def test_invalid_budget(self, sample_cities):
        data = {
            "location": "btm",
            "budget": "invalid_budget_term"
        }
        with pytest.raises(ValueError, match="Budget must be"):
            validate_and_normalize_preferences(data, sample_cities)

    def test_invalid_rating(self, sample_cities):
        data = {
            "location": "btm",
            "min_rating": "6.0"
        }
        with pytest.raises(ValueError, match="rating must be between 0.0 and 5.0"):
            validate_and_normalize_preferences(data, sample_cities)

    def test_long_context_truncation(self, sample_cities):
        long_context = "x" * 600
        data = {
            "location": "btm",
            "additional_context": long_context
        }
        prefs = validate_and_normalize_preferences(data, sample_cities)
        assert len(prefs.additional_context) == 500

    def test_budget_normalization(self, sample_cities):
        # Test synonyms for Low
        for term in ["cheap", "affordable", "pocket-friendly", "low"]:
            data = {"location": "btm", "budget": term}
            prefs = validate_and_normalize_preferences(data, sample_cities)
            assert prefs.budget == BudgetTier.LOW

        # Test synonyms for High
        for term in ["expensive", "luxury", "fine dining", "high"]:
            data = {"location": "btm", "budget": term}
            prefs = validate_and_normalize_preferences(data, sample_cities)
            assert prefs.budget == BudgetTier.HIGH

        # Test synonyms for Medium
        for term in ["moderate", "medium", "standard"]:
            data = {"location": "btm", "budget": term}
            prefs = validate_and_normalize_preferences(data, sample_cities)
            assert prefs.budget == BudgetTier.MEDIUM

        # Test numeric budget strings
        for cost_str, expected_tier in [("350", BudgetTier.LOW), ("800", BudgetTier.MEDIUM), ("2000", BudgetTier.HIGH), ("₹1,500", BudgetTier.HIGH)]:
            data = {"location": "btm", "budget": cost_str}
            prefs = validate_and_normalize_preferences(data, sample_cities)
            assert prefs.budget == expected_tier

