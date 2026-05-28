from __future__ import annotations

import re
import sys
import time
from datetime import date

import httpx
import questionary
from rich.console import Console

from qa_jira.adf import make_doc, make_paragraph, make_text
from qa_jira.ai import generate_task_description
from qa_jira.ai.base import build_task_result
from qa_jira.commands._helpers import (
    ask_attachment,
    open_editor,
    prompt_for_required_extra_fields,
)
from qa_jira.config import get_config
from qa_jira.jira_client import (
    add_comment_with_link,
    attach_file_to_issue,
    basic_auth_header,
    create_task,
    fetch_issue_details,
    get_epic_info,
    transition_to_done,
)
from qa_jira.models import Issue

console = Console()


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)
    today = date.today().isoformat()

    epic_key_raw = (
        (questionary.text("Which epic? (e.g. QA-247):").ask() or "")
        .strip()
        .upper()
    )
    with httpx.Client(timeout=30) as client:
        with console.status("Validating epic..."):
            try:
                epic = get_epic_info(client, cfg.jiraBaseUrl, auth, epic_key_raw)
            except (ValueError, httpx.HTTPError) as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)
        console.print(
            f"[green]✔[/green] Epic: [cyan]{epic.key}[/cyan] — {epic.summary}"
        )

        task_type = questionary.select(
            "What did you work on today?",
            choices=[
                questionary.Choice("Tested a Jira Story", "tested"),
                questionary.Choice("Wrote Test Cases for a Story", "testcases"),
                questionary.Choice("Other / General QA work", "other"),
            ],
        ).ask()

        story_input = bug_input = user_notes = ""
        if task_type == "tested":
            story_input = (
                questionary.text("Story you tested (key/URL, empty to skip):").ask() or ""
            ).strip()
            bug_input = (
                questionary.text("Bug IDs you filed (comma-separated, empty to skip):").ask() or ""
            ).strip()
            user_notes = (
                questionary.text("Extra notes (empty to skip):").ask() or ""
            ).strip()
        elif task_type == "testcases":
            story_input = (
                questionary.text("Story you wrote test cases for (key/URL, empty to skip):").ask() or ""
            ).strip()
            user_notes = (
                questionary.text("Extra notes (empty to skip):").ask() or ""
            ).strip()
        else:
            user_notes = (
                questionary.text("What did you work on? (brief description):").ask() or ""
            ).strip()
            bug_input = (
                questionary.text("Bug IDs you filed (comma-separated, empty to skip):").ask() or ""
            ).strip()

        attachment = ask_attachment()

        story: Issue | None = None
        if story_input:
            with console.status("Fetching story..."):
                try:
                    story = fetch_issue_details(client, cfg.jiraBaseUrl, auth, story_input)
                    console.print(f"[green]✔[/green] Story: [white]{story.summary}[/white]")
                except ValueError as e:
                    console.print(f"[yellow]⚠ Story fetch failed: {e} — continuing[/yellow]")

        bug_list: list[Issue] = []
        if bug_input:
            for raw_key in [b.strip() for b in bug_input.split(",") if b.strip()]:
                with console.status(f"Fetching bug {raw_key}..."):
                    try:
                        b = fetch_issue_details(client, cfg.jiraBaseUrl, auth, raw_key)
                        bug_list.append(b)
                        console.print(f"[green]✔[/green] Bug: [cyan]{b.key}[/cyan] — {b.summary}")
                    except ValueError as e:
                        console.print(f"[yellow]⚠ {e} — continuing[/yellow]")

        with console.status("🤖 Generating description..."):
            try:
                ai_result = generate_task_description(
                    cfg, task_type, story, bug_list, user_notes, attachment
                )
                console.print("[green]✔[/green] Description generated")
            except Exception as e:
                console.print(f"[yellow]⚠ AI failed: {e}[/yellow]")
                fallback = questionary.text("Enter description manually:").ask() or ""
                ai_result = build_task_result(
                    {"summary": fallback, "details": "", "outcome": "Task completed."},
                    story,
                    bug_list,
                    attachment,
                )

        suggested = (
            (
                f"QA Testing — {story.key}"
                if task_type == "tested"
                else f"Test Case Creation — {story.key}"
            )
            if story
            else f"QA Task — {epic.key} — {today}"
        )
        summary = questionary.text("Task summary:", default=suggested).ask() or suggested

        label_raw = (questionary.text("Label (optional):").ask() or "").strip()
        label = re.sub(r"\s+", "-", label_raw) if label_raw else None

        # Project key derived from epic key (HFC-315 → HFC)
        project_key = epic.key.split("-")[0]
        extra_fields = prompt_for_required_extra_fields(
            client, cfg.jiraBaseUrl, auth, project_key, "Task"
        )

        divider = "─" * 58
        console.print(f"\n[cyan]{divider}[/cyan]")
        console.print("[cyan]  TASK PREVIEW[/cyan]")
        console.print(f"[cyan]{divider}[/cyan]")
        console.print(f"  [dim]Epic:     [/dim]{epic.key} — {epic.summary}")
        console.print(f"  [dim]Summary:  [/dim]{summary}")
        if label:
            console.print(f"  [dim]Label:    [/dim][green]{label}[/green]")
        console.print(f"  [dim]Date:     [/dim]{today}")
        console.print("  [dim]Assignee: [/dim]You (auto-set)")
        if attachment:
            sym = "🔗" if attachment.type == "google-sheet" else "📎"
            console.print(f"  [dim]Attach:   [/dim]{sym} {attachment.name}")
        console.print(f"[cyan]{divider}[/cyan]\n")
        preview = ai_result.preview
        if len(preview) > 500:
            preview = preview[:500] + "..."
        for line in preview.split("\n"):
            console.print(f"  {line}")
        console.print(f"\n[cyan]{divider}[/cyan]\n")

        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Create this task", "create"),
                questionary.Choice("Edit description in $EDITOR", "edit"),
                questionary.Choice("Cancel", "cancel"),
            ],
        ).ask()
        if action == "cancel":
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)

        adf = ai_result.adf
        if action == "edit":
            edited = open_editor(ai_result.preview)
            paragraphs = [p for p in edited.split("\n\n") if p.strip()]
            adf = make_doc([make_paragraph([make_text(p)]) for p in paragraphs])
            console.print("[green]✔[/green] Description updated")

        with console.status("Creating task..."):
            try:
                created = create_task(
                    client,
                    cfg.jiraBaseUrl,
                    auth,
                    epic_key=epic.key,
                    summary=summary,
                    description=adf,
                    label=label,
                    start_date=today,
                    due_date=today,
                    assignee_account_id=cfg.accountId,
                    extra_fields=extra_fields,
                )
            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)

        with console.status("Setting status to Done..."):
            try:
                if transition_to_done(client, cfg.jiraBaseUrl, auth, created.issueKey):
                    console.print("[green]✔[/green] Status set to Done")
            except ValueError as e:
                console.print(f"[yellow]⚠ {e}[/yellow]")

        if attachment and attachment.type == "file" and attachment.filePath:
            with console.status(f"Uploading {attachment.fileName}..."):
                try:
                    attach_file_to_issue(
                        client,
                        cfg.jiraBaseUrl,
                        auth,
                        created.issueKey,
                        attachment.filePath,
                    )
                    console.print(f"[green]✔[/green] {attachment.label} attached")
                except ValueError as e:
                    console.print(f"[yellow]⚠ Upload failed: {e}[/yellow]")
        elif attachment and attachment.type == "google-sheet" and attachment.url:
            try:
                add_comment_with_link(
                    client,
                    cfg.jiraBaseUrl,
                    auth,
                    created.issueKey,
                    "Test Cases (Google Sheet)",
                    attachment.url,
                )
                console.print("[green]✔[/green] Google Sheet link added as comment")
            except ValueError as e:
                console.print(f"[yellow]⚠ Comment failed: {e}[/yellow]")

    elapsed = time.monotonic() - start
    console.print("\n" + "═" * 50)
    console.print(f"[green]  ✅ Created: [/green][bold cyan]{created.issueKey}[/bold cyan]")
    console.print(f"  [dim]🔗 [/dim][cyan underline]{created.issueUrl}[/cyan underline]")
    console.print("═" * 50)
    console.print(f"\n[dim]  Done in {elapsed:.1f}s[/dim]\n")
