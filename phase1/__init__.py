"""Data layer for the restaurant recommendation system."""

from phase1.models import BudgetTier, IngestionStats, Restaurant

__all__ = [
    "BudgetTier",
    "IngestionError",
    "IngestionStats",
    "Restaurant",
    "RestaurantStore",
    "run_ingestion",
]


def __getattr__(name: str):
    if name in {"IngestionError", "RestaurantStore", "run_ingestion"}:
        from phase1 import ingestion as _ingestion

        return getattr(_ingestion, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
