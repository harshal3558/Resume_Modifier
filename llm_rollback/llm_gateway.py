"""
llm_rollback/llm_gateway.py
============================
LLM Rollback Gateway — 10 models across Groq and Google Gemini.

Fallback chain (tried in order):
  Groq  1 → llama-3.3-70b-versatile
  Groq  2 → llama-3.1-8b-instant
  Groq  3 → gemma2-9b-it
  Groq  4 → mixtral-8x7b-32768
  Groq  5 → llama3-70b-8192
  Gemini 1 → gemini-2.0-flash
  Gemini 2 → gemini-1.5-pro
  Gemini 3 → gemini-1.5-flash
  Gemini 4 → gemini-2.0-flash-lite
  Gemini 5 → gemini-1.0-pro

If a model fails (rate-limit, API error, missing key, etc.) the
gateway automatically moves to the next model in the chain.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

LOGGER = logging.getLogger("resume_mod.llm_rollback")


# ---------------------------------------------------------------------------
# Provider descriptor
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMProvider:
    """Descriptor for a single LLM endpoint."""

    provider: str          # "groq" | "google"
    model: str             # model identifier
    api_key_env: str       # environment variable that holds the API key
    label: str             # human-readable label for logging


# ---------------------------------------------------------------------------
# Ordered fallback chain — 5 Groq + 5 Google Gemini = 10 total
# ---------------------------------------------------------------------------

FALLBACK_CHAIN: list[LLMProvider] = [
    # ── Groq ──────────────────────────────────────────────────────────────
    LLMProvider(
        provider="groq",
        model="llama-3.3-70b-versatile",
        api_key_env="GROQ_API_KEY",
        label="Groq · llama-3.3-70b-versatile",
    ),
    LLMProvider(
        provider="groq",
        model="llama-3.1-8b-instant",
        api_key_env="GROQ_API_KEY",
        label="Groq · llama-3.1-8b-instant",
    ),
    LLMProvider(
        provider="groq",
        model="gemma2-9b-it",
        api_key_env="GROQ_API_KEY",
        label="Groq · gemma2-9b-it",
    ),
    LLMProvider(
        provider="groq",
        model="mixtral-8x7b-32768",
        api_key_env="GROQ_API_KEY",
        label="Groq · mixtral-8x7b-32768",
    ),
    LLMProvider(
        provider="groq",
        model="llama3-70b-8192",
        api_key_env="GROQ_API_KEY",
        label="Groq · llama3-70b-8192",
    ),
    # ── Google Gemini ──────────────────────────────────────────────────────
    LLMProvider(
        provider="google",
        model="gemini-2.0-flash",
        api_key_env="GOOGLE_API_KEY",
        label="Gemini · gemini-2.0-flash",
    ),
    LLMProvider(
        provider="google",
        model="gemini-1.5-pro",
        api_key_env="GOOGLE_API_KEY",
        label="Gemini · gemini-1.5-pro",
    ),
    LLMProvider(
        provider="google",
        model="gemini-1.5-flash",
        api_key_env="GOOGLE_API_KEY",
        label="Gemini · gemini-1.5-flash",
    ),
    LLMProvider(
        provider="google",
        model="gemini-2.0-flash-lite",
        api_key_env="GOOGLE_API_KEY",
        label="Gemini · gemini-2.0-flash-lite",
    ),
    LLMProvider(
        provider="google",
        model="gemini-1.0-pro",
        api_key_env="GOOGLE_API_KEY",
        label="Gemini · gemini-1.0-pro",
    ),
]


# ---------------------------------------------------------------------------
# LLM Rollback Gateway
# ---------------------------------------------------------------------------

class LLMRollback:
    """
    Tries each LLM in FALLBACK_CHAIN sequentially.

    Usage
    -----
    gateway = LLMRollback()
    response = gateway.invoke("Your prompt here")
    """

    def __init__(
        self,
        chain: list[LLMProvider] | None = None,
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> None:
        self.chain = chain or FALLBACK_CHAIN
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Internal: build the LangChain chat model for a given provider
    # ------------------------------------------------------------------

    def _build_model(self, provider: LLMProvider):
        """Instantiate the appropriate LangChain chat model."""

        api_key: Optional[str] = os.getenv(provider.api_key_env)

        if not api_key:
            raise EnvironmentError(
                f"API key not set — env var '{provider.api_key_env}' is empty."
            )

        if provider.provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=provider.model,
                api_key=api_key,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        if provider.provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=provider.model,
                google_api_key=api_key,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )

        raise ValueError(
            f"Unknown provider: '{provider.provider}'"
        )

    # ------------------------------------------------------------------
    # Public: invoke with automatic fallback
    # ------------------------------------------------------------------

    def invoke(self, prompt: str) -> str:
        """
        Try each LLM in the fallback chain.

        Returns the first successful response text.
        Raises RuntimeError if all providers fail.
        """

        if not prompt or not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        last_error: Exception | None = None

        for index, provider in enumerate(self.chain, start=1):
            LOGGER.info(
                "[%d/%d] Trying %s …",
                index,
                len(self.chain),
                provider.label,
            )

            try:
                model = self._build_model(provider)
                response = model.invoke(prompt)

                # LangChain returns an AIMessage; extract text content
                text = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                )

                LOGGER.info(
                    "✅ Success with %s",
                    provider.label,
                )

                return text

            except EnvironmentError as env_err:
                LOGGER.warning(
                    "⚠️  Skipping %s — %s",
                    provider.label,
                    env_err,
                )
                last_error = env_err

            except Exception as exc:
                LOGGER.warning(
                    "⚠️  %s failed — %s: %s",
                    provider.label,
                    type(exc).__name__,
                    exc,
                )
                last_error = exc

        raise RuntimeError(
            "All LLM providers in the fallback chain failed. "
            f"Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # List available providers
    # ------------------------------------------------------------------

    def available_providers(self) -> list[dict]:
        """Return a summary of the fallback chain."""
        return [
            {
                "rank": i + 1,
                "label": p.label,
                "provider": p.provider,
                "model": p.model,
                "api_key_env": p.api_key_env,
                "key_present": bool(os.getenv(p.api_key_env)),
            }
            for i, p in enumerate(self.chain)
        ]


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_gateway: LLMRollback | None = None


def get_llm_response(prompt: str) -> str:
    """
    Module-level shortcut.  Uses a shared LLMRollback singleton.

    Parameters
    ----------
    prompt : str
        The full prompt to send to the LLM.

    Returns
    -------
    str
        The model's response text.
    """
    global _gateway

    if _gateway is None:
        _gateway = LLMRollback()

    return _gateway.invoke(prompt)
