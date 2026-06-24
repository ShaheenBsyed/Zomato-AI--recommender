"""Unit tests for Phase 6: Backend API Development."""

from __future__ import annotations

import json
import pytest
from phase6.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    """Test that index route loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data or b"<html>" in response.data


def test_locations_route(client):
    """Test locations API route."""
    response = client.get("/api/locations")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0


def test_cors_headers(client):
    """Test that CORS headers are present on API responses."""
    response = client.get("/api/locations")
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers or response.headers.get("Access-Control-Allow-Origin") == "*"


def test_recommendations_invalid_json(client):
    """Test recommend endpoint with invalid JSON body."""
    response = client.post("/api/recommend", data="not json", content_type="application/json")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_recommendations_missing_location(client):
    """Test recommend endpoint with missing location parameter."""
    payload = {"budget": "low"}
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data

