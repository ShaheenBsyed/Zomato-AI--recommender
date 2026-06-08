"""Configuration constants for data ingestion."""

from pathlib import Path

# Hugging Face dataset — revision pinned for reproducibility
DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"
DATASET_REVISION = "5738e9eda2fad49ad51c6e0ed26e761d9b947133"

REQUIRED_RAW_COLUMNS = (
    "name",
    "location",
    "listed_in(city)",
    "cuisines",
    "approx_cost(for two people)",
    "rate",
    "votes",
)

OPTIONAL_RAW_COLUMNS = (
    "online_order",
    "book_table",
    "rest_type",
    "listed_in(type)",
    "address",
)

# Budget tiers based on approximate cost for two (INR)
BUDGET_LOW_MAX = 500
BUDGET_MEDIUM_MAX = 1000

# Canonical city aliases (lowercase key -> canonical display name)
LOCATION_ALIASES: dict[str, str] = {
    "bengaluru": "Bangalore",
    "bangalore": "Bangalore",
    "bengaluru city": "Bangalore",
    "new delhi": "New Delhi",
    "delhi": "New Delhi",
    "ncr": "New Delhi",
    "gurugram": "Gurgaon",
    "gurgaon": "Gurgaon",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "chennai": "Chennai",
    "madras": "Chennai",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "ahmedabad": "Ahmedabad",
    "jaipur": "Jaipur",
    "lucknow": "Lucknow",
    "chandigarh": "Chandigarh",
    "goa": "Goa",
    "kochi": "Kochi",
    "cochin": "Kochi",
}

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CACHE_FILE = CACHE_DIR / "restaurants.json"
CACHE_META_FILE = CACHE_DIR / "restaurants.meta.json"

MAX_DOWNLOAD_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2
