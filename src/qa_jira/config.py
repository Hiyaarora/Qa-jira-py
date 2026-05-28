from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from rich.console import Console

from qa_jira.models import Config

console = Console()

CONFIG_DIR = Path.home() / ".qa-jira"
CONFIG_PATH = CONFIG_DIR / "config.json"


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg.model_dump(), indent=2))
    os.chmod(CONFIG_PATH, 0o600)


def get_config() -> Config:
    if not CONFIG_PATH.exists():
        console.print("[yellow]⚠[/yellow] Run [cyan]jira setup[/cyan] first")
        sys.exit(1)
    data = json.loads(CONFIG_PATH.read_text())
    return Config.model_validate(data)
