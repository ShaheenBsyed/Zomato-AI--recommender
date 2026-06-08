"""Phase 3: Integration Layer — deterministic candidate filtering and filter relaxation suggestions."""

from __future__ import annotations

import logging
from typing import Optional, Any
from phase1.models import Restaurant, BudgetTier, UserPreferences

logger = logging.getLogger(__name__)

# Default limit of candidates to send to LLM to prevent context window overflow
DEFAULT_CANDIDATE_LIMIT = 20

def filter_candidates(
    restaurants: list[Restaurant],
    prefs: UserPreferences,
    limit: int = DEFAULT_CANDIDATE_LIMIT
) -> tuple[list[Restaurant], dict[str, Any]]:
    """Filter restaurants according to user preferences.
    
    Returns:
        - A list of matching Restaurants (capped at `limit` via stable sort).
        - A dictionary of stats/suggestions (empty if matches found, suggestions if 0 matches).
    """
    stats = {
        "total_before": len(restaurants),
        "after_location": 0,
        "after_budget": 0,
        "after_cuisine": 0,
        "after_rating": 0,
        "suggestions": []
    }

    # Step 1: Filter by location (required, case-insensitive)
    loc_candidates = [
        r for r in restaurants
        if r.location.lower() == prefs.location.lower()
    ]
    stats["after_location"] = len(loc_candidates)
    if not loc_candidates:
        stats["suggestions"] = ["No restaurants found in this neighborhood. Please try another location."]
        return [], stats

    # Step 2: Apply budget filter
    budget_candidates = [
        r for r in loc_candidates
        if r.budget_tier == prefs.budget
    ]
    stats["after_budget"] = len(budget_candidates)

    # Step 3: Apply cuisine filter (any match, case-insensitive)
    cuisine_candidates = budget_candidates
    if prefs.cuisine:
        req_cuisine = prefs.cuisine.lower()
        cuisine_candidates = [
            r for r in budget_candidates
            if any(req_cuisine in c.lower() for c in r.cuisines)
        ]
    stats["after_cuisine"] = len(cuisine_candidates)

    # Step 4: Apply rating filter (rating >= min_rating, including None ratings only if min_rating is 0.0)
    final_candidates = []
    for r in cuisine_candidates:
        r_rating = r.rating if r.rating is not None else 0.0
        if r_rating >= prefs.min_rating:
            final_candidates.append(r)
    stats["after_rating"] = len(final_candidates)

    # Handle over-constrained case (0 matches)
    if not final_candidates:
        stats["suggestions"] = _generate_relaxation_suggestions(loc_candidates, prefs)
        return [], stats

    # Stable sort by (rating desc, votes desc, name asc)
    # Note: treating None rating as 0.0 for sorting purpose
    def sort_key(r: Restaurant) -> tuple[float, int, str]:
        rating_val = r.rating if r.rating is not None else 0.0
        return (-rating_val, -r.votes, r.name.lower())

    sorted_candidates = sorted(final_candidates, key=sort_key)
    
    # Cap candidates list
    pre_cap_count = len(sorted_candidates)
    capped_candidates = sorted_candidates[:limit]
    
    logger.info(
        "Filtered down to %d candidates (capped from %d by limit %d) for location=%s",
        len(capped_candidates),
        pre_cap_count,
        limit,
        prefs.location
    )

    return capped_candidates, stats

def _generate_relaxation_suggestions(
    loc_restaurants: list[Restaurant],
    prefs: UserPreferences
) -> list[str]:
    """Inspects the filters to recommend what fields the user can change or relax."""
    suggestions = []

    # 1. Test dropping cuisine filter
    if prefs.cuisine:
        no_cuisine_matches = []
        for r in loc_restaurants:
            r_rating = r.rating if r.rating is not None else 0.0
            if r.budget_tier == prefs.budget and r_rating >= prefs.min_rating:
                no_cuisine_matches.append(r)
        if no_cuisine_matches:
            suggestions.append(f"Remove or change the cuisine filter '{prefs.cuisine}'.")

    # 2. Test dropping rating filter (or lowering it)
    if prefs.min_rating > 0.0:
        no_rating_matches = []
        for r in loc_restaurants:
            if r.budget_tier == prefs.budget:
                if not prefs.cuisine or any(prefs.cuisine.lower() in c.lower() for c in r.cuisines):
                    no_rating_matches.append(r)
        if no_rating_matches:
            # Find the max rating available for the current budget + cuisine to recommend a realistic lower bound
            max_avail_rating = max((r.rating for r in no_rating_matches if r.rating is not None), default=0.0)
            if max_avail_rating > 0.0:
                suggestions.append(f"Lower your minimum rating filter (try {max_avail_rating} or below).")
            else:
                suggestions.append("Lower your minimum rating filter.")

    # 3. Test changing budget tier
    no_budget_matches = []
    for r in loc_restaurants:
        r_rating = r.rating if r.rating is not None else 0.0
        if r_rating >= prefs.min_rating:
            if not prefs.cuisine or any(prefs.cuisine.lower() in c.lower() for c in r.cuisines):
                no_budget_matches.append(r)
    if no_budget_matches:
        available_tiers = {r.budget_tier.value for r in no_budget_matches}
        suggestions.append(f"Try a different budget tier (options available: {', '.join(sorted(available_tiers))}).")

    if not suggestions:
        suggestions.append("Try relaxing multiple criteria (e.g. broadening budget, removing cuisine, or lowering rating).")

    return suggestions
