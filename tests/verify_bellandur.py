import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from phase1.ingestion import RestaurantStore
from phase2.preferences import validate_and_normalize_preferences
from phase3.filter import filter_candidates
from phase3.prompt_builder import build_prompt_payload
from phase4.llm_client import LLMClient
from phase4.parser import parse_llm_response, generate_fallback_recommendations
from phase5.formatter import format_recommendation_response

def main():
    print("=========================================================")
    print("Testing Phase 4: Live Gemini Recommendation Engine")
    print("=========================================================")
    
    # 1. Load data
    print("Loading restaurant store...")
    store = RestaurantStore.load()
    
    # 2. Input data (Bellandur, budget 2000, rating 4.0)
    raw_input = {
        "location": "Bellandur",
        "budget": "2000", # Will be normalized to High
        "min_rating": 4.0,
        "additional_context": "good seating, family friendly"
    }
    print(f"Inputs: {raw_input}")
    
    # 3. Validate and Normalize
    prefs = validate_and_normalize_preferences(raw_input, store.get_cities())
    print(f"Normalized preferences: location={prefs.location}, budget={prefs.budget.value}, min_rating={prefs.min_rating}")
    
    # 4. Filter Candidates
    candidates, stats = filter_candidates(store.restaurants, prefs)
    print(f"Filter stats: {stats}")
    print(f"Found {len(candidates)} matching candidate restaurants in {prefs.location}.")
    
    if not candidates:
        print("No candidates found matching the criteria!")
        return

    print("\nTop 5 candidates sorted by structured fields:")
    for idx, c in enumerate(candidates[:5]):
        print(f"  {idx+1}. {c.name} | Rating: {c.rating} | Cost: Rs. {c.cost_for_two} | Cuisines: {c.cuisines}")

    
    # 5. Execute Phase 4
    llm_client = LLMClient()
    
    if not llm_client.ping():
        print("\n[WARNING] GEMINI_API_KEY is not configured in your .env file!")
        print("Showing structured Fallback Ranker output instead.")
        fallback_res = generate_fallback_recommendations(candidates, prefs, "API key not configured.")
        formatted = format_recommendation_response(fallback_res)
        print("\nFallback Results (top 5 by rating):")
        print(json.dumps(formatted, indent=2))
        return
        
    print(f"\nGEMINI_API_KEY is configured. Sending prompt to Gemini ({os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')})...")
    try:
        prompt = build_prompt_payload(candidates, prefs)
        response_text = llm_client.generate_recommendations(prompt)
        result = parse_llm_response(response_text, candidates, prefs)
        formatted = format_recommendation_response(result)
        print("\nSuccess! Gemini Recommendations:")
        print(json.dumps(formatted, indent=2))
    except Exception as e:
        print(f"\nAPI Call failed: {e}")
        print("Reverting to Fallback Ranker...")
        fallback_res = generate_fallback_recommendations(candidates, prefs, str(e))
        formatted = format_recommendation_response(fallback_res)
        print(json.dumps(formatted, indent=2))

if __name__ == "__main__":
    main()
