# Google Stitch Prompt: Decoupled Next.js Frontend for Zesty Recommendations

Copy and paste the prompt below into Google Stitch (or any advanced AI UI/code generator) to generate a premium Next.js frontend and mock layout images matching the system architecture.

---

```text
You are an expert Frontend Engineer and UI/UX Designer. Generate a premium, production-ready Next.js single-page dashboard application using React, TailwindCSS, TypeScript, and Lucide React icons. 

The application is the user interface for "Zesty Recommendations" — an AI-Powered Restaurant Recommendation System. It must connect asynchronously to our Python Flask backend API.

### 1. Visual Aesthetics & Design System
- Theme: Deep, luxurious dark mode.
  - Background: Gradient from dark slate/indigo (e.g., #0b0f19) to deep charcoal (e.g., #111827).
  - Cards & Panels: Semi-transparent glassmorphism (bg-white/5 or bg-gray-900/40 backdrop-blur-md) with subtle borders (border-white/10).
  - Primary Accent: Neon Emerald / Mint Green (e.g., #10b981) for buttons, positive ratings, and indicators.
  - Secondary Accent: Golden Amber (e.g., #f59e0b) for star ratings and highlight badges.
- Typography: Premium sans-serif font (e.g., Outfit, Inter, or Space Grotesk) with clean hierarchy.
- Micro-interactions: Smooth hover translations (scale-102, shadow-lg), hover glow effects, transition durations (duration-300), and slide-up card entries.

### 2. UI Layout & Component Specifications
Design a split-screen or two-column dashboard layout (responsive, collapsing to single-column on mobile):

#### A. Left Column: Preference Input Form Panel
- **Title**: "Configure Your Tastes" with a brief, modern subtitle.
- **Location Field (Required)**: 
  - A clean search-select dropdown.
  - On page load, fetch options from `GET /api/locations` and populate. Include a loading skeleton while fetching locations.
- **Budget Tier Field**: 
  - An interactive segment control or radio buttons containing three options: "Low (≤ Rs. 500)", "Medium (Rs. 501 - 1000)", and "High (> Rs. 1000)".
  - A custom numeric input text field below: "Or enter budget directly (e.g. 1500, Rs. 2000)".
- **Cuisines Field**:
  - Multi-select search tag input (e.g. "Burgers", "Italian", "North Indian").
- **Minimum Rating Field**:
  - Interactive star rating component (0 to 5 stars) or a modern horizontal slider showing rating value.
- **Additional Context (Free-Text)**:
  - Text area placeholder: "e.g., rooftop seating, family-friendly, microbrewery, quick service...". Limit character count to 500.
- **Submit Button**:
  - Emerald green button labeled "Generate AI Recommendations".
  - Includes a glowing hover state and shows a spinner icon when loading.

#### B. Right Column: Recommendation Results & Suggestions Panel
- **Initial Empty State**:
  - Display a beautiful vector illustration or mockup card: "Your culinary recommendations will appear here. Select a neighborhood to begin."
- **Loading State**:
  - When fetching results, show 3 skeleton restaurant cards (simulating rank badges, loading text blocks, rating stars, and tag rows using pulse animations).
- **Success State (Recommendations List)**:
  - **AI Trade-off Summary Card**: A prominent card at the top with an "AI Insights" badge, displaying the summary text returned by the API.
  - **Recommendation Cards (Top 5 List)**:
    - Render cards sequentially with a staggered slide-up animation.
    - Card header: Display restaurant Name, location area, and a badge with the rank (e.g., "Rank #1", "Rank #2").
    - Card body:
      - Cuisines list rendered as elegant colored pill tags.
      - Rating badge: "★ 4.9" styled with the CSS rating classes (`rating-high`, `rating-medium`, `rating-new`) returned from the server API.
      - Estimated Cost for two people.
      - Key attributes (e.g., "microbrewery", "outdoor seating") shown as micro-badges.
      - AI explanation: A 2-3 sentence personalized justification block with a subtle background tint (e.g., bg-emerald-500/10).
- **Error / Over-Constrained State**:
  - If the backend returns a 400 Bad Request with suggestions (over-constrained criteria), display a warning alert box: "No matches found in this neighborhood."
  - Under the alert, render the suggestions list as **interactive, clickable chips/pills**.
  - Clicking a chip should automatically relax/change that filter state in the form (e.g., clicking "Lower your minimum rating filter to 4.5" adjusts the rating input to 4.5) and automatically re-submit the recommendation query.

### 3. API Integration Contract
Implement integration using the Next.js Fetch API to these relative backend paths:

- **Get Neighborhood Locations**:
  `GET /api/locations` ➔ returns string array `["Bellandur", "Btm", ...]`
- **Fetch Recommendations**:
  `POST /api/recommend` with JSON payload:
  ```json
  {
    "location": "Bellandur",
    "budget": "2000",
    "min_rating": 4.0,
    "additional_context": "outdoor seating"
  }
  ```
  - Handle 200 Success responses.
  - Handle 400 Validation/Over-constrained error responses.
  - Handle 500 Server Exception fallbacks cleanly.
```
