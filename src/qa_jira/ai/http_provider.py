from __future__ import annotations

import base64
from pathlib import Path

import httpx

from qa_jira.models import Config

IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Vision-capable free models tried in order when images are present
VISION_MODELS = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "qwen/qwen2-vl-7b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-90b-vision-instruct:free",
]

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Seed list — tried in order when configured model returns 404.
# Supplemented at runtime by querying OpenRouter's /models endpoint.
FALLBACK_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "google/gemma-3-4b-it:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "openchat/openchat-7b:free",
]


def _fetch_free_models(api_key: str) -> list[str]:
    """Ask OpenRouter which free models are currently available."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": "Bearer " + api_key},
            )
        if resp.status_code != 200:
            return []
        models = resp.json().get("data", [])
        # A model is free if its prompt pricing is "0"
        free = [
            m["id"]
            for m in models
            if str(m.get("pricing", {}).get("prompt", "1")) == "0"
        ]
        return free
    except Exception:
        return []


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
        self._api_key = config.aiApiKey
        # Only use fallbacks for OpenRouter; paid/self-hosted providers don't need them
        self._use_fallbacks = config.aiProvider in ("openrouter", "openai-compatible")

    @staticmethod
    def _encode_images(image_paths: list[str]) -> list[dict]:
        """Return a list of image_url content blocks for the multimodal message."""
        blocks = []
        for path in image_paths:
            p = Path(path)
            if not p.exists():
                continue
            mime = IMAGE_MIME.get(p.suffix.lower(), "image/png")
            data = base64.b64encode(p.read_bytes()).decode()
            blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}"},
            })
        return blocks

    def _post(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        image_paths: list[str] | None = None,
    ) -> httpx.Response:
        if image_paths:
            user_content: str | list = [{"type": "text", "text": user_prompt}]
            user_content += self._encode_images(image_paths)
        else:
            user_content = user_prompt

        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        with httpx.Client(timeout=90) as client:
            return client.post(self._url, json=payload, headers=self._headers)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        image_paths: list[str] | None = None,
    ) -> str:
        # When images are present, try vision models first
        if image_paths and self._use_fallbacks:
            vision_first = [m for m in VISION_MODELS if m != self._model]
            base_list = [self._model] + vision_first
        else:
            base_list = [self._model]

        models_to_try = list(base_list)
        if self._use_fallbacks:
            live_free = _fetch_free_models(self._api_key)
            seen = set(base_list)
            for m in live_free + FALLBACK_MODELS:
                if m not in seen:
                    seen.add(m)
                    models_to_try.append(m)

        last_err = "No models available"
        for model in models_to_try:
            resp = self._post(model, system_prompt, user_prompt, max_tokens, image_paths)

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
