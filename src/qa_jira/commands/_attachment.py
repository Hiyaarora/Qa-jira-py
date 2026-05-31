"""Upload file attachments to Jira. Google Sheet URLs are embedded in the ADF description instead."""

from __future__ import annotations

import httpx
from rich.console import Console

from qa_jira.jira_client import attach_file_to_issue
from qa_jira.models import AttachmentInfo

console = Console()


def upload_attachment(
    client: httpx.Client,
    base_url: str,
    auth: str,
    issue_key: str,
    attachment: AttachmentInfo,
) -> None:
    if attachment.type == "file" and attachment.filePath:
        with console.status(f"Uploading {attachment.fileName}..."):
            try:
                attach_file_to_issue(client, base_url, auth, issue_key, attachment.filePath)
                console.print(f"[green]✔[/green] File attached: {attachment.fileName}")
            except ValueError as e:
                console.print(f"[yellow]⚠ Upload failed: {e}[/yellow]")
    # Google Sheet URLs are already embedded in the ADF description — nothing to upload
