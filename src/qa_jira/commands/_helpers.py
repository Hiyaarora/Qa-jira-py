"""Shared interactive helpers used by the command modules."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx
import questionary
from rich.console import Console

from qa_jira.file_handler import (
    detect_input_type,
    get_file_type_label,
    validate_file,
)
from qa_jira.jira_client import (
    get_required_extra_fields,
    search_epics_in_project,
    search_projects,
    search_users,
)
from qa_jira.models import AttachmentInfo

console = Console()


def pick_user(
    client: httpx.Client, base_url: str, auth: str, label: str
) -> str | None:
    """Returns accountId or None to skip."""
    ans = questionary.confirm(f"Set a {label}?", default=False).ask()
    if not ans:
        return None
    while True:
        query = questionary.text(f"Search {label} by name or email:").ask()
        if query is None:
            return None
        query = query.strip()
        if not query:
            return None
        try:
            users = search_users(client, base_url, auth, query)
        except ValueError as e:
            console.print(f"[yellow]⚠ Search failed: {e}[/yellow]")
            if not questionary.confirm("Try again?", default=True).ask():
                return None
            continue
        if not users:
            console.print(f'[yellow]  ⚠ No users found for "{query}"[/yellow]')
            if not questionary.confirm("Search again?", default=True).ask():
                return None
            continue
        choices: list[Any] = [
            questionary.Choice(
                f"{u.displayName}" + (f" ({u.emailAddress})" if u.emailAddress else ""),
                u.accountId,
            )
            for u in users
        ]
        choices.append(questionary.Choice("Search again", "__again__"))
        choices.append(questionary.Choice(f"Skip — no {label}", None))
        pick = questionary.select(f"Select {label}:", choices=choices).ask()
        if pick is None:
            return None
        if pick == "__again__":
            continue
        return pick


def pick_project(client: httpx.Client, base_url: str, auth: str):
    while True:
        query = questionary.text("Search Jira project/space (partial name):").ask()
        if query is None:  # Ctrl+C / Escape
            raise SystemExit(0)
        query = query.strip()
        if not query:
            console.print("[yellow]  Type a project name to search (e.g. 'AI' or 'HFC')[/yellow]")
            continue
        try:
            projects = search_projects(client, base_url, auth, query)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            if not questionary.confirm("Try again?", default=True).ask():
                raise SystemExit(0)
            continue
        if not projects:
            console.print(f'[yellow]  ⚠ No projects found for "{query}"[/yellow]')
            if not questionary.confirm("Search again?", default=True).ask():
                raise SystemExit(0)
            continue
        choices: list[Any] = [
            questionary.Choice(f"[{p.key}] {p.name}", p) for p in projects
        ]
        choices.append(questionary.Choice("Search again", "__again__"))
        pick = questionary.select("Select project:", choices=choices).ask()
        if pick is None:
            raise SystemExit(0)
        if pick == "__again__":
            continue
        return pick


def pick_epic(
    client: httpx.Client, base_url: str, auth: str, project_key: str, *, optional: bool
):
    if optional:
        ans = questionary.confirm("Link this bug to an epic?", default=False).ask()
        if not ans:
            return None
    while True:
        query = questionary.text("Search epic (partial name, empty to list all):").ask()
        if query is None:
            return None
        query = query.strip()
        try:
            epics = search_epics_in_project(client, base_url, auth, project_key, query)
        except ValueError as e:
            console.print(f"[yellow]⚠ {e}[/yellow]")
            if not questionary.confirm("Try again?", default=True).ask():
                return None
            continue
        if not epics:
            console.print("[yellow]  ⚠ No epics found[/yellow]")
            if not questionary.confirm("Search again?", default=True).ask():
                return None
            continue
        choices: list[Any] = [
            questionary.Choice(f"[{e.key}] {e.summary}", e) for e in epics
        ]
        choices.append(questionary.Choice("Search again", "__again__"))
        if optional:
            choices.append(questionary.Choice("Skip — no epic", None))
        pick = questionary.select("Select epic:", choices=choices).ask()
        if pick is None:
            return None
        if pick == "__again__":
            continue
        return pick


def ask_attachment() -> AttachmentInfo | None:
    raw = questionary.text("Attach file or Google Sheet URL (empty to skip):").ask()
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    kind = detect_input_type(raw)
    if kind == "google-sheet":
        desc = questionary.text(
            "What is this Google Sheet? (e.g. Test Cases, Bug Report, Performance Data):"
        ).ask()
        if desc is None:
            desc = ""
        desc = desc.strip() or "Google Sheet"
        return AttachmentInfo(
            type="google-sheet",
            url=raw.strip("\"'"),
            name=desc,
            label=desc,
        )
    if kind == "file":
        try:
            info = validate_file(raw)
        except ValueError as e:
            console.print(f"[yellow]⚠ {e} — skipping attachment[/yellow]")
            return None
        return AttachmentInfo(
            type="file",
            filePath=info.filePath,
            fileName=info.fileName,
            name=info.fileName,
            label=get_file_type_label(info.ext),
        )
    console.print("[yellow]⚠ Could not identify input — skipping[/yellow]")
    return None


def open_editor(initial_text: str) -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(initial_text)
        path = fh.name
    try:
        subprocess.run([editor, path], check=False)
        return Path(path).read_text(encoding="utf-8")
    finally:
        Path(path).unlink(missing_ok=True)


def prompt_for_required_extra_fields(
    client: httpx.Client,
    base_url: str,
    auth: str,
    project_key: str,
    issue_type_name: str,
) -> dict[str, Any]:
    """Discover required custom fields via createmeta and prompt for each.

    Returns a dict suitable for merging into the Jira `fields` payload.
    """
    try:
        required = get_required_extra_fields(
            client, base_url, auth, project_key, issue_type_name
        )
    except Exception as e:
        console.print(
            f"[yellow]⚠ Could not load required fields metadata: {e}[/yellow]"
        )
        return {}

    if not required:
        return {}

    extra: dict[str, Any] = {}
    console.print(
        f"[dim]  Your Jira project requires {len(required)} additional field(s):[/dim]"
    )
    for f in required:
        name = f["name"]
        allowed = f["allowedValues"]
        schema_type = f["schema_type"]

        if allowed:
            choices = []
            for av in allowed:
                label = (
                    av.get("value")
                    or av.get("name")
                    or av.get("displayName")
                    or str(av.get("id"))
                )
                choices.append(questionary.Choice(str(label), av))
            picked = questionary.select(f"  {name}:", choices=choices).ask()
            value = (
                picked.get("value")
                or picked.get("name")
                or picked.get("id")
            )
            if schema_type == "option":
                extra[f["id"]] = {"value": value}
            elif schema_type == "user":
                extra[f["id"]] = {"accountId": picked.get("accountId") or value}
            elif schema_type == "array":
                extra[f["id"]] = [{"value": value}]
            else:
                extra[f["id"]] = value
        else:
            raw = (questionary.text(f"  {name}:").ask() or "").strip()
            if not raw:
                continue
            if schema_type == "number":
                try:
                    extra[f["id"]] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    extra[f["id"]] = raw
            else:
                extra[f["id"]] = raw

    return extra
