from __future__ import annotations

import json
import re
from typing import Any, Protocol

from qa_jira.adf import (
    make_bullet_list,
    make_doc,
    make_link,
    make_paragraph,
    make_rule,
    make_text,
)
from qa_jira.models import AIBugResult, AITaskResult, AttachmentInfo, Issue


class Provider(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str: ...


_FENCE_RE = re.compile(r"```(?:json)?", re.IGNORECASE)


def strip_fences(raw: str) -> str:
    return _FENCE_RE.sub("", raw).strip()


def parse_json_loose(raw: str) -> dict[str, Any]:
    """Try direct JSON, then a one-shot trailing-trim repair."""
    cleaned = strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = re.sub(r',\s*"[^"]*":\s*\[?\s*"?[^"}\]]*$', "", cleaned) + "}"
        return json.loads(repaired)


def build_bug_result(
    parsed: dict[str, Any], raw_description: str, environment: str
) -> AIBugResult:
    title = (parsed.get("title") or "").strip() or raw_description[:80]
    steps_raw = parsed.get("stepsToReproduce")
    if isinstance(steps_raw, str):
        steps_raw = [steps_raw]
    if not isinstance(steps_raw, list) or not steps_raw:
        steps_raw = ["Reproduce using the description provided"]
    steps = [re.sub(r"^\d+\.\s*", "", str(s)) for s in steps_raw]

    actual = (parsed.get("actualResult") or "").strip() or raw_description
    expected = (
        (parsed.get("expectedResult") or "").strip()
        or "Correct behavior as expected by the user"
    )
    ctx = (parsed.get("additionalContext") or "").strip()

    blocks: list[dict[str, Any]] = []
    blocks.append(make_paragraph([make_text("Steps to Reproduce", bold=True)]))
    blocks.append(make_bullet_list(steps))
    blocks.append(make_paragraph([make_text("Actual Result", bold=True)]))
    blocks.append(make_paragraph([make_text(actual)]))
    blocks.append(make_paragraph([make_text("Expected Result", bold=True)]))
    blocks.append(make_paragraph([make_text(expected)]))
    if ctx:
        blocks.append(make_paragraph([make_text("Additional Context", bold=True)]))
        blocks.append(make_paragraph([make_text(ctx)]))
    if environment:
        blocks.append(make_paragraph([make_text("Environment", bold=True)]))
        blocks.append(make_paragraph([make_text(environment)]))

    preview_parts: list[str] = [
        "Steps to Reproduce:\n" + "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(steps)),
        f"\nActual Result:\n  {actual}",
        f"\nExpected Result:\n  {expected}",
    ]
    if ctx:
        preview_parts.append(f"\nAdditional Context:\n  {ctx}")
    if environment:
        preview_parts.append(f"\nEnvironment:\n  {environment}")

    return AIBugResult(
        title=title,
        stepsToReproduce=steps,
        actualResult=actual,
        expectedResult=expected,
        additionalContext=ctx,
        adf=make_doc(blocks),
        preview="\n".join(preview_parts),
    )


def build_task_result(
    parsed: dict[str, Any],
    story: Issue | None,
    bugs: list[Issue],
    attachment: AttachmentInfo | None,
) -> AITaskResult:
    summary = (parsed.get("summary") or "").strip()
    details = (parsed.get("details") or "").strip()
    bugs_text = (parsed.get("bugs") or "").strip()
    outcome = (parsed.get("outcome") or "").strip()

    blocks: list[dict[str, Any]] = []
    if summary:
        blocks.append(make_paragraph([make_text("Summary", bold=True)]))
        blocks.append(make_paragraph([make_text(summary)]))
    if details:
        blocks.append(make_paragraph([make_text("Details", bold=True)]))
        blocks.append(make_paragraph([make_text(details)]))
    if bugs_text:
        blocks.append(make_paragraph([make_text("Bugs Found", bold=True)]))
        blocks.append(make_paragraph([make_text(bugs_text)]))
    if outcome:
        blocks.append(make_paragraph([make_text("Outcome", bold=True)]))
        blocks.append(make_paragraph([make_text(outcome)]))

    if story or bugs:
        blocks.append(make_rule())
    if story:
        blocks.append(
            make_paragraph(
                [
                    make_text("Story: ", bold=True),
                    make_link(f"{story.key} — {story.summary}", story.url),
                ]
            )
        )
    for b in bugs:
        blocks.append(
            make_paragraph(
                [
                    make_text("Bug: ", bold=True),
                    make_link(f"{b.key} — {b.summary}", b.url),
                ]
            )
        )
    if attachment and attachment.type == "google-sheet" and attachment.url:
        blocks.append(
            make_paragraph(
                [
                    make_text("Test Cases: ", bold=True),
                    make_link("Open Google Sheet", attachment.url),
                ]
            )
        )

    preview_parts: list[str] = []
    if summary:
        preview_parts.append("Summary\n" + summary)
    if details:
        preview_parts.append("Details\n" + details)
    if bugs_text:
        preview_parts.append("Bugs Found\n" + bugs_text)
    if outcome:
        preview_parts.append("Outcome\n" + outcome)
    if story:
        preview_parts.append(f"Story: {story.key} — {story.summary}")
    if bugs:
        preview_parts.append("Bugs: " + ", ".join(b.key for b in bugs))

    return AITaskResult(
        summary=summary,
        details=details,
        bugs=bugs_text,
        outcome=outcome,
        adf=make_doc(blocks),
        preview="\n\n".join(preview_parts),
    )
