from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
from rich.console import Console

from qa_jira.commands._helpers import pick_epic, pick_project
from qa_jira.config import get_config
from qa_jira.excel import write_bugsheet
from qa_jira.jira_client import basic_auth_header, fetch_bugs_in_epic

console = Console()


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)

    console.print("\n[cyan]  jira mk bugsheet — Export bugs to Excel[/cyan]\n")

    with httpx.Client(timeout=60) as client:
        project = pick_project(client, cfg.jiraBaseUrl, auth)
        console.print(
            f"[green]✔[/green] Project: [white]{project.name}[/white] ({project.key})"
        )
        epic = pick_epic(
            client, cfg.jiraBaseUrl, auth, project.key, optional=False
        )
        if epic is None:
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)
        console.print(
            f"[green]✔[/green] Epic: [white]{epic.summary}[/white] ({epic.key})"
        )

        with console.status("Fetching bugs from Jira..."):
            try:
                bugs = fetch_bugs_in_epic(client, cfg.jiraBaseUrl, auth, epic.key)
            except ValueError as e:
                console.print(f"[red]✗ Failed to fetch bugs: {e}[/red]")
                sys.exit(1)

    if not bugs:
        console.print(
            f"[yellow]  ⚠ No bugs found in epic {epic.key} — {epic.summary}[/yellow]"
        )
        sys.exit(0)
    console.print(
        f"[green]✔ Found {len(bugs)} bug(s)[/green][dim] — writing sheet...[/dim]"
    )

    out_path = write_bugsheet(bugs=bugs, epic=epic, output_dir=Path.cwd())
    elapsed = time.monotonic() - start

    console.print("\n" + "═" * 58)
    console.print("[green]  ✅ Bug Sheet Created[/green]")
    console.print(f"  [dim]Epic:  [/dim]{epic.key} — {epic.summary}")
    console.print(f"  [dim]Bugs:  [/dim]{len(bugs)} bugs exported")
    console.print(f"  [dim]File:  [/dim][cyan underline]{out_path}[/cyan underline]")
    console.print("═" * 58)
    console.print(f"\n[dim]  Done in {elapsed:.1f}s[/dim]\n")
