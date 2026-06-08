"""Phase 1: Data ingestion — load, preprocess, cache, and store restaurant data."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Optional

from phase1.config import (
    BUDGET_LOW_MAX,
    BUDGET_MEDIUM_MAX,
    CACHE_DIR,
    CACHE_FILE,
    CACHE_META_FILE,
    DATASET_NAME,
    DATASET_REVISION,
    LOCATION_ALIASES,
    MAX_DOWNLOAD_RETRIES,
    OPTIONAL_RAW_COLUMNS,
    REQUIRED_RAW_COLUMNS,
    RETRY_BASE_DELAY_SECONDS,
)
from phase1.models import BudgetTier, IngestionStats, Restaurant


logger = logging.getLogger(__name__)

NON_NUMERIC_RATING_TOKENS = frozenset({"new", "-", "—", "", "nan", "none", "null"})
COST_COLUMN = "approx_cost(for two people)"
CITY_COLUMN = "listed_in(city)"
LISTED_TYPE_COLUMN = "listed_in(type)"


class IngestionError(Exception):
    """Raised when restaurant data cannot be loaded or validated."""


class RestaurantStore:
    """In-memory store of preprocessed restaurants with cache-backed loading."""

    def __init__(self, restaurants: list[Restaurant], stats: Optional[IngestionStats] = None) -> None:
        self.restaurants = restaurants
        self.stats = stats or IngestionStats(final_count=len(restaurants))
        self._cities: Optional[list[str]] = None

    @classmethod
    def load(cls, force_refresh: bool = False, cache_path: Path = CACHE_FILE) -> RestaurantStore:
        """Load restaurants from cache or Hugging Face, with automatic caching."""
        if not force_refresh:
            cached = _load_cache(cache_path)
            if cached is not None:
                restaurants, stats = cached
                logger.info("Loaded %d restaurants from cache at %s", len(restaurants), cache_path)
                return cls(restaurants, stats)

        logger.info("Downloading dataset from Hugging Face: %s", DATASET_NAME)
        raw_rows = _download_dataset_with_retry()
        restaurants, stats = preprocess_rows(raw_rows)
        _save_cache(cache_path, restaurants, stats)
        return cls(restaurants, stats)

    def get_cities(self) -> list[str]:
        """Return sorted unique canonical city names."""
        if self._cities is None:
            self._cities = sorted({r.location for r in self.restaurants if r.location})
        return self._cities

    def filter_by_city(self, city: str) -> list[Restaurant]:
        """Return restaurants whose canonical city matches (case-insensitive)."""
        normalized = normalize_city(city)
        if not normalized:
            return []
        return [r for r in self.restaurants if r.location.lower() == normalized.lower()]

    def __len__(self) -> int:
        return len(self.restaurants)


def _download_dataset_with_retry() -> list[dict[str, Any]]:
    last_error: Optional[Exception] = None

    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        try:
            return _download_dataset()
        except Exception as exc:
            last_error = exc
            if attempt < MAX_DOWNLOAD_RETRIES:
                delay = RETRY_BASE_DELAY_SECONDS ** attempt
                logger.warning(
                    "Dataset download failed (attempt %d/%d): %s. Retrying in %ds.",
                    attempt,
                    MAX_DOWNLOAD_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)

    raise IngestionError(
        "Unable to load restaurant data. Check your connection or try again later."
    ) from last_error


def _download_dataset() -> list[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise IngestionError(
            "The 'datasets' package is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    dataset = load_dataset(
        DATASET_NAME,
        revision=DATASET_REVISION,
        split="train",
    )
    validate_raw_schema(dataset.column_names)
    rows = [dict(row) for row in dataset]
    logger.info("Downloaded %d raw rows from Hugging Face", len(rows))
    return rows


def validate_raw_schema(columns: list[str]) -> None:
    """Fail fast if required dataset columns are missing."""
    column_set = set(columns)
    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in column_set]
    if missing:
        raise IngestionError(
            f"Dataset schema mismatch. Missing required columns: {', '.join(missing)}"
        )


def preprocess_rows(raw_rows: list[dict[str, Any]]) -> tuple[list[Restaurant], IngestionStats]:
    """Map, clean, validate, and deduplicate raw dataset rows."""
    stats = IngestionStats(raw_rows=len(raw_rows))
    restaurants: list[Restaurant] = []

    for index, row in enumerate(raw_rows):
        mapped = map_row_to_restaurant(row, index, stats)
        if mapped is not None:
            restaurants.append(mapped)

    before_dedup = len(restaurants)
    restaurants = deduplicate_restaurants(restaurants)
    stats.duplicates_removed = before_dedup - len(restaurants)
    stats.final_count = len(restaurants)

    if stats.final_count == 0:
        raise IngestionError("Dataset loaded but contains no restaurants.")

    logger.info(
        "Preprocessing complete: %d restaurants (%d invalid names, %d dupes removed)",
        stats.final_count,
        stats.dropped_invalid_name,
        stats.duplicates_removed,
    )
    return restaurants, stats


def map_row_to_restaurant(
    row: dict[str, Any],
    index: int,
    stats: IngestionStats,
) -> Optional[Restaurant]:
    """Map a single raw row to a Restaurant, or None if it should be dropped."""
    name = _clean_text(row.get("name"))
    if not name:
        stats.dropped_invalid_name += 1
        return None

    city = normalize_city(row.get(CITY_COLUMN) or row.get("location"))
    area = _clean_text(row.get("location")) or ""
    cuisines = parse_cuisines(row.get("cuisines"))
    cost_for_two = parse_cost(row.get(COST_COLUMN))
    rating = parse_rating(row.get("rate"))
    votes = _parse_votes(row.get("votes"))
    budget_tier = derive_budget_tier(cost_for_two)
    attributes = build_attributes(row)

    restaurant_id = _make_restaurant_id(name, city, area, index)

    return Restaurant(
        id=restaurant_id,
        name=name,
        location=city,
        area=area,
        cuisines=cuisines,
        cost_for_two=cost_for_two,
        budget_tier=budget_tier,
        rating=rating,
        votes=votes,
        attributes=attributes,
    )


def normalize_city(raw_city: Any) -> str:
    """Normalize a city name to a canonical display value."""
    text = _clean_text(raw_city)
    if not text:
        return "Unknown"

    key = text.lower()
    if key in LOCATION_ALIASES:
        return LOCATION_ALIASES[key]

    # Handle "BTM, Bangalore" style values — take the last segment as city hint
    if "," in text:
        parts = [_clean_text(part) for part in text.split(",") if _clean_text(part)]
        if parts:
            candidate = parts[-1].lower()
            if candidate in LOCATION_ALIASES:
                return LOCATION_ALIASES[candidate]
            return parts[-1].title()

    return text.title()


def parse_rating(raw_rate: Any) -> Optional[float]:
    """Parse rating strings, returning None for NEW/unrated entries."""
    if raw_rate is None:
        return None

    text = str(raw_rate).strip()
    if text.lower() in NON_NUMERIC_RATING_TOKENS:
        return None

    # Handle "4.1/5" format
    if "/" in text:
        text = text.split("/")[0].strip()

    try:
        value = float(text)
    except ValueError:
        return None

    if value < 0 or value > 5:
        logger.debug("Clamping out-of-range rating: %s", value)
        value = max(0.0, min(5.0, value))

    return round(value, 1)


def parse_cost(raw_cost: Any) -> Optional[int]:
    """Parse approximate cost for two into a single INR integer."""
    if raw_cost is None:
        return None

    text = str(raw_cost).strip().lower()
    if not text or text in {"nan", "none", "null", "-"}:
        return None

    # Extract all numeric tokens; handle ranges like "300-500"
    numbers = [int(match) for match in re.findall(r"\d+", text.replace(",", ""))]
    if not numbers:
        return None

    if len(numbers) >= 2 and ("-" in text or "to" in text):
        return int(sum(numbers[:2]) / 2)

    return numbers[0]


def parse_cuisines(raw_cuisines: Any) -> list[str]:
    """Split comma-separated cuisines into a trimmed list."""
    text = _clean_text(raw_cuisines)
    if not text:
        return []

    parts = [part.strip() for part in text.split(",") if part.strip()]
    return parts


def derive_budget_tier(cost_for_two: Optional[int]) -> BudgetTier:
    """Derive budget tier from normalized cost; default to medium when unknown."""
    if cost_for_two is None:
        return BudgetTier.MEDIUM
    if cost_for_two <= BUDGET_LOW_MAX:
        return BudgetTier.LOW
    if cost_for_two <= BUDGET_MEDIUM_MAX:
        return BudgetTier.MEDIUM
    return BudgetTier.HIGH


def build_attributes(row: dict[str, Any]) -> list[str]:
    """Build attribute tags from structured row fields."""
    attributes: list[str] = []

    if _is_yes(row.get("online_order")):
        attributes.append("online-order")
    if _is_yes(row.get("book_table")):
        attributes.append("table-booking")

    rest_type = _clean_text(row.get("rest_type"))
    if rest_type:
        attributes.append(rest_type.lower())

    listed_type = _clean_text(row.get(LISTED_TYPE_COLUMN))
    if listed_type:
        attributes.append(listed_type.lower())

    return attributes


def deduplicate_restaurants(restaurants: list[Restaurant]) -> list[Restaurant]:
    """Keep the best row per (normalized name, city) by votes then rating."""
    best_by_key: dict[tuple[str, str], Restaurant] = {}

    for restaurant in restaurants:
        key = (_normalize_name(restaurant.name), restaurant.location.lower())
        existing = best_by_key.get(key)
        if existing is None or _restaurant_sort_key(restaurant) > _restaurant_sort_key(existing):
            best_by_key[key] = restaurant

    return list(best_by_key.values())


def _restaurant_sort_key(restaurant: Restaurant) -> tuple[int, float, str]:
    rating = restaurant.rating if restaurant.rating is not None else -1.0
    return (restaurant.votes, rating, restaurant.id)


def _make_restaurant_id(name: str, city: str, area: str, index: int) -> str:
    payload = f"{name}|{city}|{area}|{index}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:12]
    return f"rest_{digest}"


def _normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name).strip().lower()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFC", str(value)).strip()
    return text


def _parse_votes(raw_votes: Any) -> int:
    if raw_votes is None:
        return 0
    try:
        return max(0, int(raw_votes))
    except (TypeError, ValueError):
        return 0


def _is_yes(value: Any) -> bool:
    return _clean_text(value).lower() == "yes"


def _save_cache(
    cache_path: Path,
    restaurants: list[Restaurant],
    stats: IngestionStats,
) -> None:
    """Atomically write cache and metadata files."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset": DATASET_NAME,
        "revision": DATASET_REVISION,
        "restaurants": [r.to_dict() for r in restaurants],
        "stats": stats.to_dict(),
    }
    meta = {
        "dataset": DATASET_NAME,
        "revision": DATASET_REVISION,
        "count": len(restaurants),
        "stats": stats.to_dict(),
    }

    temp_path = cache_path.with_suffix(".tmp")
    temp_meta_path = CACHE_META_FILE.with_suffix(".tmp")

    try:
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(cache_path)
        temp_meta_path.replace(CACHE_META_FILE)
        logger.info("Cached %d restaurants to %s", len(restaurants), cache_path)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        temp_meta_path.unlink(missing_ok=True)
        raise IngestionError(f"Failed to write cache file: {cache_path}") from exc


def _load_cache(cache_path: Path) -> Optional[tuple[list[Restaurant], IngestionStats]]:
    """Load restaurants from cache, returning None if missing or corrupt."""
    if not cache_path.exists():
        return None

    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("revision") != DATASET_REVISION:
            logger.warning("Cache revision mismatch; ignoring stale cache.")
            return None

        restaurants = [Restaurant.from_dict(item) for item in payload["restaurants"]]
        stats_data = payload.get("stats", {})
        stats = IngestionStats(**stats_data) if stats_data else IngestionStats(final_count=len(restaurants))

        if len(restaurants) == 0:
            logger.warning("Cache file is empty; ignoring.")
            return None

        return restaurants, stats
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Corrupt cache at %s (%s); will re-download.", cache_path, exc)
        cache_path.unlink(missing_ok=True)
        CACHE_META_FILE.unlink(missing_ok=True)
        return None


def run_ingestion(force_refresh: bool = False) -> RestaurantStore:
    """CLI-friendly entry point for Phase 1 ingestion."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    store = RestaurantStore.load(force_refresh=force_refresh)
    print(f"Loaded {len(store)} restaurants across {len(store.get_cities())} cities.")
    print(f"Stats: {store.stats.to_dict()}")
    return store


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Zomato restaurant dataset (Phase 1)")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore cache and re-download from Hugging Face",
    )
    args = parser.parse_args()
    run_ingestion(force_refresh=args.force_refresh)
