/**
 * Zomato AI Frontend Orchestrator
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const form = document.getElementById("preferences-form");
    const locationSelect = document.getElementById("location-select");
    const contextTextarea = document.getElementById("context-textarea");
    const charCounter = document.getElementById("char-counter");
    const submitBtn = document.getElementById("submit-btn");
    const submitBtnText = submitBtn.querySelector(".btn-text");
    const submitBtnSpinner = submitBtn.querySelector(".spinner");

    const placeholderBox = document.getElementById("results-placeholder");
    const loadingBox = document.getElementById("results-loading");
    const errorBox = document.getElementById("results-error");
    const errorMessage = document.getElementById("error-message");
    const resultsContent = document.getElementById("results-content");
    const summaryText = document.getElementById("summary-text");
    const cardsContainer = document.getElementById("cards-container");

    const aiBadge = document.getElementById("ai-badge");
    const fallbackBadge = document.getElementById("fallback-badge");

    const suggestionsContainer = document.getElementById("relaxation-suggestions-container");
    const suggestionsList = document.getElementById("relaxation-suggestions-list");

    // Conversational Search elements
    const searchInput = document.getElementById("conversational-search-input");
    const searchSendBtn = document.getElementById("conversational-search-send");
    const quickChips = document.querySelectorAll(".quick-chip");

    // Geolocation elements
    const geoBtn = document.getElementById("geo-location-btn");

    // Preference tags elements
    const prefChips = document.querySelectorAll(".pref-chip-btn:not(.add-more-btn)");
    const addMoreBtn = document.getElementById("add-more-chip-btn");
    
    // Custom Tag Modal elements
    const customTagModal = document.getElementById("custom-tag-modal");
    const customTagInput = document.getElementById("custom-tag-input");
    const modalCancelBtn = document.getElementById("modal-cancel-btn");
    const modalAddBtn = document.getElementById("modal-add-btn");

    // Locations storage for geolocation lookup
    let loadedLocations = [];

    // High-quality food imagery mapping
    const CUISINE_IMAGES = {
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

    function getCuisineImage(cuisines) {
        if (!cuisines || cuisines.length === 0) {
            return "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=400&q=80";
        }
        for (let c of cuisines) {
            const norm = c.toLowerCase().trim();
            if (CUISINE_IMAGES[norm]) {
                return CUISINE_IMAGES[norm];
            }
        }
        return "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=400&q=80";
    }

    // Helper: Escape HTML to prevent XSS
    function escapeHTML(str) {
        if (!str) return "";
        return str
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initialize Page
    loadLocations();
    setupCharCounter();
    setupPreferenceToggles();
    setupConversationalSearch();
    setupCustomTagModal();
    setupGeolocation();

    // 1. Fetch available locations from backend
    async function loadLocations() {
        try {
            const response = await fetch("/api/locations");
            if (!response.ok) {
                throw new Error("Failed to load neighborhoods.");
            }
            const locations = await response.json();
            loadedLocations = locations;
            
            // Populate select dropdown
            locationSelect.innerHTML = '<option value="" disabled selected>e.g., Mumbai</option>';
            locations.forEach(loc => {
                const opt = document.createElement("option");
                opt.value = loc;
                opt.textContent = loc;
                locationSelect.appendChild(opt);
            });
            locationSelect.disabled = false;
        } catch (err) {
            console.error(err);
            locationSelect.innerHTML = '<option value="" disabled selected>Error loading neighborhoods</option>';
            showError("Could not retrieve neighborhood list from backend. Please refresh the page.");
        }
    }

    // 2. Setup character counter for context textarea (invisible but used by orchestrator)
    function setupCharCounter() {
        if (!contextTextarea || !charCounter) return;
        contextTextarea.addEventListener("input", () => {
            const len = contextTextarea.value.length;
            charCounter.textContent = `${len} / 500`;
        });
    }

    // 3. Preference chips interactive toggles
    function setupPreferenceToggles() {
        prefChips.forEach(chip => {
            chip.addEventListener("click", () => {
                chip.classList.toggle("active");
                syncContextTextarea();
            });
        });
    }

    // Synchronize selected chips and conversational search text into contextTextarea
    function syncContextTextarea() {
        let parts = [];
        
        // Gathers search bar craving text
        const searchVal = searchInput.value.trim();
        if (searchVal) {
            parts.push(searchVal);
        }

        // Gathers active preference chips
        const activeChips = document.querySelectorAll(".pref-chip-btn.active");
        activeChips.forEach(chip => {
            const val = chip.getAttribute("data-value");
            if (val) {
                parts.push(val);
            }
        });

        // Joins preferences into context string
        contextTextarea.value = parts.join(", ");
        
        // Trigger character counter check
        contextTextarea.dispatchEvent(new Event("input"));
    }

    // 4. Conversational search event listeners
    function setupConversationalSearch() {
        // Send button trigger
        searchSendBtn.addEventListener("click", () => {
            triggerConversationalSearch();
        });

        // Press Enter trigger
        searchInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                triggerConversationalSearch();
            }
        });

        // Quick preference chips
        quickChips.forEach(chip => {
            chip.addEventListener("click", () => {
                const cuisineVal = chip.getAttribute("data-cuisine");
                const contextVal = chip.getAttribute("data-context");

                // Populate form fields based on chip details
                if (cuisineVal) {
                    document.getElementById("cuisine-input").value = cuisineVal;
                }
                
                if (contextVal) {
                    // Activate corresponding chip in UI
                    const formChip = document.querySelector(`.pref-chip-btn[data-value="${contextVal.toLowerCase()}"]`);
                    if (formChip) {
                        formChip.classList.add("active");
                    } else {
                        // Create custom chip if not found
                        addCustomPreferenceChip(contextVal);
                    }
                }

                // If "Near Me" clicked, run geolocation
                if (chip.id === "near-me-chip") {
                    triggerGeolocation();
                    return;
                }

                // Set search input value
                searchInput.value = chip.getAttribute("data-value") || chip.textContent.trim().replace(/^[\s\S]*?\s/, "");
                
                syncContextTextarea();

                // Auto-submit search query
                form.dispatchEvent(new Event("submit"));
            });
        });
    }

    // Actions when conversational search fires
    function triggerConversationalSearch() {
        syncContextTextarea();
        
        // Auto-select a location if none is selected yet to prevent validation block
        if (!locationSelect.value && loadedLocations.length > 0) {
            // Pick first neighborhood as default or popular one
            locationSelect.value = loadedLocations[0];
        }

        form.dispatchEvent(new Event("submit"));
    }

    // 5. Custom Tag Dialog Modal setup
    function setupCustomTagModal() {
        addMoreBtn.addEventListener("click", () => {
            customTagModal.classList.remove("hidden");
            customTagInput.value = "";
            customTagInput.focus();
        });

        modalCancelBtn.addEventListener("click", () => {
            customTagModal.classList.add("hidden");
        });

        customTagModal.addEventListener("click", (e) => {
            if (e.target === customTagModal) {
                customTagModal.classList.add("hidden");
            }
        });

        modalAddBtn.addEventListener("click", () => {
            const val = customTagInput.value.trim();
            if (val) {
                addCustomPreferenceChip(val);
            }
            customTagModal.classList.add("hidden");
        });

        customTagInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                const val = customTagInput.value.trim();
                if (val) {
                    addCustomPreferenceChip(val);
                }
                customTagModal.classList.add("hidden");
            }
        });
    }

    // Dynamically insert custom preference chips
    function addCustomPreferenceChip(label) {
        const value = label.toLowerCase();
        
        // Verify if a chip with the same value already exists
        const existing = document.querySelector(`.pref-chip-btn[data-value="${value}"]`);
        if (existing) {
            existing.classList.add("active");
            syncContextTextarea();
            return;
        }

        // Build new button
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "pref-chip-btn active";
        btn.setAttribute("data-value", value);
        btn.textContent = label;
        
        // Listeners for toggle
        btn.addEventListener("click", () => {
            btn.classList.toggle("active");
            syncContextTextarea();
        });

        // Insert before the "+ Add more" button
        const container = document.getElementById("pref-chips-container");
        container.insertBefore(btn, addMoreBtn);

        syncContextTextarea();
    }

    // 6. Geolocation mock / handler
    function setupGeolocation() {
        if (!geoBtn) return;
        geoBtn.addEventListener("click", () => {
            triggerGeolocation();
        });
    }

    function triggerGeolocation() {
        if (navigator.geolocation) {
            // Change button color to show detecting state
            geoBtn.style.color = "var(--color-primary)";
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    // Mock mapping coordinate to a neighborhood from loaded locations
                    if (loadedLocations.length > 0) {
                        // Return a random neighborhood to simulate geolocation lookup
                        const randomLoc = loadedLocations[Math.floor(Math.random() * loadedLocations.length)];
                        locationSelect.value = randomLoc;
                        
                        // Notify user via console or search placeholder
                        searchInput.placeholder = `📍 Located near ${randomLoc}`;
                        
                        geoBtn.style.color = "var(--color-success)";
                        setTimeout(() => {
                            geoBtn.style.color = "";
                        }, 2000);

                        // Trigger auto-submit
                        form.dispatchEvent(new Event("submit"));
                    }
                },
                (error) => {
                    console.warn("Geolocation failed or denied. Falling back to first available neighborhood.");
                    fallbackGeolocation();
                }
            );
        } else {
            fallbackGeolocation();
        }
    }

    function fallbackGeolocation() {
        if (loadedLocations.length > 0) {
            const defaultLoc = loadedLocations[0];
            locationSelect.value = defaultLoc;
            searchInput.placeholder = `📍 Location set to ${defaultLoc}`;
            form.dispatchEvent(new Event("submit"));
        }
    }

    // 7. Handle preference form submission
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        // Sync inputs before send
        syncContextTextarea();

        // Retrieve values
        const location = locationSelect.value;
        const budgetRadio = document.querySelector('input[name="budget"]:checked');
        const budget = budgetRadio ? budgetRadio.value : "medium";
        const cuisine = document.getElementById("cuisine-input").value.trim();
        const minRating = parseFloat(document.getElementById("rating-select").value);
        const additionalContext = contextTextarea.value;

        // Validation
        if (!location) {
            showError("Please select a location neighborhood to proceed.");
            return;
        }

        // Set Loading State
        setLoading(true);

        try {
            const response = await fetch("/api/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    location,
                    budget,
                    cuisine: cuisine || null,
                    min_rating: minRating,
                    additional_context: additionalContext
                })
            });

            const result = await response.json();

            if (!response.ok) {
                // Check if backend returned detailed suggestions (e.g. over-constrained filters)
                if (result.suggestions && result.suggestions.length > 0) {
                    showOverConstrainedError(result.error || "No restaurants matched your filters.", result.suggestions);
                } else {
                    throw new Error(result.error || "An error occurred while generating recommendations.");
                }
                return;
            }

            // Render Results
            renderRecommendations(result);

        } catch (err) {
            console.error(err);
            showError(err.message || "Unable to reach the server. Please verify that the backend is running.");
        } finally {
            setLoading(false);
        }
    });

    // Toggle loading states
    function setLoading(isLoading) {
        if (isLoading) {
            submitBtn.disabled = true;
            submitBtnSpinner.classList.remove("hidden");
            submitBtnText.textContent = "Curating...";
            
            placeholderBox.classList.add("hidden");
            resultsContent.classList.add("hidden");
            errorBox.classList.add("hidden");
            loadingBox.classList.remove("hidden");
            
            aiBadge.classList.add("hidden");
            fallbackBadge.classList.add("hidden");
            suggestionsContainer.classList.add("hidden");
        } else {
            submitBtn.disabled = false;
            submitBtnSpinner.classList.add("hidden");
            submitBtnText.textContent = "✨ Get AI Recommendations";
            loadingBox.classList.add("hidden");
        }
    }

    // Display generic error message
    function showError(message) {
        errorMessage.textContent = message;
        errorBox.classList.remove("hidden");
        placeholderBox.classList.add("hidden");
        loadingBox.classList.add("hidden");
        resultsContent.classList.add("hidden");
        suggestionsContainer.classList.add("hidden");
    }

    // Display suggestion links for over-constrained filters
    function showOverConstrainedError(message, suggestions) {
        errorMessage.textContent = message;
        renderSuggestionChips(suggestions);

        suggestionsContainer.classList.remove("hidden");
        errorBox.classList.remove("hidden");
        placeholderBox.classList.add("hidden");
        loadingBox.classList.add("hidden");
        resultsContent.classList.add("hidden");
    }

    // Create interactive suggestion chip
    function createSuggestionChip(text, iconName, onClick) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip-hover";
        btn.innerHTML = `
            <div class="chip-content">
                <span class="material-symbols-outlined chip-icon">${iconName}</span>
                <span class="chip-text">${escapeHTML(text)}</span>
            </div>
            <span class="material-symbols-outlined chip-arrow">arrow_forward</span>
        `;
        btn.addEventListener("click", onClick);
        return btn;
    }

    // Parse suggestions array from server and render interactive chips
    function renderSuggestionChips(suggestions) {
        suggestionsList.innerHTML = "";
        if (!suggestions || suggestions.length === 0) return;

        suggestions.forEach(suggestion => {
            const text = suggestion.toLowerCase();
            
            // 1. Cuisine restriction
            if (text.includes("cuisine")) {
                const match = suggestion.match(/['"]([^'"]+)['"]/);
                const cuisineName = match ? match[1] : "";
                const label = cuisineName ? `Remove '${cuisineName}' cuisine` : "Remove cuisine restriction";
                
                const chip = createSuggestionChip(label, "restaurant_menu", () => {
                    document.getElementById("cuisine-input").value = "";
                    form.dispatchEvent(new Event("submit"));
                });
                suggestionsList.appendChild(chip);
            }
            
            // 2. Rating requirement
            else if (text.includes("rating")) {
                const match = suggestion.match(/(\d+\.\d+|\d+)/);
                let targetRating = 0.0;
                let label = "Lower rating requirement";
                if (match) {
                    targetRating = parseFloat(match[0]);
                    label = `Lower rating requirement (try ${targetRating}★ or below)`;
                }
                
                const chip = createSuggestionChip(label, "star_half", () => {
                    const ratingSelect = document.getElementById("rating-select");
                    if (ratingSelect) {
                        let bestVal = "0.0";
                        Array.from(ratingSelect.options).forEach(opt => {
                            const val = parseFloat(opt.value);
                            if (!isNaN(val) && val <= targetRating && val > parseFloat(bestVal)) {
                                bestVal = opt.value;
                            }
                        });
                        ratingSelect.value = bestVal;
                    }
                    form.dispatchEvent(new Event("submit"));
                });
                suggestionsList.appendChild(chip);
            }
            
            // 3. Budget tier restriction
            else if (text.includes("budget")) {
                const hasLow = text.includes("low");
                const hasMedium = text.includes("medium");
                const hasHigh = text.includes("high");
                
                const addBudgetChip = (tier, tierLabel) => {
                    const chip = createSuggestionChip(`Switch to ${tierLabel} budget`, "payments", () => {
                        const radio = document.getElementById(`budget-${tier}`);
                        if (radio) {
                            radio.checked = true;
                        }
                        form.dispatchEvent(new Event("submit"));
                    });
                    suggestionsList.appendChild(chip);
                };

                let added = false;
                if (hasLow) { addBudgetChip("low", "Low"); added = true; }
                if (hasMedium) { addBudgetChip("medium", "Medium"); added = true; }
                if (hasHigh) { addBudgetChip("high", "High"); added = true; }
                
                if (!added) {
                    const activeBudgetRadio = document.querySelector('input[name="budget"]:checked');
                    const activeBudget = activeBudgetRadio ? activeBudgetRadio.value : "medium";
                    if (activeBudget === "low" || activeBudget === "high") {
                        addBudgetChip("medium", "Medium");
                    } else {
                        addBudgetChip("high", "High");
                    }
                }
            }
            
            // 4. Default / General suggestion
            else {
                const chip = createSuggestionChip(suggestion, "explore", () => {
                    document.getElementById("cuisine-input").value = "";
                    const ratingSelect = document.getElementById("rating-select");
                    if (ratingSelect) ratingSelect.value = "0.0";
                    const midBudget = document.getElementById("budget-medium");
                    if (midBudget) midBudget.checked = true;
                    form.dispatchEvent(new Event("submit"));
                });
                suggestionsList.appendChild(chip);
            }
        });
    }

    // Render recommendations card list matching the premium design
    function renderRecommendations(data) {
        const recs = data.recommendations || [];
        const summary = data.summary || "";
        const isFallback = data.fallback || false;

        // Toggle badges
        if (isFallback) {
            fallbackBadge.classList.remove("hidden");
            aiBadge.classList.add("hidden");
        } else {
            aiBadge.classList.remove("hidden");
            fallbackBadge.classList.add("hidden");
        }

        // Set summary text
        summaryText.textContent = summary;

        // Clear previous cards
        cardsContainer.innerHTML = "";

        if (recs.length === 0) {
            showError("No valid recommendations found.");
            return;
        }

        // Render each restaurant card in a 2-column layout
        recs.forEach(rec => {
            const card = document.createElement("article");
            card.className = "restaurant-card";
            card.style.animationDelay = `${(rec.rank - 1) * 0.1}s`;

            // Format rating classes
            let ratingClass = "rating-new";
            let ratingText = "NEW";
            if (rec.rating !== null && rec.rating !== undefined && !isNaN(rec.rating)) {
                const r = parseFloat(rec.rating);
                ratingText = `${r.toFixed(1)} ★`;
                if (r >= 4.0) {
                    ratingClass = "rating-high";
                } else if (r >= 3.0) {
                    ratingClass = "rating-medium";
                }
            } else if (rec.rating_text) {
                ratingText = rec.rating_text;
                ratingClass = rec.rating_class || "rating-new";
            }

            const costText = rec.cost_text || "Approx cost unknown";
            const cuisineImg = getCuisineImage(rec.cuisines);

            // Format cuisines and attributes as tags
            let allTags = [...rec.cuisines];
            if (rec.attributes && rec.attributes.length > 0) {
                allTags = allTags.concat(rec.attributes.slice(0, 2));
            }
            const tagsHTML = allTags.map(t => `<span class="cuisine-tag">${escapeHTML(t)}</span>`).join("");

            // Format area details
            const areaText = rec.area ? `${escapeHTML(rec.cuisines[0] || 'Cuisine')} • ${escapeHTML(rec.area)}` : escapeHTML(rec.cuisines[0] || 'Cuisine');
            
            // Mock dynamic distances for scannability
            const mockDistance = `${rec.rank * 230 + 350} m`;

            // Build premium HTML structure
            card.innerHTML = `
                <div class="card-image-box">
                    <img src="${cuisineImg}" alt="${escapeHTML(rec.name)}" onerror="this.src='https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=400&q=80';">
                    <button class="favorite-btn" aria-label="Add to favorites">
                        <span class="material-symbols-outlined">favorite</span>
                    </button>
                </div>
                <div class="card-details-container">
                    <div class="card-info">
                        <h3 class="restaurant-name" title="${escapeHTML(rec.name)}">${escapeHTML(rec.name)}</h3>
                        <div class="restaurant-cuisine-area">${areaText}</div>
                        <div class="restaurant-meta">
                            <span class="rating-badge ${ratingClass}">${ratingText}</span>
                            <span class="meta-dot">•</span>
                            <span class="distance-text">${mockDistance}</span>
                            <span class="meta-dot">•</span>
                            <span class="cost-text">${costText}</span>
                        </div>
                        <div class="card-tags">
                            ${tagsHTML}
                        </div>
                    </div>
                    <div class="ai-reason-box">
                        <div class="ai-reason-header">
                            <span class="material-symbols-outlined sparkle-icon">sparkles</span>
                            <span>Why AI picked this</span>
                        </div>
                        <p class="ai-reason-text">${escapeHTML(rec.explanation)}</p>
                    </div>
                </div>
            `;

            // Setup favorites heart toggle
            const favBtn = card.querySelector(".favorite-btn");
            favBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                favBtn.classList.toggle("active");
            });

            cardsContainer.appendChild(card);
        });

        // Show Results Content
        resultsContent.classList.remove("hidden");
    }
});
