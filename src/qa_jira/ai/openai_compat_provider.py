from __future__ import annotations

from openai import OpenAI

from qa_jira.models import Config


class OpenAICompatProvider:
    """Works for OpenRouter and any OpenAI-compatible endpoint."""

    def __init__(self, config: Config) -> None:
        base_url = config.aiBaseUrl
        if base_url is None and config.aiProvider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        self._client = OpenAI(api_key=config.aiApiKey, base_url=base_url)
        self._model = config.aiModel

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""
