from __future__ import annotations

from qa_jira.models import AttachmentInfo, Issue

SYSTEM_PROMPT_TASK = (
    "You are a senior QA engineer writing detailed, professional Jira task descriptions. "
    "Write in first person. Be specific, thorough, and verbose — Jira readers want context. "
    "Never invent facts not given to you, but elaborate generously on what is provided "
    "(scope, methodology, edge cases considered, implications). "
    "Return ONLY a single JSON object. No prose before or after. No markdown fences. "
    "No code blocks. Use the exact keys requested. Each string field must be at least "
    "80 words — do not return short answers."
)

SYSTEM_PROMPT_BUG = (
    "You are a senior QA engineer writing structured Jira bug reports for a product team. "
    "You take a user's raw bug description and transform it into a detailed, professional "
    "report with rich, specific content in every field. Output format is JSON only — no prose "
    "before or after, no markdown fences, no code blocks, no commentary. "
    "Every field must meet its length requirement; terse one-line answers are not acceptable. "
    "Never invent product features that weren't mentioned in the user input, but always "
    "elaborate on environment, reproducibility, and user impact since those are always relevant."
)


def build_bug_user_prompt(raw_description: str) -> str:
    return (
        "Convert this bug description into a structured, detailed bug report:\n\n"
        f'"""{raw_description}"""\n\n'
        "Return ONLY a single JSON object with exactly these keys, no prose, no fences:\n"
        "{\n"
        '  "title": "verb-led, specific, max 80 chars",\n'
        '  "stepsToReproduce": ["…", "…", "…", "…", "…"],\n'
        '  "actualResult": "what actually happens — at least 3 sentences",\n'
        '  "expectedResult": "what should happen — at least 3 sentences",\n'
        '  "additionalContext": "environment, preconditions, impact — at least 4 sentences"\n'
        "}\n\n"
        "Hard requirements (your output is REJECTED if any are violated):\n"
        '- Title must be specific. NEVER use generic phrases like "Bug found" or "Issue with X".\n'
        "- stepsToReproduce MUST have at least 5 entries. If the user gave 1-2 steps, infer "
        "reasonable intermediate steps: open the app, log in with role/creds, navigate to the "
        "screen, perform the action, observe the result. Each step is one clear imperative "
        "action, NO leading numbers or bullets in the strings.\n"
        "- actualResult: minimum 3 full sentences (about 60+ words). Describe what the user "
        "saw, what error or wrong behavior occurred, and any visible symptoms (error messages, "
        "missing UI, wrong data, etc.).\n"
        "- expectedResult: minimum 3 full sentences (about 60+ words). Describe the correct "
        "behavior the user would expect, why it is correct, and what success looks like end "
        "to end.\n"
        "- additionalContext: minimum 4 sentences (about 80+ words). Cover: environment "
        "(browser/device/build), preconditions or test data used, whether it's reproducible "
        "every time, any related symptoms or affected screens, and the impact on users (who "
        "is blocked, how severely).\n"
        "- Do NOT invent product features that aren't in the user's description. If the user "
        "didn't say something, write honestly around what they did say — but still elaborate "
        "on environment, reproducibility, and impact (those are always relevant).\n\n"
        "Example of acceptable length and tone for additionalContext:\n"
        '"Reproduced on Chrome 131 on macOS 14.6 with the staging build deployed on 2026-05-28. '
        "The test account used was a Supervisor role with two assigned sales reps. The issue "
        "reproduces every time the page is refreshed and is not affected by clearing cache or "
        "logging out. Other supervisor screens (Dashboard, Reports) continue to work normally, "
        "which suggests the regression is scoped to the Work With route. Impact: any supervisor "
        'opening Work With cannot see their sales rep list, which blocks daily market planning."\n\n'
        "Return ONLY the JSON object."
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
            '"bugs": "For each bug: 3-4 sentences describing what the bug is, how it manifests, '
            "expected vs actual behavior, and potential user impact. Be specific about severity "
            "and reproducibility. Minimum 80 words total.\","
            if bugs
            else ""
        )
        return (
            "I am a QA engineer. Today I tested the following Jira story:\n"
            f"{story_block}\n{bugs_part}\n{notes_block}\n{attach_block}\n\n"
            "Write a detailed, professional Jira task description. Return ONLY one JSON object "
            "with these exact keys. Every string value must be at least 80 words and read as "
            "rich, complete prose — no terse one-liners.\n"
            "{\n"
            '  "summary": "5-7 sentences describing what the story is about, what specific '
            "functionality or feature I tested, what areas and user flows I covered, the overall "
            'scope of testing, and why this testing was important. Minimum 100 words.",\n'
            '  "details": "5-7 sentences explaining my testing approach: types of testing '
            "performed (functional, regression, edge cases, cross-browser, etc.), specific "
            "scenarios validated, boundary conditions checked, data variations exercised, and "
            'depth of coverage. Minimum 100 words.",\n'
            f"  {bugs_key}\n"
            '  "outcome": "3-4 sentences: final status of testing — did the story pass or fail '
            "QA, how many bugs were found, severity profile, and whether the story is ready for "
            'release or needs another pass. Minimum 60 words."\n'
            "}\n"
            "Return ONLY the JSON object. No prose before or after. No markdown fences."
        )

    if task_type == "testcases":
        return (
            "I am a QA engineer. Today I wrote test cases for the following Jira story:\n"
            f"{story_block}\n{notes_block}\n{attach_block}\n\n"
            "Write a detailed, professional Jira task description. Return ONLY one JSON object. "
            "Every string value must be at least 80 words.\n"
            "{\n"
            '  "summary": "5-7 sentences about the story, what functionality the test cases '
            "cover, and why thorough coverage matters for this feature. Reference specific "
            'features and behaviors from the story description. Minimum 100 words.",\n'
            '  "details": "5-7 sentences explaining the specific test scenarios, user flows, '
            "edge cases, boundary conditions, positive/negative cases, and data-driven "
            'scenarios. Be specific about what each group of test cases validates. Minimum 100 words.",\n'
            '  "outcome": "3-4 sentences: completion status, total number of test cases '
            'created, areas that may still need coverage. Minimum 60 words."\n'
            "}\n"
            "Return ONLY the JSON object. No prose before or after. No markdown fences."
        )

    # task_type == "other"
    bugs_part = (
        f"\nI also found and filed the following {len(bugs)} bug(s):\n{bugs_block}"
        if bugs
        else ""
    )
    bugs_key = (
        '"bugs": "For each bug: 3-4 sentences. What the bug is, how it manifests, expected vs '
        "actual behavior, user impact. Minimum 80 words total.\","
        if bugs
        else ""
    )
    return (
        "I am a QA engineer. Today I did the following QA work:\n"
        f"{user_notes}\n{bugs_part}\n{attach_block}\n\n"
        "Write a detailed, professional Jira task description. Return ONLY one JSON object. "
        "Every string value must be at least 80 words.\n"
        "{\n"
        '  "summary": "5-7 sentences describing the QA work performed, why it matters, and '
        'what product areas it touched. Minimum 100 words.",\n'
        '  "details": "5-7 sentences explaining the approach, methodology, tools used, '
        'specific actions, what was analyzed/reviewed/investigated, and findings. Minimum 100 words.",\n'
        f"  {bugs_key}\n"
        '  "outcome": "3-4 sentences: status, what was accomplished, follow-ups needed, bugs '
        'filed. Minimum 60 words."\n'
        "}\n"
        "Return ONLY the JSON object. No prose before or after. No markdown fences."
    )
