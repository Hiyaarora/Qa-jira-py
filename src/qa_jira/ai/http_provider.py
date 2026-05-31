from __future__ import annotations

import httpx

from qa_jira.models import Config

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Tried in order when the configured model returns 404 (offline/removed).
# All are free on OpenRouter and support the chat-completions API.
FALLBACK_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "google/gemma-3-4b-it:free",
]


class HttpProvider:
    """Calls any OpenAI-compatible /chat/completions endpoint via raw httpx.

    Works for OpenRouter, Anthropic (via their OpenAI-compatible endpoint),
    and any other provider that speaks the chat-completions API.
    If the configured model returns 404, automatically falls back through
    FALLBACK_MODELS so the user never sees a model-not-found error.
    """

    def __init__(self, config: Config) -> None:
        if config.aiBaseUrl:
            base = config.aiBaseUrl.rstrip("/")
        elif config.aiProvider == "anthropic":
            base = ANTHROPIC_BASE_URL
        elif config.aiProvider == "openrouter":
            base = OPENROUTER_BASE_URL
        else:
            base = OPENROUTER_BASE_URL

        self._url = base + "/chat/completions"
        self._headers = {
            "Authorization": "Bearer " + config.aiApiKey,
            "Content-Type": "application/json",
        }
        self._model = config.aiModel
        # Only use fallbacks for OpenRouter (free tier); paid providers don't need them
        self._use_fallbacks = config.aiProvider in ("openrouter", "openai-compatible")

    def _post(self, model: str, system_prompt: str, user_prompt: str, max_tokens: int) -> httpx.Response:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        with httpx.Client(timeout=60) as client:
            return client.post(self._url, json=payload, headers=self._headers)

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        models_to_try = [self._model]
        if self._use_fallbacks:
            models_to_try += [m for m in FALLBACK_MODELS if m != self._model]

        last_err = "No models available"
        for model in models_to_try:
            resp = self._post(model, system_prompt, user_prompt, max_tokens)

            if resp.status_code == 404:
                # Model offline — silently try next
                try:
                    last_err = resp.json().get("error", {}).get("message") or f"404 for {model}"
                except Exception:
                    last_err = f"404 for {model}"
                continue

            if resp.status_code == 429:
                try:
                    retry = resp.json().get("error", {}).get("metadata", {}).get(
                        "retry_after_seconds", ""
                    )
                except Exception:
                    retry = ""
                hint = f" Retry after {int(float(retry))}s." if retry else ""
                raise RuntimeError(f"Rate limited (429).{hint} Try again shortly.")

            if resp.status_code >= 400:
                try:
                    msg = resp.json().get("error", {}).get("message") or resp.text
                except Exception:
                    msg = resp.text
                raise RuntimeError(f"AI request failed ({resp.status_code}): {msg}")

            return resp.json()["choices"][0]["message"]["content"] or ""

        raise RuntimeError(f"All AI models unavailable. Last error: {last_err}")
