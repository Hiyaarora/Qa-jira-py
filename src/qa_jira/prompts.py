from __future__ import annotations

from qa_jira.models import AttachmentInfo, Issue

SYSTEM_PROMPT_TASK = (
    "You are a senior QA engineer writing detailed, professional Jira task descriptions. "
    "Write in first person. Be specific and thorough. Never invent details not given to you — "
    "only elaborate on what is provided. Return ONLY valid JSON. No markdown fences. "
    "No extra text. Use the exact keys requested."
)

SYSTEM_PROMPT_BUG = (
    "You are a QA engineer writing structured Jira bug reports. You receive a raw description "
    "of a bug and convert it into a professional structured report. Return ONLY valid JSON. "
    "No markdown fences. No explanation. No preamble.\n"
    "Response format:\n"
    "{\n"
    '  "title": "Short descriptive bug title, max 80 chars, starts with a verb",\n'
    '  "stepsToReproduce": ["Step 1...", "Step 2...", "Step 3..."],\n'
    '  "actualResult": "What actually happens",\n'
    '  "expectedResult": "What should happen instead",\n'
    '  "additionalContext": "Any extra context, environment info, or notes (can be empty string)"\n'
    "}"
)


def build_bug_user_prompt(raw_description: str) -> str:
    return (
        "Convert this bug description into a structured report:\n\n"
        f'"{raw_description}"\n\n'
        "Rules:\n"
        '- Title must be specific and descriptive, not generic like "Bug found"\n'
        "- Steps must be numbered, actionable, and specific\n"
        "- If steps are not clear from the description, infer reasonable steps based on the context\n"
        "- Actual result: what went wrong\n"
        "- Expected result: what the correct behavior should be\n"
        "- Return ONLY the JSON object"
    )


def _bugs_block(bugs: list[Issue]) -> str:
    if not bugs:
        return ""
    parts: list[str] = []
    for i, b in enumerate(bugs, 1):
        parts.append(
            f"\nBUG {i} KEY: {b.key}"
            f"\nBUG {i} TITLE: {b.summary}"
            f"\nBUG {i} DESCRIPTION: {b.descriptionText or 'No description provided.'}"
            f"\nBUG {i} STATUS: {b.status}"
        )
    return "\n".join(parts)


def build_task_user_prompt(
    task_type: str,
    story: Issue | None,
    bugs: list[Issue],
    user_notes: str,
    attachment: AttachmentInfo | None,
) -> str:
    if story:
        story_block = (
            f"\nSTORY KEY: {story.key}"
            f"\nSTORY TITLE: {story.summary}"
            f"\nSTORY DESCRIPTION: {story.descriptionText or 'No description provided.'}"
            f"\nSTORY TYPE: {story.issueType}"
            f"\nSTORY STATUS: {story.status}"
        )
    else:
        story_block = "No story provided."

    bugs_block = _bugs_block(bugs)
    attach_block = (
        f"I am also attaching: {attachment.label} ({attachment.name})" if attachment else ""
    )
    notes_block = (
        f"Additional notes from me: {user_notes}"
        if user_notes and user_notes.strip()
        else ""
    )

    if task_type == "tested":
        bugs_part = (
            f"\nI found and filed the following {len(bugs)} bug(s) during testing:\n{bugs_block}"
            if bugs
            else "\nNo bugs were found during testing."
        )
        bugs_key = (
            '"bugs": "For each bug: 2-3 sentences describing what the bug is, '
            "how it manifests, what the expected vs actual behavior is, and the potential "
            "impact on users. Be specific about each bug's nature and severity.\","
            if bugs
            else ""
        )
        return (
            "I am a QA engineer. Today I tested the following Jira story:\n"
            f"{story_block}\n{bugs_part}\n{notes_block}\n{attach_block}\n\n"
            "Write a detailed, professional Jira task description. Return ONLY this JSON "
            "(no backticks, no explanation):\n"
            "{\n"
            '  "summary": "4-5 sentences describing what the story is about, what specific '
            "functionality or feature I tested, what areas and user flows I covered, and the "
            'overall scope of testing. Be specific about what was validated.",\n'
            '  "details": "4-5 sentences explaining my testing approach in detail — what types '
            "of testing I performed, specific scenarios I validated, boundary conditions I "
            'checked, and how thorough the coverage was.",\n'
            f"  {bugs_key}\n"
            '  "outcome": "2 sentences: final status of testing — whether the story passed or '
            'failed QA, how many bugs were found, and whether the story is ready for release."\n'
            "}"
        )

    if task_type == "testcases":
        return (
            "I am a QA engineer. Today I wrote test cases for the following Jira story:\n"
            f"{story_block}\n{notes_block}\n{attach_block}\n\n"
            "Write a detailed, professional Jira task description. Return ONLY this JSON:\n"
            "{\n"
            '  "summary": "4-5 sentences about the story and why these test cases matter.",\n'
            '  "details": "4-5 sentences explaining the scenarios, edge cases, and flows '
            'covered. Positive, negative, and data-driven cases.",\n'
            '  "outcome": "2 sentences: completion status and total number of test cases."\n'
            "}"
        )

    # task_type == "other"
    bugs_part = (
        f"\nI also found and filed the following {len(bugs)} bug(s):\n{bugs_block}"
        if bugs
        else ""
    )
    bugs_key = (
        '"bugs": "For each bug: 2-3 sentences describing what the bug is, how it manifests, '
        "and the potential impact on users.\","
        if bugs
        else ""
    )
    return (
        "I am a QA engineer. Today I did the following work:\n"
        f"{user_notes}\n{bugs_part}\n{attach_block}\n\n"
        "Write a detailed, professional Jira task description. Return ONLY this JSON:\n"
        "{\n"
        '  "summary": "4-5 sentences describing the QA work performed and why it matters.",\n'
        '  "details": "4-5 sentences explaining approach, methodology, and findings.",\n'
        f"  {bugs_key}\n"
        '  "outcome": "2 sentences: status and follow-ups."\n'
        "}"
    )
