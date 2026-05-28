from __future__ import annotations

from anthropic import Anthropic

from qa_jira.models import Config


class AnthropicProvider:
    def __init__(self, config: Config) -> None:
        self._client = Anthropic(api_key=config.aiApiKey)
        self._model = config.aiModel

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        return "".join(parts)
