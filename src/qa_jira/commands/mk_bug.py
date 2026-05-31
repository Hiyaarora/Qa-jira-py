from __future__ import annotations

import sys
import time

import httpx
import questionary
from rich.console import Console

from qa_jira.adf import make_doc, make_paragraph, make_text
from qa_jira.ai import generate_bug_description
from qa_jira.ai.base import build_bug_result
from qa_jira.commands._helpers import (
    ask_attachment,
    open_editor,
    pick_epic,
    pick_project,
    pick_user,
    prompt_for_required_extra_fields,
)
from qa_jira.config import get_config
from qa_jira.commands._attachment import upload_attachment
from qa_jira.jira_client import (
    basic_auth_header,
    create_bug,
    transition_to_in_progress,
)

console = Console()


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)

    console.print("\n[cyan]  jira mk bug — AI-powered bug creator[/cyan]\n")
    raw_description = questionary.text(
        "Describe the bug (be as detailed as you want):"
    ).ask()
    if not raw_description or not raw_description.strip():
        console.print("[red]Description cannot be empty.[/red]")
        sys.exit(1)

    environment = questionary.select(
        "Environment:",
        choices=["Production", "Demo", "Test"],
    ).ask()

    # Collect image paths — user-attached screenshot (if any)
    image_paths: list[str] = []
    if attachment and attachment.type == "file" and attachment.filePath:
        from qa_jira.ai.http_provider import IMAGE_MIME
        from pathlib import Path as _Path
        if _Path(attachment.filePath).suffix.lower() in IMAGE_MIME:
            image_paths.append(attachment.filePath)

    with console.status("🤖 Structuring bug report..."):
        try:
            bug_ai = generate_bug_description(
                cfg, raw_description, environment, attachment, image_paths or None
            )
            if image_paths:
                console.print("[green]✔[/green] Bug report structured by AI (read your screenshot)")
            else:
                console.print("[green]✔[/green] Bug report structured by AI")
        except Exception as e:
            console.print(f"[yellow]⚠ AI failed: {e} — using manual input[/yellow]")
            bug_ai = build_bug_result({}, raw_description, environment, attachment)

    priority = questionary.select(
        "Priority:",
        choices=[
            questionary.Choice("P1 — Critical / Blocker (Highest)", "P1"),
            questionary.Choice("P2 — Major (High)", "P2"),
            questionary.Choice("P3 — Minor (Medium)", "P3"),
        ],
    ).ask()
    if priority is None:
        console.print("[dim]Cancelled.[/dim]")
        sys.exit(0)

    with httpx.Client(timeout=30) as client:
        assignee_id = pick_user(client, cfg.jiraBaseUrl, auth, "Assignee")
        owner_id = pick_user(client, cfg.jiraBaseUrl, auth, "Issue Owner")
        attachment = ask_attachment()

        project = pick_project(client, cfg.jiraBaseUrl, auth)
        console.print(
            f"[green]✔[/green] Project: [white]{project.name}[/white] ({project.key})"
        )
        epic = pick_epic(client, cfg.jiraBaseUrl, auth, project.key, optional=True)
        if epic:
            console.print(
                f"[green]✔[/green] Epic: [white]{epic.summary}[/white] ({epic.key})"
            )

        extra_fields = prompt_for_required_extra_fields(
            client, cfg.jiraBaseUrl, auth, project.key, "Bug"
        )

        divider = "─" * 58
        console.print(f"\n[cyan]{divider}[/cyan]")
        console.print("[cyan]  BUG PREVIEW[/cyan]")
        console.print(f"[cyan]{divider}[/cyan]")
        console.print(f"  [dim]Title:    [/dim][white]{bug_ai.title}[/white]")
        console.print(f"  [dim]Project:  [/dim]{project.name} ({project.key})")
        if epic:
            console.print(f"  [dim]Epic:     [/dim]{epic.summary} ({epic.key})")
        console.print(f"  [dim]Priority: [/dim][yellow]{priority}[/yellow]")
        console.print(f"  [dim]Environ:  [/dim]{environment}")
        if assignee_id:
            console.print("  [dim]Assignee: [/dim]Selected user")
        if owner_id:
            console.print("  [dim]Owner:    [/dim]Selected user")
        if attachment:
            console.print(f"  [dim]Attach:   [/dim]{attachment.name}")
        console.print(f"[cyan]{divider}[/cyan]\n")
        for line in bug_ai.preview.split("\n"):
            console.print(f"  {line}")
        console.print(f"\n[cyan]{divider}[/cyan]\n")

        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Create this bug", "create"),
                questionary.Choice("Edit description in $EDITOR", "edit"),
                questionary.Choice("Cancel", "cancel"),
            ],
        ).ask()

        if action == "cancel":
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)

        adf = bug_ai.adf
        if action == "edit":
            edited = open_editor(bug_ai.preview)
            paragraphs = [p for p in edited.split("\n\n") if p.strip()]
            adf = make_doc(
                [make_paragraph([make_text(p)]) for p in paragraphs]
            )
            console.print("[green]✔[/green] Description updated")

        with console.status("Creating bug in Jira..."):
            try:
                created = create_bug(
                    client,
                    cfg.jiraBaseUrl,
                    auth,
                    project_key=project.key,
                    epic_key=epic.key if epic else None,
                    summary=bug_ai.title,
                    description=adf,
                    priority=priority,
                    assignee_account_id=assignee_id,
                    issue_owner_account_id=owner_id,
                    environment=environment,
                    extra_fields=extra_fields,
                )
            except (ValueError, httpx.HTTPError) as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)

        if attachment:
            upload_attachment(client, cfg.jiraBaseUrl, auth, created.issueKey, attachment)

        with console.status("Setting status to In Progress..."):
            try:
                if transition_to_in_progress(
                    client, cfg.jiraBaseUrl, auth, created.issueKey
                ):
                    console.print("[green]✔[/green] Status: In Progress")
                else:
                    console.print(
                        "[dim]  (Status left as default — set manually if needed)[/dim]"
                    )
            except Exception:
                pass

    elapsed = time.monotonic() - start
    console.print("\n" + "═" * 50)
    console.print(
        f"[red]  🐛 Bug Created: [/red][bold cyan]{created.issueKey}[/bold cyan]"
    )
    console.print(
        f"  [dim]🔗 [/dim][cyan underline]{created.issueUrl}[/cyan underline]"
    )
    console.print("═" * 50)
    console.print(f"\n[dim]  Done in {elapsed:.1f}s[/dim]\n")
