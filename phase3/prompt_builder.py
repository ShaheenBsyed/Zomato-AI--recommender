"""Phase 3: Integration Layer — prompt construction and templating for LLM reasoning."""

from __future__ import annotations

import json
from typing import Any
from phase1.models import Restaurant, UserPreferences


PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """You are a food critic and local restaurant guide. Your task is to rank the provided candidate restaurants and choose the best matches (up to 5) that align with the user's preferences.

You MUST follow these strict rules:
1. ONLY recommend restaurants from the provided "Candidates" list. Do NOT invent or hallucinate any restaurants.
2. For each recommendation, include the EXACT `restaurant_id` from the candidate item.
3. Provide a personalized, high-quality, 2-3 sentence explanation for why each restaurant fits the user's needs, referencing their "Additional Context" if relevant (e.g., family-friendly, quiet, specific dishes, quick service).
4. Do NOT change or hallucinate the ratings, cost, or cuisine in your output — use the structured data.
5. Provide a brief, single-sentence summary of the overall recommendations and any trade-offs (e.g., "While Cafe X has the best rating, Cafe Y is closer to your request for quick service").
6. You MUST respond with ONLY a valid JSON object. Do not include any conversational intro, outro, or markdown code fences (other than optionally wrapping the JSON in ```json ... ```).

JSON Response Schema:
{
  "recommendations": [
    {
      "rank": 1,
      "restaurant_id": "rest_...",
      "name": "...",
      "explanation": "..."
    }
  ],
  "summary": "..."
}"""

def build_prompt_payload(
    candidates: list[Restaurant],
    prefs: UserPreferences
) -> str:
    """Serialize the user preferences and candidate restaurants into the final LLM prompt."""
    
    # Structure candidate information to be compact and JSON-serializable
    candidate_list = []
    for r in candidates:
        candidate_list.append({
            "restaurant_id": r.id,
            "name": r.name,
            "cuisines": r.cuisines,
            "rating": r.rating if r.rating is not None else "NEW/No rating",
            "cost_for_two_inr": r.cost_for_two if r.cost_for_two is not None else "Unknown",
            "attributes": r.attributes
        })

    # Adjust instructions slightly if only one candidate is available
    count_to_select = min(5, len(candidates))
    selection_guideline = (
        f"Select and rank the top {count_to_select} restaurants from the candidates list."
        if len(candidates) > 1
        else "Explain why this single matching candidate is a good fit."
    )

    user_payload = {
        "user_preferences": {
            "target_location": prefs.location,
            "requested_budget": prefs.budget.value,
            "requested_cuisine": prefs.cuisine if prefs.cuisine else "Any",
            "minimum_rating": prefs.min_rating,
            "additional_context": prefs.additional_context if prefs.additional_context else "None"
        },
        "candidates": candidate_list,
        "instructions": {
            "selection_guideline": selection_guideline,
            "max_recommendations": count_to_select
        }
    }

    prompt = f"{SYSTEM_PROMPT}\n\nUser Input Data:\n{json.dumps(user_payload, indent=2, ensure_ascii=False)}"
    return prompt
