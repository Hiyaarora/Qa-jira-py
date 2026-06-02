from __future__ import annotations

import sys
import webbrowser

import httpx
import questionary
from rich.console import Console

from qa_jira.config import save_config
from qa_jira.jira_client import basic_auth_header
from qa_jira.models import Config

console = Console()

JIRA_BASE_URL = "https://applicate.atlassian.net"
JIRA_TOKEN_URL = "https://id.atlassian.com/manage-profile/security/api-tokens"

PROVIDER_PRESETS: dict[str, dict[str, str | None]] = {
    "anthropic": {
        "label": "Anthropic Claude (paid after small free credit)",
        "key_url": "https://console.anthropic.com/settings/keys",
        "model": "claude-sonnet-4-6",
        "base_url": None,
    },
    "openrouter": {
        "label": "OpenRouter (free models available)",
        "key_url": "https://openrouter.ai/keys",
        "model": "nvidia/nemotron-3-nano-30b-a3b:free",
        "base_url": "https://openrouter.ai/api/v1",
    },
    "openai-compatible": {
        "label": "Other OpenAI-compatible API",
        "key_url": None,
        "model": None,
        "base_url": None,
    },
}


def _validate_jira(email: str, token: str) -> tuple[str, str]:
    auth = basic_auth_header(email, token)
    with httpx.Client(timeout=15) as client:
        resp = client.get(
            f"{JIRA_BASE_URL}/rest/api/3/myself",
            headers={"Authorization": auth, "Accept": "application/json"},
        )
    if resp.status_code == 401:
        raise ValueError("Invalid credentials. Check your email and API token.")
    resp.raise_for_status()
    data = resp.json()
    return data["accountId"], data["displayName"]


def _validate_ai(api_key: str, model: str, base_url: str) -> None:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    payload = {
        "model": model,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": 'Say "ok" only.'}],
    }
    import httpx as _httpx
    with _httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:200]}")


def run() -> None:
    console.print("\n[cyan]  jira setup — Let's get you configured[/cyan]\n")
    console.print(f"  [dim]Jira workspace:[/dim] [cyan]{JIRA_BASE_URL}[/cyan]")

    console.print("\n[dim]Step 1 of 4: Jira email[/dim]")
    while True:
        jira_email_raw = questionary.text("Your Jira account email:").ask()
        if jira_email_raw is None:          # Ctrl+C → exit cleanly
            console.print("[dim]Cancelled.[/dim]")
            sys.exit(0)
        if jira_email_raw.strip():          # not empty → move on
            break
        console.print("[yellow]⚠ Email cannot be empty. Please try again.[/yellow]")
    jira_email = jira_email_raw.strip()

    console.print("\n[dim]Step 2 of 4: Jira API token[/dim]")
    console.print("  Open the Atlassian token page, create a token, then paste it below.")
    try:
        webbrowser.open(JIRA_TOKEN_URL)
    except Exception:
        pass
    jira_token = questionary.password("Paste your Jira API token:").ask()
    if not jira_token:
        sys.exit(1)

    with console.status("Validating Jira credentials..."):
        try:
            account_id, display_name = _validate_jira(jira_email, jira_token)
        except Exception as e:
            console.print(f"[red]✗ {e}[/red]")
            if questionary.confirm("Retry Jira setup?", default=True).ask():
                return run()
            sys.exit(1)
    console.print(f"[green]✔[/green] Jira authenticated — Hello, [white]{display_name}[/white]")

    console.print("\n[dim]Step 3 of 4: AI provider[/dim]")
    provider_choice = questionary.select(
        "Which AI provider?",
        choices=[
            questionary.Choice(PROVIDER_PRESETS["anthropic"]["label"], "anthropic"),
            questionary.Choice(PROVIDER_PRESETS["openrouter"]["label"], "openrouter"),
            questionary.Choice(PROVIDER_PRESETS["openai-compatible"]["label"], "openai-compatible"),
        ],
    ).ask()
    preset = PROVIDER_PRESETS[provider_choice]

    if provider_choice == "openai-compatible":
        ai_base_url = questionary.text("AI base URL (e.g. https://api.example.com/v1):").ask()
        ai_model_default = questionary.text("Model name:").ask()
    else:
        ai_base_url = preset["base_url"]
        ai_model_default = preset["model"]

    console.print("\n[dim]Step 4 of 4: AI API key[/dim]")
    if preset["key_url"]:
        try:
            webbrowser.open(preset["key_url"])
            console.print(f"  [dim]Opened {preset['key_url']}[/dim]")
        except Exception:
            console.print(f"  [dim]Get your key at: {preset['key_url']}[/dim]")
    ai_api_key = questionary.password("Paste your AI API key:").ask()
    ai_model_input = questionary.text(
        f"AI model name (default: {ai_model_default}):",
        default=ai_model_default or "",
    ).ask()
    ai_model = (ai_model_input or "").strip() or ai_model_default

    with console.status("Validating AI key..."):
        try:
            _validate_ai(ai_api_key, ai_model, ai_base_url or "https://openrouter.ai/api/v1")
            console.print("[green]✔[/green] AI key validated")
        except Exception as e:
            console.print(f"[yellow]⚠ Could not validate AI key ({e}) — saving anyway[/yellow]")

    cfg = Config(
        jiraEmail=jira_email,
        jiraApiToken=jira_token,
        jiraBaseUrl=JIRA_BASE_URL,
        accountId=account_id,
        displayName=display_name,
        aiProvider=provider_choice,
        aiApiKey=ai_api_key,
        aiModel=ai_model,
        aiBaseUrl=ai_base_url,
    )
    save_config(cfg)
    console.print("\n[green]✔ Config saved to ~/.qa-jira/config.json[/green]")
    console.print("  Run: [cyan]jira task create[/cyan] to log your first task.\n")
