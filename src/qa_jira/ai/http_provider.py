from __future__ import annotations

import httpx

from qa_jira.models import Config

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class HttpProvider:
    """Calls any OpenAI-compatible /chat/completions endpoint via raw httpx.

    Works for OpenRouter, Anthropic (via their OpenAI-compatible endpoint),
    and any other provider that speaks the chat-completions API.
    """

    def __init__(self, config: Config) -> None:
        if config.aiBaseUrl:
            base = config.aiBaseUrl.rstrip("/")
        elif config.aiProvider == "anthropic":
            base = ANTHROPIC_BASE_URL
        elif config.aiProvider == "openrouter":
            base = OPENROUTER_BASE_URL
        else:
            base = OPENROUTER_BASE_URL  # fallback

        self._url = base + "/chat/completions"
        self._headers = {
            "Authorization": "Bearer " + config.aiApiKey,
            "Content-Type": "application/json",
        }
        self._model = config.aiModel

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(self._url, json=payload, headers=self._headers)

        if resp.status_code == 429:
            retry = resp.json().get("error", {}).get("metadata", {}).get(
                "retry_after_seconds", ""
            )
            hint = f" Retry after {int(retry)}s." if retry else ""
            raise RuntimeError(
                f"Rate limited (429).{hint} Try a different model or wait."
            )
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("error", {}).get("message") or resp.text
            except Exception:
                msg = resp.text
            raise RuntimeError(f"AI request failed ({resp.status_code}): {msg}")

        return resp.json()["choices"][0]["message"]["content"] or ""
