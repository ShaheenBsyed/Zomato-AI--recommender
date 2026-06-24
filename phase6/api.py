"""Phase 6: Backend API Development — Flask API Router and Pipeline Orchestrator."""

from __future__ import annotations

import os
import logging
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Logging
logger = logging.getLogger("zesty")

from phase1.ingestion import RestaurantStore
from phase2.preferences import validate_and_normalize_preferences
from phase3.filter import filter_candidates
from phase3.prompt_builder import build_prompt_payload
from phase4.llm_client import LLMClient, LLMAPIError, LLMConfigurationError
from phase4.parser import parse_llm_response, generate_fallback_recommendations
from phase5.formatter import format_recommendation_response

# Decoupled Flask app initialization with parent directory assets reference
app = Flask(
    __name__,
    static_folder="../phase7/static",
    template_folder="../phase7/templates"
)
CORS(app)  # Enable Cross-Origin Resource Sharing


# Load Restaurant Database once on startup
logger.info("Initializing restaurant database...")
try:
    store = RestaurantStore.load()
    logger.info("Database initialized successfully with %d records.", len(store))
except Exception as exc:
    logger.error("Failed to initialize restaurant database: %s", exc)
    raise SystemExit("Fatal: Could not load restaurant store.") from exc

# Initialize LLM Client
llm_client = LLMClient()


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/locations", methods=["GET"])
def get_locations():
    """Return list of valid canonical locations/neighborhoods."""
    try:
        cities = store.get_cities()
        return jsonify(cities)
    except Exception as exc:
        logger.error("Error retrieving locations: %s", exc)
        return jsonify({"error": "Failed to load locations"}), 500


@app.route("/api/recommend", methods=["POST"])
def get_recommendations():
    """Process user preferences and return AI or fallback recommendations."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Missing JSON request body."}), 400

        # Phase 2: Validate and normalize user input
        try:
            prefs = validate_and_normalize_preferences(data, store.get_cities())
        except ValueError as val_err:
            logger.warning("Input validation failed: %s", val_err)
            return jsonify({"error": str(val_err)}), 400

        logger.info(
            "Received recommendation request for location='%s', budget='%s', cuisine='%s', min_rating=%s",
            prefs.location,
            prefs.budget.value,
            prefs.cuisine,
            prefs.min_rating
        )

        # Phase 3: Candidate Filtering
        candidates, filter_stats = filter_candidates(store.restaurants, prefs)
        
        # Handle 0 candidates (over-constrained filters)
        if not candidates:
            logger.info("Zero candidates matched preferences. Suggestions: %s", filter_stats["suggestions"])
            return jsonify({
                "error": "No restaurants matched your filters in this neighborhood.",
                "suggestions": filter_stats["suggestions"]
            }), 400

        # Phase 4 & 5: AI Recommendations or Fallback Ranker
        if not llm_client.ping():
            # No API key configured, degrade to Fallback Ranker directly
            logger.warning("LLM client not configured (missing API key). Using Fallback Ranker.")
            result = generate_fallback_recommendations(
                candidates, 
                prefs, 
                "AI is unavailable because no API keys are configured on the server."
            )
            return jsonify(format_recommendation_response(result))

        # Build prompt, call LLM, and parse response
        try:
            prompt = build_prompt_payload(candidates, prefs)
            response_text = llm_client.generate_recommendations(prompt)
            result = parse_llm_response(response_text, candidates, prefs)
            return jsonify(format_recommendation_response(result))
            
        except (LLMAPIError, LLMConfigurationError, Exception) as exc:
            # Catch API failures, quota errors, parse failures, etc. and fall back safely
            logger.error("LLM pipeline failed: %s. Initiating fallback ranking.", exc, exc_info=True)
            result = generate_fallback_recommendations(
                candidates, 
                prefs, 
                f"The AI recommendation service encountered an issue: {str(exc)}"
            )
            return jsonify(format_recommendation_response(result))

    except Exception as exc:
        logger.error("Unexpected server error: %s", exc, exc_info=True)
        return jsonify({"error": "An unexpected server error occurred. Please try again."}), 500
