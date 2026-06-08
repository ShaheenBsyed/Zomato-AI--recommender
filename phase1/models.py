"""Data models for the restaurant recommendation system."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class BudgetTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Restaurant:
    id: str
    name: str
    location: str
    area: str
    cuisines: list[str]
    cost_for_two: Optional[int]
    budget_tier: BudgetTier
    rating: Optional[float]
    votes: int
    attributes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["budget_tier"] = self.budget_tier.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Restaurant:
        return cls(
            id=data["id"],
            name=data["name"],
            location=data["location"],
            area=data.get("area", ""),
            cuisines=list(data.get("cuisines", [])),
            cost_for_two=data.get("cost_for_two"),
            budget_tier=BudgetTier(data["budget_tier"]),
            rating=data.get("rating"),
            votes=int(data.get("votes", 0)),
            attributes=list(data.get("attributes", [])),
        )


@dataclass
class IngestionStats:
    raw_rows: int = 0
    dropped_invalid_name: int = 0
    dropped_invalid_rating: int = 0
    duplicates_removed: int = 0
    final_count: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass
class UserPreferences:
    location: str
    budget: BudgetTier
    cuisine: Optional[str] = None
    min_rating: float = 0.0
    additional_context: str = ""

