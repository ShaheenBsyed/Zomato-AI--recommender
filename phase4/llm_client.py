"""Phase 4: Recommendation Engine — LLM client client interface for Gemini and OpenAI."""

from __future__ import annotations

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LLMConfigurationError(Exception):
    """Raised when API keys or configurations are missing or incorrect."""
    pass

class LLMAPIError(Exception):
    """Raised when LLM API request fails after retries."""
    pass

class LLMClient:
    """Handles communication with LLM providers (Gemini or OpenAI) with retry logic."""

    def __init__(self) -> None:
        # Load environment variables (dotenv is loaded at the app level)
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.provider = os.getenv("LLM_PROVIDER", "").strip().lower()

        # Auto-detect provider if not explicitly set
        if not self.provider:
            if self.gemini_key:
                self.provider = "gemini"
            elif self.openai_key:
                self.provider = "openai"
            else:
                self.provider = "none"

        logger.info("Initialized LLM Client with provider: %s", self.provider)

    def ping(self) -> bool:
        """Lightweight verification of API keys and connectivity."""
        if self.provider == "none":
            return False
        
        # We can do a quick check to see if key strings look valid (non-empty)
        if self.provider == "gemini" and not self.gemini_key:
            return False
        if self.provider == "openai" and not self.openai_key:
            return False
        return True

    def generate_recommendations(self, prompt: str) -> str:
        """Calls the configured LLM API with retries and exponential backoff."""
        if self.provider == "none":
            raise LLMConfigurationError("No LLM API keys provided. Please set GEMINI_API_KEY or OPENAI_API_KEY.")

        if self.provider == "gemini":
            return self._call_gemini_with_retry(prompt)
        elif self.provider == "openai":
            return self._call_openai_with_retry(prompt)
        else:
            raise LLMConfigurationError(f"Unsupported LLM provider: {self.provider}")

    def _call_gemini_with_retry(self, prompt: str, max_retries: int = 3, base_delay: float = 2.0) -> str:
        """Calls Google Gemini API using google-genai SDK."""
        last_err: Optional[Exception] = None
        
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMConfigurationError(
                "The 'google-genai' SDK is required for Gemini. Install with: pip install google-genai"
            ) from exc

        try:
            # Initialize client with key
            client = genai.Client(api_key=self.gemini_key)
        except Exception as exc:
            raise LLMConfigurationError(f"Failed to initialize Gemini Client: {exc}") from exc

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Sending prompt to Gemini model %s (attempt %d/%d)...", model_name, attempt, max_retries)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2, # Low temperature for consistent, structured ranking
                        response_mime_type="application/json" # Request JSON output
                    )
                )
                if not response.text:
                    raise LLMAPIError("Gemini returned an empty response.")
                return response.text
            except Exception as exc:
                last_err = exc
                logger.warning("Gemini API call failed (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** (attempt - 1)))
        
        raise LLMAPIError(f"Gemini API request failed after {max_retries} attempts.") from last_err

    def _call_openai_with_retry(self, prompt: str, max_retries: int = 3, base_delay: float = 2.0) -> str:
        """Calls OpenAI API using openai SDK."""
        last_err: Optional[Exception] = None

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigurationError(
                "The 'openai' SDK is required for OpenAI. Install with: pip install openai"
            ) from exc

        try:
            client = OpenAI(api_key=self.openai_key)
        except Exception as exc:
            raise LLMConfigurationError(f"Failed to initialize OpenAI Client: {exc}") from exc

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        for attempt in range(1, max_retries + 1):
            try:
                logger.info("Sending prompt to OpenAI model %s (attempt %d/%d)...", model_name, attempt, max_retries)
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
                text = response.choices[0].message.content
                if not text:
                    raise LLMAPIError("OpenAI returned an empty response.")
                return text
            except Exception as exc:
                last_err = exc
                logger.warning("OpenAI API call failed (attempt %d/%d): %s", attempt, max_retries, exc)
                if attempt < max_retries:
                    time.sleep(base_delay * (2 ** (attempt - 1)))

        raise LLMAPIError(f"OpenAI API request failed after {max_retries} attempts.") from last_err
