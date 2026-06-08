"""Phase 2: User Input — validation and normalization of user preferences."""

from __future__ import annotations

from typing import Any, Optional
from phase1.models import BudgetTier, UserPreferences
from phase1.config import LOCATION_ALIASES


def normalize_budget(raw_budget: Any) -> BudgetTier:
    """Normalize raw budget string, mapping free-text synonyms (like 'cheap', 'expensive') to structured BudgetTiers."""
    if not raw_budget:
        return BudgetTier.MEDIUM
    
    text = str(raw_budget).strip().lower()
    
    # Try parsing as a number (e.g. "2000" or "450")
    # Clean any commas or currency symbols
    clean_text = text.replace(",", "").replace("₹", "").replace("rs", "").strip()
    try:
        cost_val = int(clean_text)
        from phase1.config import BUDGET_LOW_MAX, BUDGET_MEDIUM_MAX
        if cost_val <= BUDGET_LOW_MAX:
            return BudgetTier.LOW
        if cost_val <= BUDGET_MEDIUM_MAX:
            return BudgetTier.MEDIUM
        return BudgetTier.HIGH
    except (ValueError, ImportError):
        pass

    # Try exact match first
    try:
        return BudgetTier(text)
    except ValueError:
        pass
        
    # Synonyms mapping
    low_synonyms = {"cheap", "affordable", "pocket-friendly", "budget", "low", "value", "economical", "inexpensive"}
    medium_synonyms = {"moderate", "medium", "average", "normal", "standard", "mid-range", "mid"}
    high_synonyms = {"expensive", "luxury", "fine dining", "premium", "high", "fancy", "posh", "costly"}
    
    if text in low_synonyms:
        return BudgetTier.LOW
    if text in medium_synonyms:
        return BudgetTier.MEDIUM
    if text in high_synonyms:
        return BudgetTier.HIGH
        
    raise ValueError(f"Unable to normalize budget '{raw_budget}'.")


def validate_and_normalize_preferences(
    data: dict[str, Any],
    valid_cities: list[str]
) -> UserPreferences:
    """Validate user raw preferences, apply defaults, and return a normalized UserPreferences object.
    
    Raises ValueError with descriptive messages for validation failures.
    """
    if not isinstance(data, dict):
        raise ValueError("Invalid request format. Expected a JSON object.")

    # 1. Location Validation
    location_raw = data.get("location")
    if not location_raw or not str(location_raw).strip():
        raise ValueError("Location is required.")
    
    location = str(location_raw).strip()
    
    # Check alias mapping
    location_lower = location.lower()
    if location_lower in LOCATION_ALIASES:
        location = LOCATION_ALIASES[location_lower]
    
    # Handle "BTM, Bangalore" style or clean title
    if "," in location:
        parts = [p.strip() for p in location.split(",") if p.strip()]
        if parts:
            candidate = parts[-1].lower()
            if candidate in LOCATION_ALIASES:
                location = LOCATION_ALIASES[candidate]
            else:
                location = parts[-1].title()
    else:
        location = location.title()

    # Verify if location is available in the store
    valid_cities_lower = {c.lower() for c in valid_cities}
    if location.lower() not in valid_cities_lower:
        raise ValueError(
            f"Location '{location}' is not available in our dataset. "
            f"Please choose from available locations."
        )
    
    # Match exact casing from valid cities list
    for c in valid_cities:
        if c.lower() == location.lower():
            location = c
            break

    # 2. Budget Validation
    budget_raw = data.get("budget")
    try:
        budget = normalize_budget(budget_raw)
    except ValueError as exc:
        raise ValueError("Budget must be low, medium, or high.") from exc


    # 3. Cuisine Validation (Optional)
    cuisine_raw = data.get("cuisine")
    if cuisine_raw is not None:
        cuisine = str(cuisine_raw).strip()
        if not cuisine:
            cuisine = None
    else:
        cuisine = None

    # 4. Rating Validation (Optional)
    rating_raw = data.get("min_rating")
    if rating_raw is None or rating_raw == "":
        min_rating = 0.0
    else:
        try:
            min_rating = float(rating_raw)
        except ValueError as exc:
            raise ValueError("Minimum rating must be a number.") from exc
        
        if min_rating < 0.0 or min_rating > 5.0:
            raise ValueError("Minimum rating must be between 0.0 and 5.0.")

    # 5. Additional Context Validation (Optional)
    context_raw = data.get("additional_context")
    if context_raw is not None:
        context = str(context_raw).strip()
        # Enforce max character limit of 500 to prevent token/prompt bloat
        if len(context) > 500:
            context = context[:500]
    else:
        context = ""

    return UserPreferences(
        location=location,
        budget=budget,
        cuisine=cuisine,
        min_rating=min_rating,
        additional_context=context
    )
