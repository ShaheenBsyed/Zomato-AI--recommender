"""Phase 5: Output Display — Formatting recommendation results for the view."""

from __future__ import annotations

from typing import Any


def format_recommendation_response(data: dict[str, Any]) -> dict[str, Any]:
    """Format the raw recommendation response into UI view models."""
    formatted_recs = []
    
    for rec in data.get("recommendations", []):
        cost = rec.get("cost_for_two")
        cost_str = f"₹{cost} for two" if cost else "Approx cost unknown"
        
        rating = rec.get("rating")
        rating_str = f"{rating} ★" if rating is not None else "NEW"

        # Map rating values to CSS classes for frontend visual layout
        rating_class = "rating-new"
        if rating is not None:
            if rating >= 4.0:
                rating_class = "rating-high"
            elif rating >= 3.0:
                rating_class = "rating-medium"

        formatted_item = dict(rec)
        formatted_item["rating_text"] = rating_str
        formatted_item["cost_text"] = cost_str
        formatted_item["rating_class"] = rating_class
        formatted_recs.append(formatted_item)

    return {
        "recommendations": formatted_recs,
        "summary": data.get("summary", ""),
        "fallback": data.get("fallback", False)
    }
