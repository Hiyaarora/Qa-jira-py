from __future__ import annotations

import sys

import httpx
import questionary
from rich.console import Console

from qa_jira.config import get_config
from qa_jira.jira_client import (
    basic_auth_header,
    delete_issue,
    extract_issue_key,
    fetch_issue_details,
)

console = Console()


def run(target: str) -> None:
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)

    try:
        key = extract_issue_key(target)
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        sys.exit(1)

    with httpx.Client(timeout=20) as client:
        with console.status("Fetching issue..."):
            try:
                issue = fetch_issue_details(client, cfg.jiraBaseUrl, auth, key)
            except (ValueError, httpx.HTTPError) as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)

            try:
                extra = client.get(
                    f"{cfg.jiraBaseUrl}/rest/api/3/issue/{issue.key}?fields=priority,assignee",
                    headers={"Authorization": auth, "Accept": "application/json"},
                ).json()
                priority = (extra["fields"].get("priority") or {}).get("name") or "None"
                assignee = (
                    (extra["fields"].get("assignee") or {}).get("displayName") or "Unassigned"
                )
            except Exception:
                priority, assignee = "Unknown", "Unassigned"

        divider = "─" * 56
        console.print(f"\n[cyan]{divider}[/cyan]")
        console.print("[cyan]  ISSUE DETAILS[/cyan]")
        console.print(f"[cyan]{divider}[/cyan]")
        console.print(f"  [dim]Key:       [/dim][bold cyan]{issue.key}[/bold cyan]")
        console.print(f"  [dim]Type:      [/dim]{issue.issueType}")
        console.print(f"  [dim]Status:    [/dim]{issue.status}")
        console.print(f"  [dim]Priority:  [/dim]{priority}")
        console.print(f"  [dim]Assignee:  [/dim]{assignee}")
        console.print(f"  [dim]Summary:   [/dim][white]{issue.summary}[/white]")
        if issue.descriptionText.strip():
            preview = issue.descriptionText.strip()[:350]
            if len(issue.descriptionText.strip()) > 350:
                preview += "..."
            console.print(f"[cyan]{divider}[/cyan]")
            console.print("  [dim]Description:[/dim]\n")
            for line in preview.split("\n"):
                console.print(f"  [dim]{line}[/dim]")
        console.print(f"\n[cyan]{divider}[/cyan]\n")
        console.print(
            f"[red]  ⚠  Deleting [bold]{issue.key}[/bold] is permanent and cannot be undone.[/red]\n"
        )

        confirmed = questionary.confirm(
            f'Delete {issue.key} — "{issue.summary[:60]}"?',
            default=False,
        ).ask()
        if not confirmed:
            console.print("\n[dim]  Cancelled. Issue was not deleted.[/dim]\n")
            sys.exit(0)

        with console.status("Deleting..."):
            try:
                delete_issue(client, cfg.jiraBaseUrl, auth, issue.key)
            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                if "permission" in str(e).lower():
                    console.print(
                        '[dim]  Tip: You may need "Delete Issues" permission in this Jira project.[/dim]'
                    )
                sys.exit(1)

    console.print(
        f"[green]✔ Deleted: [/green][cyan]{issue.key}[/cyan][dim] — {issue.summary}[/dim]\n"
    )
