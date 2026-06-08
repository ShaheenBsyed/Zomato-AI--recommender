"""Phase 4: Recommendation Engine — response parsing, structured validation, and fallback ranking."""

from __future__ import annotations

import re
import json
import logging
from typing import Any, Optional
from phase1.models import Restaurant, BudgetTier, UserPreferences


logger = logging.getLogger(__name__)

class ParsingError(Exception):
    """Raised when JSON parsing or structural validation fails completely."""
    pass

def parse_llm_response(
    raw_response: str,
    candidates: list[Restaurant],
    prefs: UserPreferences
) -> dict[str, Any]:
    """Parse the raw LLM string, validate and map it to candidates, and return final UI payload."""
    try:
        data = _clean_and_parse_json(raw_response)
    except Exception as exc:
        logger.warning("Failed to parse raw LLM JSON: %s. Reverting to fallback ranker.", exc)
        return generate_fallback_recommendations(candidates, prefs, "Invalid JSON structure returned by AI.")

    recommendations_raw = data.get("recommendations")
    if not isinstance(recommendations_raw, list):
        logger.warning("No 'recommendations' list found in LLM output. Reverting to fallback.")
        return generate_fallback_recommendations(candidates, prefs, "Missing recommendations list.")

    candidate_map = {r.id: r for r in candidates}
    # Create name map for fuzzy fallback if ID is mistyped
    candidate_name_map = {r.name.lower().strip(): r for r in candidates}

    valid_recs = []
    
    for idx, rec in enumerate(recommendations_raw):
        if not isinstance(rec, dict):
            continue
            
        restaurant_id = rec.get("restaurant_id")
        rec_name = rec.get("name", "").strip()
        explanation = rec.get("explanation", "").strip()

        # 1. Match back to candidate structured object
        matched_restaurant: Optional[Restaurant] = None
        if restaurant_id in candidate_map:
            matched_restaurant = candidate_map[restaurant_id]
        elif rec_name.lower().strip() in candidate_name_map:
            matched_restaurant = candidate_name_map[rec_name.lower().strip()]
            logger.warning("LLM mistyped ID '%s' but name matched '%s'", restaurant_id, rec_name)
        
        if matched_restaurant is None:
            logger.warning("LLM hallucinated restaurant ID '%s' name '%s'. Dropping.", restaurant_id, rec_name)
            continue

        # 2. Check/Build Explanation
        if not explanation:
            rating_str = f"{matched_restaurant.rating}/5" if matched_restaurant.rating else "NEW"
            cuisine_str = ", ".join(matched_restaurant.cuisines)
            explanation = (
                f"Rated {rating_str} for {cuisine_str} in {matched_restaurant.location}, "
                f"matching your {prefs.budget.value} budget."
            )

        # 3. Create Recommendation Card (always pull details from structured candidate to prevent hallucination)
        valid_recs.append({
            "restaurant_id": matched_restaurant.id,
            "name": matched_restaurant.name,
            "location": matched_restaurant.location,
            "area": matched_restaurant.area,
            "cuisines": matched_restaurant.cuisines,
            "rating": matched_restaurant.rating,
            "votes": matched_restaurant.votes,
            "cost_for_two": matched_restaurant.cost_for_two,
            "budget_tier": matched_restaurant.budget_tier.value,
            "attributes": matched_restaurant.attributes,
            "explanation": explanation
        })

    # If all items were invalid or list is empty, trigger fallback
    if not valid_recs:
        logger.warning("No valid recommendations could be parsed or matched. Reverting to fallback.")
        return generate_fallback_recommendations(candidates, prefs, "No valid restaurants were matched.")

    # Re-assign ranks sequentially (1, 2, 3...) to guarantee correct order
    for index, rec in enumerate(valid_recs):
        rec["rank"] = index + 1

    summary = data.get("summary", "").strip()
    if not summary:
        summary = f"Here are the top matches for your request in {prefs.location}."

    return {
        "recommendations": valid_recs,
        "summary": summary,
        "fallback": False
    }

def _clean_and_parse_json(text: str) -> dict[str, Any]:
    """Cleans up markdown fences and parses JSON string."""
    cleaned = text.strip()
    
    # Strip markdown code blocks: e.g. ```json ... ```
    if cleaned.startswith("```"):
        # Match anything inside ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
            
    # Try to parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Final salvage: search for first '{' and last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            try:
                return json.loads(cleaned[start_idx:end_idx+1])
            except json.JSONDecodeError:
                pass
        raise exc

def generate_fallback_recommendations(
    candidates: list[Restaurant],
    prefs: UserPreferences,
    reason: str = ""
) -> dict[str, Any]:
    """Generates default recommendation rankings and explanations directly from the filtered candidates."""
    logger.info("Generating fallback recommendations. Reason: %s", reason)
    
    # Take top 5 candidates (already sorted by rating desc, votes desc)
    top_candidates = candidates[:5]
    recs = []

    for index, r in enumerate(top_candidates):
        rating_str = f"{r.rating}/5" if r.rating is not None else "NEW"
        cuisine_str = ", ".join(r.cuisines)
        
        explanation = (
            f"Rated {rating_str} for {cuisine_str} in {r.location}, "
            f"matching your {prefs.budget.value} budget requirements."
        )
        if r.rating is None:
            explanation = (
                f"NEW restaurant serving {cuisine_str} in {r.location}, "
                f"fitting your {prefs.budget.value} budget."
            )

        recs.append({
            "rank": index + 1,
            "restaurant_id": r.id,
            "name": r.name,
            "location": r.location,
            "area": r.area,
            "cuisines": r.cuisines,
            "rating": r.rating,
            "votes": r.votes,
            "cost_for_two": r.cost_for_two,
            "budget_tier": r.budget_tier.value,
            "attributes": r.attributes,
            "explanation": explanation
        })

    summary = "AI recommendations are temporarily unavailable. Displaying top-rated options matching your filters."
    
    return {
        "recommendations": recs,
        "summary": summary,
        "fallback": True,
        "fallback_reason": reason
    }
