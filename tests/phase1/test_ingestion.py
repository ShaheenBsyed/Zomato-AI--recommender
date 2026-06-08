"""Unit tests for Phase 1 data ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase1.config import CACHE_FILE, DATASET_REVISION
from phase1.ingestion import (
    _load_cache,
    _save_cache,
    build_attributes,
    deduplicate_restaurants,
    derive_budget_tier,
    map_row_to_restaurant,
    normalize_city,
    parse_cost,
    parse_cuisines,
    parse_rating,
    preprocess_rows,
    validate_raw_schema,
)
from phase1.models import BudgetTier, IngestionStats, Restaurant


def _sample_row(**overrides) -> dict:
    base = {
        "name": "Test Café",
        "location": "Koramangala",
        "listed_in(city)": "Bangalore",
        "cuisines": "Italian, Cafe",
        "approx_cost(for two people)": "800",
        "rate": "4.2/5",
        "votes": 120,
        "online_order": "Yes",
        "book_table": "No",
        "rest_type": "Cafe",
        "listed_in(type)": "Buffet",
    }
    base.update(overrides)
    return base


class TestParseRating:
    def test_parses_fraction_format(self):
        assert parse_rating("4.2/5") == 4.2

    def test_new_rating_returns_none(self):
        assert parse_rating("NEW") is None

    def test_dash_rating_returns_none(self):
        assert parse_rating("-") is None

    def test_clamps_out_of_range(self):
        assert parse_rating("8.5") == 5.0
        assert parse_rating("-1") == 0.0


class TestParseCost:
    def test_parses_plain_number(self):
        assert parse_cost("800") == 800

    def test_parses_range_midpoint(self):
        assert parse_cost("300-500") == 400

    def test_parses_currency_text(self):
        assert parse_cost("₹500 for two") == 500

    def test_missing_cost_returns_none(self):
        assert parse_cost(None) is None
        assert parse_cost("-") is None


class TestParseCuisines:
    def test_splits_comma_separated(self):
        assert parse_cuisines("North Indian, Chinese, Fast Food") == [
            "North Indian",
            "Chinese",
            "Fast Food",
        ]

    def test_empty_returns_empty_list(self):
        assert parse_cuisines("") == []


class TestNormalizeCity:
    def test_alias_bengaluru_to_bangalore(self):
        assert normalize_city("Bengaluru") == "Bangalore"

    def test_case_insensitive(self):
        assert normalize_city("delhi") == "New Delhi"

    def test_comma_separated_location(self):
        assert normalize_city("BTM, Bangalore") == "Bangalore"


class TestDeriveBudgetTier:
    def test_low(self):
        assert derive_budget_tier(300) == BudgetTier.LOW

    def test_medium(self):
        assert derive_budget_tier(800) == BudgetTier.MEDIUM

    def test_high(self):
        assert derive_budget_tier(1500) == BudgetTier.HIGH

    def test_unknown_defaults_medium(self):
        assert derive_budget_tier(None) == BudgetTier.MEDIUM


class TestBuildAttributes:
    def test_maps_yes_fields(self):
        attrs = build_attributes(_sample_row())
        assert "online-order" in attrs
        assert "cafe" in attrs
        assert "buffet" in attrs
        assert "table-booking" not in attrs


class TestMapRowToRestaurant:
    def test_maps_valid_row(self):
        stats = IngestionStats()
        restaurant = map_row_to_restaurant(_sample_row(), 0, stats)
        assert restaurant is not None
        assert restaurant.name == "Test Café"
        assert restaurant.location == "Bangalore"
        assert restaurant.area == "Koramangala"
        assert restaurant.rating == 4.2
        assert restaurant.cost_for_two == 800
        assert restaurant.budget_tier == BudgetTier.MEDIUM

    def test_drops_blank_name(self):
        stats = IngestionStats()
        result = map_row_to_restaurant(_sample_row(name="   "), 0, stats)
        assert result is None
        assert stats.dropped_invalid_name == 1


class TestDeduplicateRestaurants:
    def test_keeps_highest_votes(self):
        a = Restaurant(
            id="a",
            name="Same Place",
            location="Bangalore",
            area="A",
            cuisines=["Indian"],
            cost_for_two=500,
            budget_tier=BudgetTier.LOW,
            rating=4.0,
            votes=10,
        )
        b = Restaurant(
            id="b",
            name="same place",
            location="Bangalore",
            area="B",
            cuisines=["Indian"],
            cost_for_two=500,
            budget_tier=BudgetTier.LOW,
            rating=4.5,
            votes=50,
        )
        result = deduplicate_restaurants([a, b])
        assert len(result) == 1
        assert result[0].id == "b"


class TestPreprocessRows:
    def test_preprocesses_multiple_rows(self):
        rows = [
            _sample_row(name="A"),
            _sample_row(name="B", **{"listed_in(city)": "Delhi"}),
            _sample_row(name=""),
        ]
        restaurants, stats = preprocess_rows(rows)
        assert len(restaurants) == 2
        assert stats.raw_rows == 3
        assert stats.dropped_invalid_name == 1

    def test_empty_after_drop_raises(self):
        with pytest.raises(Exception, match="contains no restaurants"):
            preprocess_rows([_sample_row(name="")])


class TestValidateRawSchema:
    def test_passes_with_required_columns(self):
        validate_raw_schema(list(_sample_row().keys()))

    def test_fails_when_missing_required(self):
        with pytest.raises(Exception, match="Missing required columns"):
            validate_raw_schema(["name"])


class TestCacheRoundTrip:
    def test_save_and_load_cache(self, tmp_path: Path):
        cache_path = tmp_path / "restaurants.json"
        restaurants = [
            Restaurant(
                id="rest_1",
                name="Cache Test",
                location="Bangalore",
                area="Indiranagar",
                cuisines=["Chinese"],
                cost_for_two=600,
                budget_tier=BudgetTier.MEDIUM,
                rating=4.1,
                votes=25,
                attributes=["online-order"],
            )
        ]
        stats = IngestionStats(raw_rows=1, final_count=1)
        _save_cache(cache_path, restaurants, stats)

        loaded = _load_cache(cache_path)
        assert loaded is not None
        loaded_restaurants, loaded_stats = loaded
        assert len(loaded_restaurants) == 1
        assert loaded_restaurants[0].name == "Cache Test"
        assert loaded_stats.final_count == 1

    def test_corrupt_cache_returns_none(self, tmp_path: Path):
        cache_path = tmp_path / "restaurants.json"
        cache_path.write_text("{not valid json", encoding="utf-8")
        assert _load_cache(cache_path) is None

    def test_revision_mismatch_returns_none(self, tmp_path: Path):
        cache_path = tmp_path / "restaurants.json"
        payload = {
            "dataset": "test",
            "revision": "stale-revision",
            "restaurants": [],
            "stats": {},
        }
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        assert _load_cache(cache_path) is None


class TestRestaurantSerialization:
    def test_to_dict_and_from_dict(self):
        original = Restaurant(
            id="rest_x",
            name="Round Trip",
            location="Mumbai",
            area="Andheri",
            cuisines=["Italian"],
            cost_for_two=1200,
            budget_tier=BudgetTier.HIGH,
            rating=None,
            votes=0,
            attributes=["delivery"],
        )
        restored = Restaurant.from_dict(original.to_dict())
        assert restored == original
