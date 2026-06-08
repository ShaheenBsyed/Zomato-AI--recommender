# Problem Statement: AI-Powered Restaurant Recommendation System

## Overview

Build an AI-powered restaurant recommendation service inspired by Zomato. The system should combine structured restaurant data with a Large Language Model (LLM) to deliver personalized, human-like suggestions based on user preferences.

## Objective

Design and implement an application that:

- Accepts user preferences (location, budget, cuisine, ratings, and more)
- Uses a real-world restaurant dataset for grounding recommendations
- Leverages an LLM to rank options and generate natural-language explanations
- Presents results in a clear, useful format for end users

## Data Source

Use the Zomato restaurant dataset hosted on Hugging Face:

**Dataset:** [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)

Relevant fields to extract include restaurant name, location, cuisine, cost, and rating.

## System Workflow

### 1. Data Ingestion

- Load and preprocess the dataset from Hugging Face
- Clean and normalize fields needed for filtering and display
- Prepare structured records the recommendation pipeline can query

### 2. User Input

Collect preferences such as:

| Preference | Examples |
|------------|----------|
| Location | Delhi, Bangalore |
| Budget | Low, medium, high |
| Cuisine | Italian, Chinese |
| Minimum rating | e.g., 4.0+ |
| Additional context | Family-friendly, quick service, outdoor seating |

### 3. Integration Layer

- Filter the dataset based on user input
- Select a candidate set of restaurants for ranking
- Build an LLM prompt that includes structured results and user constraints
- Design the prompt so the model can reason over options and justify its choices

### 4. Recommendation Engine

Use the LLM to:

- Rank restaurants against the user's stated preferences
- Explain why each recommendation is a good fit
- Optionally summarize trade-offs across the top choices

### 5. Output Display

Present the top recommendations in a user-friendly format, including:

- Restaurant name
- Cuisine
- Rating
- Estimated cost
- AI-generated explanation for each pick

## Expected Outcome

A working recommendation flow where users enter preferences, the system filters real restaurant data, an LLM refines and explains the best matches, and the final output is easy to read and act on.
