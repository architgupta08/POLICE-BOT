"""
Hugging Face Inference API LLM handler.

Used as the cloud-friendly replacement for the local Ollama handler.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config import HF_API_TOKEN, HF_MODEL, SYSTEM_PROMPT

logger = logging.getLogger("police_bot.hf_llm")

_HF_BASE = "https://api-inference.huggingface.co/models"


class HuggingFaceHandler:
    """
    Calls the Hugging Face Inference API (text-generation task).

    Works with any text-generation model such as:
      - mistralai/Mistral-7B-Instruct-v0.2
      - HuggingFaceH4/zephyr-7b-beta
      - tiiuae/falcon-7b-instruct
    """

    def __init__(
        self,
        api_token: str = HF_API_TOKEN,
        model: str = HF_MODEL,
        timeout: float = 120.0,
    ) -> None:
        self.api_token = api_token
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------
    # Health / availability
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when an HF token is configured."""
        return bool(self.api_token)

    def is_model_available(self) -> bool:
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
        if not self.api_token:
            raise RuntimeError(
                "HF_API_TOKEN is not set. "
                "Please add it to your .env file or Render/Vercel environment variables."
            )

        full_prompt = self._build_prompt(prompt, context, chat_history or [])
        url = f"{_HF_BASE}/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        payload: dict[str, Any] = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": 0.3,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False,
            },
        }

        try:
            resp = self._client.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            # HF returns a list with one item
            if isinstance(data, list) and data:
                text = data[0].get("generated_text", "")
            else:
                text = str(data)
            if not text.strip():
                raise ValueError("Empty response from Hugging Face")
            return text.strip()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HF API HTTP error: %s – %s", exc.response.status_code, exc.response.text
            )
            raise RuntimeError(
                f"Hugging Face API request failed ({exc.response.status_code}). "
                "Check your HF_API_TOKEN and model name."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("HF API connection error: %s", exc)
            raise RuntimeError("Could not connect to Hugging Face API.") from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        prompt: str,
        context: str,
        chat_history: list[dict[str, str]],
    ) -> str:
        """Build a chat-style prompt using the [INST] format common for instruct models."""
        parts: list[str] = [f"[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n"]

        # Include recent history (last 3 turns)
        for turn in chat_history[-3:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            if role == "user":
                parts.append(f"{content} [/INST] ")
            elif role == "assistant":
                parts.append(f"{content} </s><s>[INST] ")

        # Current user turn with RAG context
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

        parts.append(f"{user_content} [/INST]")
        return "".join(parts)

    def __del__(self):
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            pass
