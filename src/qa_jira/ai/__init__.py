from __future__ import annotations

from qa_jira.ai.base import build_bug_result, build_task_result, parse_json_loose
from qa_jira.ai.http_provider import HttpProvider
from qa_jira.models import AIBugResult, AITaskResult, AttachmentInfo, Config, Issue
from qa_jira.prompts import (
    SYSTEM_PROMPT_BUG,
    SYSTEM_PROMPT_TASK,
    build_bug_user_prompt,
    build_task_user_prompt,
)


def get_provider(config: Config) -> HttpProvider:
    return HttpProvider(config)


def generate_bug_description(
    config: Config,
    raw_description: str,
    environment: str,
    attachment: AttachmentInfo | None = None,
    image_paths: list[str] | None = None,
) -> AIBugResult:
    provider = get_provider(config)
    raw = provider.complete_json(
        SYSTEM_PROMPT_BUG,
        build_bug_user_prompt(raw_description),
        max_tokens=4000,
        image_paths=image_paths or [],
    )
    try:
        parsed = parse_json_loose(raw)
    except Exception:
        parsed = {}
    return build_bug_result(parsed, raw_description, environment, attachment)


def generate_task_description(
    config: Config,
    task_type: str,
    story: Issue | None,
    bugs: list[Issue],
    user_notes: str,
    attachment: AttachmentInfo | None,
    image_paths: list[str] | None = None,
) -> AITaskResult:
    provider = get_provider(config)
    raw = provider.complete_json(
        SYSTEM_PROMPT_TASK,
        build_task_user_prompt(task_type, story, bugs, user_notes, attachment),
        max_tokens=4000,
        image_paths=image_paths or [],
    )
    try:
        parsed = parse_json_loose(raw)
    except Exception:
        cleaned = (raw or "").strip()
        parsed = {
            "summary": "AI output could not be parsed — raw text in Details below.",
            "details": cleaned[:2000] if cleaned else "(no output)",
            "outcome": "Task completed.",
        }
    return build_task_result(parsed, story, bugs, attachment)
