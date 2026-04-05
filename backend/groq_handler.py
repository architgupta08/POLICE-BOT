"""
Groq Cloud LLM handler.

Used as the cloud-friendly replacement for the local Ollama handler.
Requires a free Groq API key from https://console.groq.com
"""
from __future__ import annotations

import logging
from typing import Any

from config import GROQ_API_KEY, GROQ_MODEL, SYSTEM_PROMPT

logger = logging.getLogger("police_bot.groq_llm")


class GroqHandler:
    """
    Calls the Groq Cloud Inference API using the official groq Python SDK.

    Works with any Groq-hosted model such as:
      - mixtral-8x7b-32768  (default, powerful and fast)
      - llama3-8b-8192
      - llama3-70b-8192
      - gemma-7b-it
    """

    def __init__(
        self,
        api_key: str = GROQ_API_KEY,
        model: str = GROQ_MODEL,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client: Any = None
        if api_key:
            try:
                from groq import Groq  # type: ignore[import-untyped]

                self._client = Groq(api_key=api_key)
            except ImportError:
                logger.error(
                    "groq package is not installed. Run: pip install groq"
                )

    # ------------------------------------------------------------------
    # Health / availability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when a Groq API key is configured and the SDK is installed."""
        return self._client is not None and bool(self.api_key)

    def is_model_available(self) -> bool:
        """Groq models are always available as cloud models — no local pull needed."""
        return self.is_available()

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        context: str = "",
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response using the Groq API."""
        if not self.api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Please get a free API key from https://console.groq.com "
                "and add it to your environment variables."
            )
        if self._client is None:
            raise RuntimeError(
                "Groq SDK is not installed. Run: pip install groq"
            )

        messages = self._build_messages(prompt, context, chat_history or [])

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                top_p=0.9,
                max_tokens=1024,
            )
            content = completion.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Groq")
            return content.strip()
        except Exception as exc:
            # Import Groq-specific error types if available
            exc_type = type(exc).__name__
            if exc_type in ("AuthenticationError",):
                logger.error("Groq authentication error: %s", exc)
                raise RuntimeError(
                    "Groq API authentication failed. Check your GROQ_API_KEY."
                ) from exc
            if exc_type in ("RateLimitError",):
                logger.error("Groq rate limit error: %s", exc)
                raise RuntimeError(
                    "Groq API rate limit exceeded. Please try again shortly."
                ) from exc
            logger.error("Groq API error (%s): %s", exc_type, exc)
            raise RuntimeError(f"Groq API request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        prompt: str,
        context: str,
        chat_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject recent history (last 6 turns to stay within context window)
        for turn in chat_history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})

        # Compose the user turn with context
        if context:
            user_content = (
                f"RELEVANT CONTEXT FROM NDPS KNOWLEDGE BASE:\n"
                f"{'=' * 60}\n"
                f"{context}\n"
                f"{'=' * 60}\n\n"
                f"OFFICER QUERY:\n{prompt}"
            )
        else:
            user_content = prompt

        messages.append({"role": "user", "content": user_content})
        return messages
