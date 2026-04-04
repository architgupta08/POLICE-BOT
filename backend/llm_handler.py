import json
import logging
from pathlib import Path
from typing import Any

import httpx

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYSTEM_PROMPT

logger = logging.getLogger("police_bot.llm")


class OllamaHandler:
    """Thin wrapper around the Ollama HTTP API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    # ------------------------------------------------------------------
    # Health / availability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama not reachable: %s", exc)
            return False

    def is_model_available(self) -> bool:
        """Return True if the configured model is already pulled."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if resp.status_code != 200:
                return False
            data = resp.json()
            model_names = [m.get("name", "") for m in data.get("models", [])]
            return any(self.model in name for name in model_names)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not check model availability: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        context: str = "",
        chat_history: list[dict[str, str]] | None = None,
    ) -> str:
        """
        Generate a response using Ollama's /api/chat endpoint.

        The prompt is augmented with the retrieved context.
        """
        if not self.is_available():
            raise RuntimeError(
                "Ollama server is not running. "
                "Please start it with: ollama serve"
            )

        messages = self._build_messages(prompt, context, chat_history or [])

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }

        try:
            resp = self._client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            if not content:
                raise ValueError("Empty response from Ollama")
            return content.strip()
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error: %s – %s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"LLM request failed ({exc.response.status_code})") from exc
        except httpx.RequestError as exc:
            logger.error("Ollama connection error: %s", exc)
            raise RuntimeError("Could not connect to Ollama. Is it running?") from exc

    def generate_stream(
        self,
        prompt: str,
        context: str = "",
        chat_history: list[dict[str, str]] | None = None,
    ):
        """
        Stream tokens from Ollama (generator that yields str chunks).
        """
        if not self.is_available():
            raise RuntimeError("Ollama server is not running.")

        messages = self._build_messages(prompt, context, chat_history or [])

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }

        with self._client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

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

    def __del__(self):
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass
