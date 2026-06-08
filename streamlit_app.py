"""Zomato AI - Premium Restaurant Recommendation Landing Page using Streamlit."""

from __future__ import annotations

import base64
import logging
import html
import os
import streamlit as st

def escapeHTML(text):
    if text is None:
        return ""
    return html.escape(str(text))

# Setup Logging
logger = logging.getLogger("zomato_streamlit")
logging.basicConfig(level=logging.INFO)

from phase1.ingestion import RestaurantStore
from phase2.preferences import validate_and_normalize_preferences
from phase3.filter import filter_candidates
from phase3.prompt_builder import build_prompt_payload
from phase4.llm_client import LLMClient, LLMAPIError, LLMConfigurationError
from phase4.parser import parse_llm_response, generate_fallback_recommendations
from phase5.formatter import format_recommendation_response

# 1. Resource Caching: Load Restaurant Database once on startup
@st.cache_resource
def load_store():
    logger.info("Initializing restaurant database for Streamlit...")
    try:
        store = RestaurantStore.load()
        logger.info("Database loaded successfully with %d records.", len(store))
        return store
    except Exception as exc:
        logger.error("Failed to load restaurant store: %s", exc)
        st.error("Fatal: Could not load restaurant dataset.")
        return None

store = load_store()
cities = store.get_cities() if store else []

# High-quality food imagery mapping
CUISINE_IMAGES = {
    "north indian": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=400&q=80",
    "south indian": "https://images.unsplash.com/photo-1668236543090-82eba5ee5976?auto=format&fit=crop&w=400&q=80",
    "biryani": "https://images.unsplash.com/photo-1633945274405-b6c8069047b0?auto=format&fit=crop&w=400&q=80",
    "mughlai": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=400&q=80",
    "fast food": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=400&q=80",
    "burgers": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=400&q=80",
    "burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=400&q=80",
    "pizza": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=400&q=80",
    "street food": "https://images.unsplash.com/photo-1626132647523-66f5bf380027?auto=format&fit=crop&w=400&q=80",
    "italian": "https://images.unsplash.com/photo-1533777857889-4be7c70b33f7?auto=format&fit=crop&w=400&q=80",
    "pasta": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=400&q=80",
    "continental": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=400&q=80",
    "chinese": "https://images.unsplash.com/photo-1585032226651-759b368d7246?auto=format&fit=crop&w=400&q=80",
    "asian": "https://images.unsplash.com/photo-1585032226651-759b368d7246?auto=format&fit=crop&w=400&q=80",
    "cafe": "https://images.unsplash.com/photo-1445116572660-236099ec97a0?auto=format&fit=crop&w=400&q=80",
    "beverages": "https://images.unsplash.com/photo-1497515114629-f71d768fd07c?auto=format&fit=crop&w=400&q=80",
    "desserts": "https://images.unsplash.com/photo-1551024601-bec78aea704b?auto=format&fit=crop&w=400&q=80",
    "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80",
    "salads": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=400&q=80",
    "salad": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=400&q=80"
};

def get_cuisine_image(cuisines):
    if not cuisines:
        return "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=400&q=80"
    for c in cuisines:
        norm = c.lower().strip()
        if norm in CUISINE_IMAGES:
            return CUISINE_IMAGES[norm]
    return "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=400&q=80"

# Convert local photo collage banner to Base64 for inline background styling
def get_banner_style():
    banner_path = "phase7/static/images/food_collage_banner.png"
    if os.path.exists(banner_path):
        try:
            with open(banner_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode()
            return f"background-image: url('data:image/png;base64,{encoded}');"
        except Exception:
            pass
    return "background-image: url('https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=1200&q=80');"

banner_inline_style = get_banner_style()

# 2. Session State Initialization
if "craving" not in st.session_state:
    st.session_state.craving = ""
if "location" not in st.session_state:
    st.session_state.location = ""
if "cuisine" not in st.session_state:
    st.session_state.cuisine = ""
if "budget" not in st.session_state:
    st.session_state.budget = "medium"
if "min_rating" not in st.session_state:
    st.session_state.min_rating = 0.0
if "additional_tags" not in st.session_state:
    st.session_state.additional_tags = []
if "custom_tags" not in st.session_state:
    st.session_state.custom_tags = []
if "show_add_more" not in st.session_state:
    st.session_state.show_add_more = False
if "submitted" not in st.session_state:
    st.session_state.submitted = False

# 3. Streamlit Page Setup
st.set_page_config(
    page_title="Zomato AI - Find Your Perfect Meal",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 4. Premium Theme CSS Injections
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet">
<style>
    /* Reset & Overrides */
    .stApp {
        background-color: #ffffff;
    }
    
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    footer {
        display: none !important;
    }
    
    /* Navigation Bar */
    .top-navbar {
        background-color: #ffffff;
        border-bottom: 1px solid #e8e8e8;
        position: sticky;
        top: 0;
        z-index: 100;
        height: 72px;
        display: flex;
        align-items: center;
        width: 100%;
        margin-bottom: 0px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
    }
    
    .nav-container {
        width: 100%;
        max-width: 1240px;
        margin: 0 auto;
        padding: 0 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .brand {
        display: flex;
        align-items: center;
        gap: 4px;
        text-decoration: none;
    }
    
    .brand-zomato {
        font-family: 'Outfit', sans-serif;
        font-size: 28px;
        font-weight: 800;
        color: #E23744;
        letter-spacing: -0.04em;
        font-style: italic;
    }
    
    .brand-ai {
        background-color: #E23744;
        color: #ffffff;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 6px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-left: 2px;
        line-height: 1.2;
    }
    
    .nav-links {
        display: flex;
        gap: 32px;
        align-items: center;
    }
    
    .nav-link {
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        font-weight: 500;
        color: #696969;
        cursor: pointer;
        padding: 6px 0;
        position: relative;
    }
    
    .nav-link.active {
        color: #E23744;
        font-weight: 600;
    }
    
    .nav-link.active::after {
        content: "";
        position: absolute;
        bottom: -6px;
        left: 0;
        width: 100%;
        height: 3px;
        background-color: #E23744;
        border-radius: 9999px;
    }

    /* Hero Section */
    .hero-banner {
        width: 100%;
        position: relative;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        padding: 80px 24px 90px;
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        border-radius: 0 0 24px 24px;
        margin-bottom: -50px;
    }
    
    .hero-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(180deg, rgba(28, 28, 28, 0.45) 0%, rgba(28, 28, 28, 0.7) 100%);
        z-index: 1;
    }
    
    .hero-content-wrapper {
        position: relative;
        z-index: 2;
        max-width: 800px;
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 40px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        margin-bottom: 8px;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .hero-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 17px;
        color: rgba(255, 255, 255, 0.9);
        margin-bottom: 0px;
        text-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }

    /* Card Details Container (2-Column Recommendations Layout) */
    .cards-grid-2col {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 24px;
        margin-top: 24px;
        width: 100%;
    }
    
    @media (max-width: 1024px) {
        .cards-grid-2col {
            grid-template-columns: 1fr;
        }
    }
       /* Recommendation Card Design (Simplified) */
    .restaurant-card {
        background-color: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 20px;
        overflow: hidden;
        position: relative;
        box-shadow: 0 10px 30px rgba(28, 28, 28, 0.04), 0 1px 3px rgba(28, 28, 28, 0.01);
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    
    .restaurant-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 35px rgba(226, 55, 68, 0.06), 0 2px 8px rgba(226, 55, 68, 0.01);
        border-color: #ffd1d3;
    }
    
    .favorite-btn {
        position: absolute;
        top: 18px;
        right: 18px;
        z-index: 10;
        background-color: #f8f8f8;
        border: none;
        color: #696969;
        border-radius: 50%;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        transition: background-color 0.2s, color 0.2s, transform 0.2s;
    }
    
    .favorite-btn:hover {
        transform: scale(1.08);
        background-color: #ffffff;
        color: #E23744;
    }
    
    .favorite-btn.active {
        color: #E23744;
    }
    
    .favorite-btn .material-symbols-outlined {
        font-size: 18px;
        font-variation-settings: 'FILL' 0;
    }
    
    .favorite-btn.active .material-symbols-outlined {
        font-variation-settings: 'FILL' 1;
    }
    
    .card-details-container {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 20px 24px;
        gap: 12px;
        min-width: 0;
    }
    
    .card-info {
        width: 100%;
        display: flex;
        flex-direction: column;
        gap: 6px;
        min-width: 0;
    }
    
    .restaurant-name {
        font-family: 'Outfit', sans-serif;
        font-size: 17px;
        font-weight: 700;
        color: #1c1c1c;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .restaurant-cuisine-area {
        font-family: 'Inter', sans-serif;
        font-size: 13px;
        color: #696969;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .restaurant-meta {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12.5px;
        color: #696969;
    }
    
    .meta-dot {
        color: #9c9c9c;
    }
    
    .rating-badge {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
    }
    
    .rating-badge.rating-high {
        background-color: #248245;
        color: #ffffff;
    }
    
    .rating-badge.rating-medium {
        background-color: rgba(180, 83, 9, 0.08);
        color: #b45309;
    }
    
    .rating-badge.rating-new {
        background-color: #f8f8f8;
        color: #696969;
    }
    
    .card-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 4px;
    }
    
    .cuisine-tag {
        font-size: 11px;
        font-weight: 500;
        padding: 2px 6px;
        border-radius: 6px;
        background-color: #f8f8f8;
        color: #696969;
        border: 1px solid #e8e8e8;
    }
    
    /* AI Explanation Bubble */
    .ai-reason-box {
        flex: 0.9;
        background-color: #fff5f5;
        border-radius: 12px;
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        border: 1px solid rgba(226, 55, 68, 0.05);
        min-width: 0;
    }
    
    .ai-reason-header {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 700;
        color: #E23744;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .ai-reason-text {
        font-size: 11.5px;
        line-height: 1.35;
        color: #4a3334;
    }
    
    /* Insights Card */
    .summary-card {
        border-radius: 20px;
        background: linear-gradient(135deg, #ffffff 40%, #fff5f5 100%);
        border: 1px solid #ffd1d3;
        padding: 20px 24px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 10px 30px rgba(28, 28, 28, 0.04);
        margin-bottom: 24px;
        width: 100%;
    }
    
    .summary-icon-box {
        flex-shrink: 0;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background-color: #fff5f5;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #ffd1d3;
    }
    
    .summary-icon {
        font-size: 22px;
        color: #E23744;
    }
    
    .summary-text-container {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    
    .summary-tag {
        font-size: 11px;
        font-weight: 700;
        color: #E23744;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .summary-text {
        font-size: 14.5px;
        font-weight: 500;
        line-height: 1.4;
        color: #1c1c1c;
    }

    /* Subtitle Results Heading style */
    .results-heading-box {
        margin-top: 32px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 1px solid #e8e8e8;
        padding-bottom: 16px;
    }
    
    .results-title {
        font-family: 'Outfit', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #1c1c1c;
        margin: 0;
    }
    
    .results-subtitle {
        font-size: 14px;
        color: #696969;
        margin-top: 4px;
    }
    
    /* Footer Styling */
    .app-footer {
        background-color: #f8f8f8;
        border-top: 1px solid #e8e8e8;
        padding: 40px 24px;
        margin-top: 64px;
        width: 100%;
    }
    
    .footer-container {
        max-width: 1240px;
        margin: 0 auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .copyright-text {
        font-size: 12.5px;
        color: #9c9c9c;
    }
</style>
""", unsafe_allow_html=True)

# 5. Header Navbar
st.markdown("""
<nav class="top-navbar">
    <div class="nav-container">
        <div class="brand">
            <span class="brand-zomato">zomato</span>
            <span class="brand-ai">AI</span>
        </div>
        <div class="nav-links">
            <span class="nav-link active">Home</span>
            <span class="nav-link">Favorites</span>
        </div>
        <div style="width: 80px;"></div>
    </div>
</nav>
""", unsafe_allow_html=True)

# 6. Hero Banner
st.markdown(f"""
<section class="hero-banner" style="{banner_inline_style}">
    <div class="hero-overlay"></div>
    <div class="hero-content-wrapper">
        <h1 class="hero-title">Find Your Perfect Meal with Zomato AI ✨</h1>
        <p class="hero-subtitle">Your AI food companion that knows your taste</p>
    </div>
</section>
""", unsafe_allow_html=True)

# 7. Conversational Search input bar & Send button
st.write("")
col_search, col_send = st.columns([6, 1])
with col_search:
    craving_input = st.text_input(
        "Craving Search",
        value=st.session_state.craving,
        placeholder="Hi! What are you craving today?",
        label_visibility="collapsed",
        key="craving_search_input"
    )
with col_send:
    search_triggered = st.button("Send", use_container_width=True, type="primary")

# Synchronize search trigger or Enter key
if search_triggered:
    st.session_state.craving = craving_input
    # Set default location if empty
    if not st.session_state.location and len(cities) > 0:
        st.session_state.location = cities[0]
    st.session_state.submitted = True

# 8. Quick Preference Chips
st.markdown("<p style='text-align: center; color: #9c9c9c; font-size: 13.5px; margin-top: 10px;'>Quick ideas:</p>", unsafe_allow_html=True)
col_chips = st.columns(6)
chips_list = [
    ("🍝 Italian", "Italian", "cuisine"),
    ("🌶️ Spicy", "Spicy", "context"),
    ("🍰 Dessert", "Desserts", "cuisine"),
    ("📍 Near Me", "near_me", "geo"),
    ("🌃 Rooftop Dining", "Rooftop Dining", "context"),
    ("👥 Family Friendly", "Family Friendly", "context")
]

for idx, (label, val, typ) in enumerate(chips_list):
    with col_chips[idx]:
        if st.button(label, key=f"quick_chip_{idx}", use_container_width=True):
            st.session_state.craving = label.split(" ", 1)[-1]
            if typ == "cuisine":
                st.session_state.cuisine = val
            elif typ == "context":
                if val not in st.session_state.additional_tags:
                    st.session_state.additional_tags.append(val)
            elif typ == "geo" and len(cities) > 0:
                # Select a random canonical neighborhood to mock GPS detection
                import random
                st.session_state.location = random.choice(cities)
            st.session_state.submitted = True
            st.rerun()

st.write("")
st.write("")

# 9. Preferences Form (Card Container)
st.markdown("### Tell us your preferences <span style='font-size:14px; font-weight:400; color:#9c9c9c;'>(Optional)</span> <span style='color:#E23744;'>✨</span>", unsafe_allow_html=True)

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_location = st.selectbox(
            "Location",
            options=cities,
            index=cities.index(st.session_state.location) if st.session_state.location in cities else 0,
            placeholder="e.g. Mumbai"
        )
        st.session_state.location = selected_location
        
    with col2:
        selected_cuisine = st.text_input(
            "Cuisine",
            value=st.session_state.cuisine,
            placeholder="e.g. North Indian"
        )
        st.session_state.cuisine = selected_cuisine
        
    with col3:
        budget_options = ["₹", "₹₹", "₹₹₹", "₹₹₹₹"]
        curr_b_idx = 1
        if st.session_state.budget == "low":
            curr_b_idx = 0
        elif st.session_state.budget == "high":
            curr_b_idx = 2
            
        selected_budget_pill = st.radio(
            "Budget for two",
            options=budget_options,
            index=curr_b_idx,
            horizontal=True
        )
        # Map pill representation to backend low/medium/high
        if selected_budget_pill == "₹":
            st.session_state.budget = "low"
        elif selected_budget_pill == "₹₹":
            st.session_state.budget = "medium"
        else:
            st.session_state.budget = "high"
            
    with col4:
        rating_choices = [
            ("Any Rating", 0.0),
            ("3.0+ ★", 3.0),
            ("3.5+ ★", 3.5),
            ("4.0+ ★", 4.0),
            ("4.5+ ★", 4.5)
        ]
        curr_r_idx = 0
        for i, (l, v) in enumerate(rating_choices):
            if v == st.session_state.min_rating:
                curr_r_idx = i
                break
                
        selected_rating_label = st.selectbox(
            "Minimum Rating",
            options=[l for l, v in rating_choices],
            index=curr_r_idx
        )
        st.session_state.min_rating = next(v for l, v in rating_choices if l == selected_rating_label)

    # 10. Additional Toggle Chips
    st.write("")
    st.markdown("**Additional Preferences**")
    default_tags = ["outdoor seating", "pet friendly", "live music", "rooftop"]
    
    # Merge custom user tags
    all_tags = default_tags + st.session_state.custom_tags
    
    col_toggles = st.columns(len(all_tags) + 1)
    new_toggled_tags = []
    
    for i, tag in enumerate(all_tags):
        with col_toggles[i]:
            title_case = tag.title()
            is_checked = tag in st.session_state.additional_tags
            if st.checkbox(title_case, value=is_checked, key=f"form_chip_{i}"):
                new_toggled_tags.append(tag)
                
    st.session_state.additional_tags = new_toggled_tags

    with col_toggles[-1]:
        if st.button("➕ Add more", key="add_more_toggle"):
            st.session_state.show_add_more = not st.session_state.show_add_more

    # Custom Add More text field input inside card
    if st.session_state.show_add_more:
        st.write("")
        col_add_inp, col_add_btn = st.columns([4, 1])
        with col_add_inp:
            new_custom_tag = st.text_input(
                "Enter custom preference tag:",
                placeholder="e.g. valet parking, microbrewery",
                label_visibility="collapsed",
                key="custom_tag_input_box"
            )
        with col_add_btn:
            if st.button("Add Tag", use_container_width=True):
                norm_tag = new_custom_tag.strip().lower()
                if norm_tag and norm_tag not in st.session_state.custom_tags:
                    st.session_state.custom_tags.append(norm_tag)
                    st.session_state.additional_tags.append(norm_tag)
                    st.session_state.show_add_more = False
                    st.rerun()

    # Form Submission Trigger Button
    st.write("")
    col_empty, col_submit = st.columns([3, 1])
    with col_submit:
        form_submit_clicked = st.button("✨ Get Recommendations", type="primary", use_container_width=True)

if form_submit_clicked:
    st.session_state.submitted = True

# 11. Recommendations Pipeline execution
if st.session_state.submitted:
    # Build complete additional context string
    context_parts = []
    if craving_input.strip() and craving_input.strip() != st.session_state.craving:
        context_parts.append(craving_input.strip())
    elif st.session_state.craving:
        context_parts.append(st.session_state.craving)
        
    for tag in st.session_state.additional_tags:
        context_parts.append(tag)
        
    final_context = ", ".join(context_parts)

    st.markdown(f"""
    <div class="results-heading-box">
        <div>
            <h2 class="results-title">AI Recommendations for You ✨</h2>
            <p class="results-subtitle">Curated just for your taste and mood</p>
        </div>
        <div style="font-family:'Inter', sans-serif; font-size:14px; font-weight:600; color:#E23744;">
            View all &nbsp;<span class="material-symbols-outlined" style="font-size:16px; vertical-align:middle;">chevron_right</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.location:
        st.warning("Please choose a location to receive recommendations.")
    else:
        with st.spinner("Consulting Zomato AI pipeline..."):
            # Execute Pipeline directly
            try:
                # Normalization
                payload = {
                    "location": st.session_state.location,
                    "budget": st.session_state.budget,
                    "cuisine": st.session_state.cuisine or None,
                    "min_rating": st.session_state.min_rating,
                    "additional_context": final_context
                }
                
                prefs = validate_and_normalize_preferences(payload, cities)
                
                # Filter candidates
                candidates, filter_stats = filter_candidates(store.restaurants, prefs)
                
                if not candidates:
                    # Suggestions for over-constrained errors
                    st.markdown(f"""
                    <div class="summary-card" style="border-color:#ba1a1a; background-color:#fff5f5;">
                        <div class="summary-icon-box" style="border-color:#ba1a1a;">
                            <span class="material-symbols-outlined" style="color:#ba1a1a;">error</span>
                        </div>
                        <div class="summary-text-container">
                            <span class="summary-tag" style="color:#ba1a1a;">No Matches Found</span>
                            <p class="summary-text" style="color:#1c1c1c;">Your criteria might be too specific. Try relaxing filters!</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if filter_stats.get("suggestions"):
                        st.info("Try relaxing your filters:")
                        for suggestion in filter_stats["suggestions"]:
                            st.write(f"- {suggestion}")
                else:
                    # Recommendation logic
                    llm_client = LLMClient()
                    if not llm_client.ping():
                        # LLM Offline Fallback
                        logger.warning("LLM client offline. Triggering fallback ranker.")
                        result = generate_fallback_recommendations(
                            candidates,
                            prefs,
                            "AI is currently unavailable because API keys are missing on the server."
                        )
                    else:
                        try:
                            prompt = build_prompt_payload(candidates, prefs)
                            response_text = llm_client.generate_recommendations(prompt)
                            result = parse_llm_response(response_text, candidates, prefs)
                        except Exception as exc:
                            logger.error("LLM pipeline failed: %s. Initiating fallback.", exc)
                            result = generate_fallback_recommendations(
                                candidates,
                                prefs,
                                f"AI encountered an issue: {str(exc)}"
                            )

                    # Formatted recommendations response
                    formatted_data = format_recommendation_response(result)
                    recs = formatted_data.get("recommendations", [])
                    summary = formatted_data.get("summary", "")
                    is_fallback = formatted_data.get("fallback", False)

                    # Trade-off insights summary card
                    badge_title = "Structured Fallback (AI Offline)" if is_fallback else "AI Insights"
                    st.markdown(f"""
                    <div class="summary-card">
                        <div class="summary-icon-box">
                            <span class="material-symbols-outlined summary-icon">lightbulb</span>
                        </div>
                        <div class="summary-text-container">
                            <span class="summary-tag">{badge_title}</span>
                            <p class="summary-text">{summary}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # 2-Column Restaurant Grid Card Layout (HTML/CSS Injections)
                    cards_html = '<div class="cards-grid-2col">'
                    for rec in recs:
                        rank = rec.get("rank", 1)
                        name = rec.get("name", "")
                        rating_text = rec.get("rating_text", "NEW")
                        rating_class = rec.get("rating_class", "rating-new")
                        cost_text = rec.get("cost_text", "Approx cost unknown")
                        explanation = rec.get("explanation", "")
                        rec_cuisines = rec.get("cuisines", [])
                        
                        cuisine_img = get_cuisine_image(rec_cuisines)
                        area_text = f"{rec_cuisines[0]} • {rec.get('area', '')}" if rec.get('area') else rec_cuisines[0]
                        mock_distance = f"{rank * 230 + 350} m"
                        
                        all_tags = list(rec_cuisines)
                        if rec.get("attributes"):
                            all_tags += list(rec.get("attributes", []))[:2]
                        
                        tags_html = "".join([f'<span class="cuisine-tag">{escapeHTML(t)}</span>' for t in all_tags])
                        
                        cards_html += f"""
                        <div class="restaurant-card">
                            <div class="card-details-container">
                                <button class="favorite-btn">
                                    <span class="material-symbols-outlined">favorite</span>
                                </button>
                                <div class="card-info">
                                    <h3 class="restaurant-name">{escapeHTML(name)}</h3>
                                    <div class="restaurant-cuisine-area">{escapeHTML(area_text)}</div>
                                    <div class="restaurant-meta">
                                        <span class="rating-badge {rating_class}">{escapeHTML(rating_text)}</span>
                                        <span class="meta-dot">•</span>
                                        <span class="distance-text">{mock_distance}</span>
                                        <span class="meta-dot">•</span>
                                        <span class="cost-text">{escapeHTML(cost_text)}</span>
                                    </div>
                                    <div class="card-tags">
                                        {tags_html}
                                    </div>
                                </div>
                                <div class="ai-reason-box">
                                    <div class="ai-reason-header">
                                        <span class="material-symbols-outlined sparkle-icon">sparkles</span>
                                        <span>Why AI picked this</span>
                                    </div>
                                    <p class="ai-reason-text">{escapeHTML(explanation)}</p>
                                </div>
                            </div>
                        </div>
                        """
                    cards_html += '</div>'
                    st.markdown(cards_html, unsafe_allow_html=True)
            except Exception as pipeline_err:
                logger.error("Pipeline failure: %s", pipeline_err, exc_info=True)
                st.error(f"Error executing recommendation query: {str(pipeline_err)}")

# 12. Footer
st.markdown("""
<footer class="app-footer">
    <div class="footer-container">
        <div>
            <div class="brand" style="margin-bottom:8px;">
                <span class="brand-zomato">zomato</span>
                <span class="brand-ai">AI</span>
            </div>
            <p class="copyright-text">&copy; 2026 Zomato AI Labs | All rights reserved.</p>
        </div>
        <div style="text-align: right; font-family:'Inter',sans-serif;">
            <p style="font-size:12.5px; font-weight:600; color:#696969; text-transform:uppercase; margin-bottom:8px;">Follow Us</p>
            <p style="font-size:12px; color:#9c9c9c;">Facebook • Instagram • Twitter • YouTube</p>
        </div>
    </div>
</footer>
""", unsafe_allow_html=True)
