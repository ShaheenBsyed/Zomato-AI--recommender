"""Entry point for the AI-Powered Restaurant Recommendation System."""

from __future__ import annotations

from phase6.api import app

if __name__ == "__main__":
    # In development, run on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
