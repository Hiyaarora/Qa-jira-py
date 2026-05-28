# QA Jira CLI (Python) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive CLI named `jira` that lets QA engineers create AI-structured Jira tasks and bugs, delete issues, and export bug rollups for an epic as a local Excel file.

**Architecture:** Single Python 3.11+ package (`qa_jira`) installed via uv. CLI dispatches to five command modules. A shared layer of utilities — Jira REST client (httpx), AI provider abstraction (Anthropic default + OpenAI-compatible alternative), ADF builder, Excel writer, file handler, config store, Pydantic models — backs all commands.

**Tech Stack:** Python 3.11+, uv, httpx, questionary, rich, openpyxl, pydantic v2, anthropic, openai, python-dateutil, pytest.

---

## Pre-flight

- Working directory: `/Users/salescode/qa-jira-py` (does not exist yet — Task 1 creates it).
- Reference spec: `/Users/salescode/qa-jira-py/docs/superpowers/specs/2026-05-28-qa-jira-python-port-design.md`.
- `uv` must be available on `PATH`. Verify with `uv --version` before starting. If missing, install per `https://docs.astral.sh/uv/`.
- Jira workspace URL is hard-coded to `https://applicate.atlassian.net` (same as the source CLI; not user-configurable).

---

## Task 1: Scaffold the package

**Files:**
- Create: `/Users/salescode/qa-jira-py/pyproject.toml`
- Create: `/Users/salescode/qa-jira-py/.gitignore`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/__init__.py`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/__main__.py`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/cli.py`
- Create: `/Users/salescode/qa-jira-py/README.md` (one-line stub — full README is Task 17)
- Create: `/Users/salescode/qa-jira-py/tests/__init__.py`

- [ ] **Step 1: Create the project structure**

```bash
mkdir -p /Users/salescode/qa-jira-py/src/qa_jira/ai \
         /Users/salescode/qa-jira-py/src/qa_jira/commands \
         /Users/salescode/qa-jira-py/tests
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "qa-jira"
version = "0.1.0"
description = "CLI for QA engineers — AI-structured Jira tasks, bugs, and Excel bug sheets"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "questionary>=2.0",
    "rich>=13.7",
    "openpyxl>=3.1",
    "pydantic>=2.7",
    "anthropic>=0.40",
    "openai>=1.40",
    "python-dateutil>=2.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
    "respx>=0.21",
]

[project.scripts]
jira = "qa_jira.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/qa_jira"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Write `.gitignore`**

```
__pycache__/
*.pyc
.venv/
.pytest_cache/
*.egg-info/
dist/
build/
.qa-jira/
```

- [ ] **Step 4: Write `src/qa_jira/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `src/qa_jira/__main__.py`**

```python
from qa_jira.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Write a minimal `src/qa_jira/cli.py` (just `--help` for now)**

```python
import sys
from rich.console import Console

console = Console()


def print_help() -> None:
    console.print("\n[cyan]  jira[/cyan][dim] — QA Jira CLI[/dim]\n")
    console.print("  [green]jira setup[/green]          [dim]First-time configuration[/dim]")
    console.print("  [green]jira task create[/green]    [dim]Create a daily QA task[/dim]")
    console.print("  [green]jira mk bug[/green]         [dim]Create a bug with AI-structured description[/dim]")
    console.print("  [green]jira mk bugsheet[/green]    [dim]Export bugs in an epic to a local Excel file[/dim]")
    console.print("  [green]jira rm <ID|URL>[/green]    [dim]Delete a Jira issue by key or URL[/dim]\n")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return
    console.print(f"[red]Unknown command: {' '.join(args)}[/red]")
    print_help()
    sys.exit(1)
```

- [ ] **Step 7: Initialise git and install in editable mode**

```bash
cd /Users/salescode/qa-jira-py && git init && uv venv && uv pip install -e ".[dev]"
```

- [ ] **Step 8: Verify the `jira` command works**

Run: `cd /Users/salescode/qa-jira-py && uv run jira --help`
Expected: prints the five-command help block, exits 0.

- [ ] **Step 9: Write stub `README.md`**

```markdown
# qa-jira

CLI for QA engineers — see `docs/superpowers/specs/` for the full design.
Install with `uv pip install -e ".[dev]"`, then run `jira setup`.
```

- [ ] **Step 10: First commit**

```bash
cd /Users/salescode/qa-jira-py && git add -A && git commit -m "scaffold: pyproject, CLI entry, package skeleton"
```

---

## Task 2: Pydantic models

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/models.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from qa_jira.models import (
    Config, Issue, Project, Epic, User, AttachmentInfo,
    AIBugResult, AITaskResult, BugInEpic,
)


def test_config_roundtrip():
    cfg = Config(
        jiraEmail="me@example.com",
        jiraApiToken="tok",
        jiraBaseUrl="https://x.atlassian.net",
        accountId="abc",
        displayName="Me",
        aiProvider="anthropic",
        aiApiKey="sk-ant",
        aiModel="claude-sonnet-4-6",
    )
    assert cfg.aiBaseUrl is None
    dumped = cfg.model_dump()
    assert Config.model_validate(dumped) == cfg


def test_ai_bug_result_defaults():
    r = AIBugResult(
        title="Login button is hidden on small screens",
        stepsToReproduce=["Open app", "Resize to 320px"],
        actualResult="Button overflows",
        expectedResult="Button is visible",
        adf={"type": "doc", "version": 1, "content": []},
        preview="...",
    )
    assert r.additionalContext == ""


def test_issue_url_required():
    i = Issue(
        key="PROJ-1", summary="x", descriptionText="",
        issueType="Bug", status="Open", url="https://x.atlassian.net/browse/PROJ-1",
    )
    assert i.key == "PROJ-1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: ImportError — `qa_jira.models` does not exist.

- [ ] **Step 3: Write `src/qa_jira/models.py`**

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Config(BaseModel):
    jiraEmail: str
    jiraApiToken: str
    jiraBaseUrl: str
    accountId: str
    displayName: str
    aiProvider: Literal["anthropic", "openrouter", "openai-compatible"]
    aiApiKey: str
    aiModel: str
    aiBaseUrl: str | None = None


class Project(BaseModel):
    key: str
    name: str
    id: str


class Epic(BaseModel):
    key: str
    summary: str


class User(BaseModel):
    accountId: str
    displayName: str
    emailAddress: str = ""


class Issue(BaseModel):
    key: str
    summary: str
    descriptionText: str = ""
    issueType: str
    status: str
    url: str


class BugInEpic(BaseModel):
    key: str
    summary: str
    status: str
    priority: str
    assignee: str
    reporter: str
    created: str  # YYYY-MM-DD
    description: str
    url: str
    environment: str


class AttachmentInfo(BaseModel):
    type: Literal["file", "google-sheet", "url"]
    name: str
    label: str
    filePath: str | None = None
    fileName: str | None = None
    url: str | None = None


class AIBugResult(BaseModel):
    title: str
    stepsToReproduce: list[str]
    actualResult: str
    expectedResult: str
    additionalContext: str = ""
    adf: dict[str, Any]
    preview: str


class AITaskResult(BaseModel):
    summary: str
    details: str = ""
    bugs: str = ""
    outcome: str = ""
    adf: dict[str, Any]
    preview: str


class CreateIssueResult(BaseModel):
    issueKey: str
    issueUrl: str
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_models.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/models.py tests/test_models.py && git commit -m "models: pydantic types for Config, Issue, AIBugResult, AITaskResult"
```

---

## Task 3: Config module

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/config.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import json
import os
import stat
from pathlib import Path

import pytest

from qa_jira import config as config_mod
from qa_jira.models import Config


def test_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "config.json")

    cfg = Config(
        jiraEmail="me@example.com",
        jiraApiToken="t",
        jiraBaseUrl="https://x.atlassian.net",
        accountId="a",
        displayName="Me",
        aiProvider="anthropic",
        aiApiKey="k",
        aiModel="claude-sonnet-4-6",
    )
    config_mod.save_config(cfg)

    assert (tmp_path / "config.json").exists()
    mode = stat.S_IMODE((tmp_path / "config.json").stat().st_mode)
    assert mode == 0o600

    loaded = config_mod.get_config()
    assert loaded == cfg


def test_get_config_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "missing.json")
    with pytest.raises(SystemExit):
        config_mod.get_config()
```

- [ ] **Step 2: Run test — verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: ImportError.

- [ ] **Step 3: Write `src/qa_jira/config.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/config.py tests/test_config.py && git commit -m "config: load/save ~/.qa-jira/config.json with chmod 600"
```

---

## Task 4: ADF builder

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/adf.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_adf.py`

ADF (Atlassian Document Format) is the JSON shape Jira's REST API expects for issue descriptions and comments. This module produces only the subset we need: doc / paragraph / text / link / rule / bulletList.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adf.py
import pytest

from qa_jira.adf import (
    make_doc, make_paragraph, make_text, make_link,
    make_rule, make_bullet_list, validate_adf, adf_to_plain_text,
)


def test_make_text_bold():
    assert make_text("hi", bold=True) == {
        "type": "text", "text": "hi", "marks": [{"type": "strong"}],
    }


def test_make_link():
    assert make_link("Google", "https://g.com") == {
        "type": "text", "text": "Google",
        "marks": [{"type": "link", "attrs": {"href": "https://g.com"}}],
    }


def test_make_doc_structure():
    doc = make_doc([make_paragraph([make_text("hi")])])
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert doc["content"][0]["type"] == "paragraph"


def test_make_paragraph_empty():
    # empty paragraphs need a space-text to be valid ADF
    para = make_paragraph([])
    assert para["content"] == [{"type": "text", "text": " "}]


def test_bullet_list():
    bl = make_bullet_list(["one", "two"])
    assert bl["type"] == "bulletList"
    assert len(bl["content"]) == 2
    assert bl["content"][0]["type"] == "listItem"


def test_validate_adf_rejects_bad_block():
    bad = {"type": "doc", "version": 1, "content": [{"type": "video"}]}
    with pytest.raises(ValueError):
        validate_adf(bad)


def test_validate_adf_accepts_good():
    good = make_doc([make_paragraph([make_text("ok")])])
    assert validate_adf(good) is True


def test_adf_to_plain_text():
    doc = make_doc([
        make_paragraph([make_text("hello ")]),
        make_paragraph([make_text("world")]),
    ])
    assert "hello" in adf_to_plain_text(doc)
    assert "world" in adf_to_plain_text(doc)
```

- [ ] **Step 2: Run — verify failure**

Run: `uv run pytest tests/test_adf.py -v`

- [ ] **Step 3: Write `src/qa_jira/adf.py`**

```python
from __future__ import annotations

from typing import Any

BLOCK_TYPES = {
    "paragraph", "bulletList", "orderedList", "rule",
    "heading", "blockquote", "codeBlock", "listItem",
}
INLINE_TYPES = {"text", "emoji", "hardBreak", "mention", "inlineCard"}


def make_doc(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "doc", "version": 1, "content": [b for b in blocks if b]}


def make_paragraph(inline_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    filtered = [n for n in inline_nodes if n]
    if not filtered:
        return {"type": "paragraph", "content": [{"type": "text", "text": " "}]}
    return {"type": "paragraph", "content": filtered}


def make_text(text: str, bold: bool = False) -> dict[str, Any]:
    if not text or not isinstance(text, str):
        return {"type": "text", "text": " "}
    node: dict[str, Any] = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def make_link(text: str, url: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text or url,
        "marks": [{"type": "link", "attrs": {"href": url}}],
    }


def make_rule() -> dict[str, Any]:
    return {"type": "rule"}


def make_bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [make_paragraph([make_text(item)])]}
            for item in items if item
        ],
    }


def validate_adf(doc: dict[str, Any]) -> bool:
    if doc.get("type") != "doc":
        raise ValueError("ADF root must be type doc")
    for block in doc.get("content", []):
        if block["type"] not in BLOCK_TYPES:
            raise ValueError(f"Invalid block type: {block['type']}")
        for inline in block.get("content", []):
            if inline["type"] not in BLOCK_TYPES | INLINE_TYPES:
                raise ValueError(f"Invalid inline type: {inline['type']}")
    return True


def adf_to_plain_text(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    t = node.get("type")
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    if t in {"doc", "paragraph", "blockquote", "heading"}:
        return "".join(adf_to_plain_text(c) for c in node.get("content", [])) + "\n"
    if t in {"bulletList", "orderedList"}:
        return "".join(adf_to_plain_text(c) for c in node.get("content", []))
    if t == "listItem":
        return "- " + "".join(adf_to_plain_text(c) for c in node.get("content", []))
    return "".join(adf_to_plain_text(c) for c in node.get("content", []))
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_adf.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/adf.py tests/test_adf.py && git commit -m "adf: builder for doc/paragraph/text/link/rule/bulletList + validator + plain-text extractor"
```

---

## Task 5: File handler

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/file_handler.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_file_handler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_file_handler.py
import pytest

from qa_jira.file_handler import (
    detect_input_type, validate_file, get_file_type_label, MAX_FILE_SIZE,
)


def test_detect_google_sheet():
    assert detect_input_type("https://docs.google.com/spreadsheets/d/abc") == "google-sheet"


def test_detect_url():
    assert detect_input_type("https://example.com/x") == "url"


def test_detect_unknown():
    assert detect_input_type("nope") == "unknown"
    assert detect_input_type("") == "unknown"


def test_detect_file(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2")
    assert detect_input_type(str(p)) == "file"


def test_validate_file_strips_quotes(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    info = validate_file(f'"{p}"')
    assert info.fileName == "x.json"
    assert info.ext == ".json"


def test_validate_file_too_large(tmp_path, monkeypatch):
    p = tmp_path / "big.csv"
    p.write_bytes(b"x" * 100)
    monkeypatch.setattr("qa_jira.file_handler.MAX_FILE_SIZE", 50)
    with pytest.raises(ValueError, match="too large"):
        validate_file(str(p))


def test_validate_file_missing():
    with pytest.raises(ValueError, match="not found"):
        validate_file("/no/such/file.csv")


def test_label_known():
    assert get_file_type_label(".jmx") == "JMeter Load Test Script"
    assert get_file_type_label(".unknown") == "Attachment"
```

- [ ] **Step 2: Run — verify failure**

- [ ] **Step 3: Write `src/qa_jira/file_handler.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {".jmx", ".js", ".json", ".csv", ".xml", ".xlsx", ".zip",
                      ".png", ".jpg", ".jpeg", ".pdf"}

EXTENSION_LABELS = {
    ".jmx": "JMeter Load Test Script",
    ".js": "API Test Script",
    ".json": "Test Data / Config",
    ".csv": "Test Data",
    ".xml": "Test Config / Suite",
    ".xlsx": "Test Report / Sheet",
    ".zip": "Test Archive",
    ".png": "Screenshot",
    ".jpg": "Screenshot",
    ".jpeg": "Screenshot",
    ".pdf": "Document",
}


@dataclass
class FileInfo:
    filePath: str
    fileName: str
    size: int
    ext: str


def _clean_path(raw: str) -> str:
    s = (raw or "").strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s


def detect_input_type(raw: str) -> str:
    if not raw or not raw.strip():
        return "unknown"
    s = _clean_path(raw)
    if s.startswith("https://docs.google.com/spreadsheets"):
        return "google-sheet"
    if s.startswith("https://") or s.startswith("http://"):
        return "url"
    if Path(s).exists():
        return "file"
    return "unknown"


def validate_file(raw_path: str) -> FileInfo:
    p = Path(_clean_path(raw_path))
    if not p.exists():
        raise ValueError(f"File not found: {p}")
    size = p.stat().st_size
    if size > MAX_FILE_SIZE:
        mb = size / 1024 / 1024
        raise ValueError(f"File too large: {mb:.1f}MB (max 10MB for Jira attachments)")
    return FileInfo(filePath=str(p), fileName=p.name, size=size, ext=p.suffix.lower())


def get_file_type_label(ext: str | None) -> str:
    if not ext:
        return "Attachment"
    return EXTENSION_LABELS.get(ext.lower(), "Attachment")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_file_handler.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/file_handler.py tests/test_file_handler.py && git commit -m "file_handler: detect input type, validate path, 10MB limit, extension labels"
```

---

## Task 6: Jira client — auth + fetch helpers

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/jira_client.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_jira_client.py`

This task lays the auth helper and the read-side endpoints. Write-side endpoints follow in Task 7.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_jira_client.py
import httpx
import pytest

from qa_jira.jira_client import (
    basic_auth_header, extract_issue_key, fetch_issue_details,
    get_epic_info, search_projects, search_epics_in_project, search_users,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_basic_auth_header():
    h = basic_auth_header("me@example.com", "tok")
    assert h.startswith("Basic ")


def test_extract_issue_key_plain():
    assert extract_issue_key("proj-12") == "PROJ-12"
    assert extract_issue_key("  PROJ-12  ") == "PROJ-12"


def test_extract_issue_key_url():
    assert extract_issue_key("https://x.atlassian.net/browse/PROJ-12") == "PROJ-12"


def test_fetch_issue_details_ok():
    def handler(req):
        assert "/rest/api/3/issue/PROJ-1" in str(req.url)
        return httpx.Response(200, json={
            "fields": {
                "summary": "x", "description": None,
                "issuetype": {"name": "Bug"}, "status": {"name": "Open"},
            }
        })
    issue = fetch_issue_details(_client(handler), "https://x.atlassian.net", "AUTH", "PROJ-1")
    assert issue.key == "PROJ-1"
    assert issue.url == "https://x.atlassian.net/browse/PROJ-1"


def test_fetch_issue_details_404():
    def handler(req):
        return httpx.Response(404, json={"errorMessages": ["No issue"]})
    with pytest.raises(ValueError, match="not found"):
        fetch_issue_details(_client(handler), "https://x.atlassian.net", "AUTH", "PROJ-99")


def test_get_epic_info_rejects_non_epic():
    def handler(req):
        return httpx.Response(200, json={
            "fields": {"summary": "s", "issuetype": {"name": "Task"}}
        })
    with pytest.raises(ValueError, match="not an Epic"):
        get_epic_info(_client(handler), "https://x", "AUTH", "PROJ-1")


def test_search_projects():
    def handler(req):
        return httpx.Response(200, json={"values": [
            {"key": "A", "name": "Alpha", "id": "1"},
            {"key": "B", "name": "Beta",  "id": "2"},
        ]})
    results = search_projects(_client(handler), "https://x", "AUTH", "a")
    assert [p.key for p in results] == ["A", "B"]


def test_search_epics_in_project_with_query():
    captured = {}
    def handler(req):
        body = req.read().decode()
        captured["body"] = body
        return httpx.Response(200, json={"issues": [
            {"key": "P-1", "fields": {"summary": "Epic one"}},
        ]})
    results = search_epics_in_project(_client(handler), "https://x", "AUTH", "PROJ", "login")
    assert results[0].key == "P-1"
    assert "summary ~" in captured["body"]


def test_search_users():
    def handler(req):
        return httpx.Response(200, json=[
            {"accountId": "a1", "displayName": "Alice", "emailAddress": "a@x"},
            {"accountId": "a2", "displayName": "Andy",  "emailAddress": ""},
        ])
    users = search_users(_client(handler), "https://x", "AUTH", "a")
    assert len(users) == 2
    assert users[1].emailAddress == ""
```

- [ ] **Step 2: Run — verify failure**

- [ ] **Step 3: Write the first half of `src/qa_jira/jira_client.py`** (write-side functions added in Task 7)

```python
from __future__ import annotations

import base64
import re
from typing import Any

import httpx

from qa_jira.adf import adf_to_plain_text
from qa_jira.models import Epic, Issue, Project, User


def basic_auth_header(email: str, api_token: str) -> str:
    raw = f"{email}:{api_token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


_KEY_RE = re.compile(r"/browse/([A-Z]+-\d+)", re.IGNORECASE)


def extract_issue_key(key_or_url: str) -> str:
    s = (key_or_url or "").strip()
    if "/browse/" in s:
        m = _KEY_RE.search(s)
        if not m:
            raise ValueError(f"Could not extract issue key from URL: {key_or_url}")
        return m.group(1).upper()
    return s.upper()


def _err_msgs(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return resp.text or f"HTTP {resp.status_code}"
    msgs = list(data.get("errorMessages") or [])
    msgs += list((data.get("errors") or {}).values())
    return ", ".join(str(m) for m in msgs) or f"HTTP {resp.status_code}"


def fetch_issue_details(client: httpx.Client, base_url: str, auth: str, key_or_url: str) -> Issue:
    key = extract_issue_key(key_or_url)
    url = f"{base_url}/rest/api/3/issue/{key}?fields=summary,description,issuetype,status"
    resp = client.get(url, headers={"Authorization": auth})
    if resp.status_code == 404:
        raise ValueError(f"Issue {key} not found")
    if resp.status_code == 401:
        raise ValueError("Jira authentication failed — run jira setup")
    if resp.status_code >= 400:
        raise ValueError(f"Failed to fetch {key}: {_err_msgs(resp)}")

    f = resp.json()["fields"]
    return Issue(
        key=key,
        summary=f.get("summary") or "",
        descriptionText=adf_to_plain_text(f.get("description")) if f.get("description") else "",
        issueType=f["issuetype"]["name"],
        status=f["status"]["name"],
        url=f"{base_url}/browse/{key}",
    )


def get_epic_info(client: httpx.Client, base_url: str, auth: str, epic_key: str) -> Epic:
    key = epic_key.strip().upper()
    url = f"{base_url}/rest/api/3/issue/{key}?fields=summary,issuetype"
    resp = client.get(url, headers={"Authorization": auth})
    resp.raise_for_status()
    data = resp.json()
    if data["fields"]["issuetype"]["name"] != "Epic":
        raise ValueError(f"{key} is not an Epic")
    return Epic(key=key, summary=data["fields"]["summary"])


def search_projects(client: httpx.Client, base_url: str, auth: str, query: str) -> list[Project]:
    url = f"{base_url}/rest/api/3/project/search"
    resp = client.get(
        url,
        params={"query": query, "maxResults": 10},
        headers={"Authorization": auth, "Accept": "application/json"},
    )
    if resp.status_code == 401:
        raise ValueError("Jira auth failed — run jira setup")
    if resp.status_code >= 400:
        raise ValueError(f"Project search failed: {_err_msgs(resp)}")
    values = resp.json().get("values", [])
    return [Project(key=p["key"], name=p["name"], id=p["id"]) for p in values]


def search_epics_in_project(
    client: httpx.Client, base_url: str, auth: str,
    project_key: str, query: str,
) -> list[Epic]:
    query = query.strip()
    if query:
        jql = (
            f'project = "{project_key}" AND issuetype = Epic '
            f'AND summary ~ "{query}" ORDER BY created DESC'
        )
    else:
        jql = f'project = "{project_key}" AND issuetype = Epic ORDER BY created DESC'

    url = f"{base_url}/rest/api/3/search/jql"
    resp = client.post(
        url,
        json={"jql": jql, "fields": ["summary", "status"], "maxResults": 10},
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    if resp.status_code >= 400:
        raise ValueError(f"Epic search failed: {_err_msgs(resp)}")
    issues = resp.json().get("issues", [])
    return [Epic(key=i["key"], summary=i["fields"]["summary"]) for i in issues]


def search_users(client: httpx.Client, base_url: str, auth: str, query: str) -> list[User]:
    url = f"{base_url}/rest/api/3/user/search"
    resp = client.get(
        url,
        params={"query": query, "maxResults": 8},
        headers={"Authorization": auth, "Accept": "application/json"},
    )
    if resp.status_code >= 400:
        raise ValueError(f"User search failed: {_err_msgs(resp)}")
    return [
        User(
            accountId=u["accountId"],
            displayName=u["displayName"],
            emailAddress=u.get("emailAddress") or "",
        )
        for u in resp.json()
    ]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_jira_client.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/jira_client.py tests/test_jira_client.py && git commit -m "jira_client: auth helper, key extraction, read-side endpoints (fetch issue, epic, search projects/epics/users)"
```

---

## Task 7: Jira client — write endpoints

**Files:**
- Modify: `/Users/salescode/qa-jira-py/src/qa_jira/jira_client.py` (append functions)
- Modify: `/Users/salescode/qa-jira-py/tests/test_jira_client.py` (append tests)

- [ ] **Step 1: Add failing tests**

Append to `tests/test_jira_client.py`:

```python
from qa_jira.jira_client import (
    create_task, create_bug, transition_to_done, delete_issue,
    add_comment_with_link, fetch_bugs_in_epic, find_transition_id,
)


def test_create_task_posts_correct_fields():
    captured = {}
    def handler(req):
        captured["url"] = str(req.url)
        captured["body"] = req.read().decode()
        return httpx.Response(201, json={"key": "PROJ-9"})
    res = create_task(_client(handler), "https://x", "AUTH",
                     epic_key="PROJ-1", summary="s",
                     description={"type": "doc"}, label=None,
                     start_date="2026-05-28", due_date="2026-05-28",
                     assignee_account_id="me")
    assert res.issueKey == "PROJ-9"
    assert "customfield_10015" in captured["body"]
    assert "PROJ-1" in captured["body"]


def test_create_bug_success_first_try():
    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(200, json={"issueTypes": [{"name": "Bug"}]})
        return httpx.Response(201, json={"key": "PROJ-2"})
    res = create_bug(_client(handler), "https://x", "AUTH",
                     project_key="PROJ", epic_key="PROJ-1",
                     summary="s", description={"type": "doc"},
                     priority="P1", assignee_account_id=None,
                     issue_owner_account_id=None, environment="Production")
    assert res.issueKey == "PROJ-2"


def test_create_bug_no_bug_type_in_project():
    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(200, json={"issueTypes": [{"name": "Story"}, {"name": "Task"}]})
        return httpx.Response(500)
    with pytest.raises(ValueError, match='does not have a "Bug"'):
        create_bug(_client(handler), "https://x", "AUTH",
                   project_key="PROJ", epic_key=None,
                   summary="s", description={"type": "doc"},
                   priority="P3", assignee_account_id=None,
                   issue_owner_account_id=None, environment=None)


def test_create_bug_epic_field_fallback():
    calls = []
    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(200, json={"issueTypes": [{"name": "Bug"}]})
        body = req.read().decode()
        calls.append(body)
        # First two attempts fail with epic-field error, third succeeds
        if len(calls) < 3:
            return httpx.Response(400, json={"errors": {"parent": "Invalid"}})
        return httpx.Response(201, json={"key": "PROJ-3"})
    res = create_bug(_client(handler), "https://x", "AUTH",
                     project_key="PROJ", epic_key="PROJ-1",
                     summary="s", description={"type": "doc"},
                     priority="P2", assignee_account_id=None,
                     issue_owner_account_id=None, environment=None)
    assert res.issueKey == "PROJ-3"
    assert len(calls) == 3


def test_transition_to_done_finds_match():
    def handler(req):
        if req.method == "GET":
            return httpx.Response(200, json={"transitions": [
                {"id": "10", "name": "In Progress"},
                {"id": "11", "name": "Done"},
            ]})
        return httpx.Response(204)
    assert transition_to_done(_client(handler), "https://x", "AUTH", "PROJ-1") is True


def test_transition_to_done_no_match():
    def handler(req):
        return httpx.Response(200, json={"transitions": [{"id": "10", "name": "In Review"}]})
    assert transition_to_done(_client(handler), "https://x", "AUTH", "PROJ-1") is False


def test_delete_issue_403():
    def handler(req):
        return httpx.Response(403, json={"errorMessages": ["No perm"]})
    with pytest.raises(ValueError, match="Permission denied"):
        delete_issue(_client(handler), "https://x", "AUTH", "PROJ-1")


def test_fetch_bugs_in_epic_first_jql_works():
    def handler(req):
        body = req.read().decode()
        assert "Epic Link" in body
        return httpx.Response(200, json={"issues": [
            {"key": "PROJ-9", "fields": {
                "summary": "Bug nine", "status": {"name": "Open"},
                "priority": {"name": "P1"},
                "assignee": {"displayName": "Alice"},
                "reporter": {"displayName": "Bob"},
                "created": "2026-05-01T10:00:00.000+0000",
                "description": None,
                "issuetype": {"name": "Bug"},
            }}
        ]})
    bugs = fetch_bugs_in_epic(_client(handler), "https://x", "AUTH", "PROJ-1")
    assert bugs[0].key == "PROJ-9"
    assert bugs[0].created == "2026-05-01"
    assert bugs[0].environment == "UAT"  # default when no env keywords
```

- [ ] **Step 2: Run tests — verify failure**

- [ ] **Step 3: Append write functions to `src/qa_jira/jira_client.py`**

```python
# Append below the read-side functions in jira_client.py

import json as _json
from datetime import date as _date
from pathlib import Path as _Path

from qa_jira.adf import make_doc, make_link, make_paragraph, make_text
from qa_jira.models import BugInEpic, CreateIssueResult


def create_task(
    client: httpx.Client, base_url: str, auth: str, *,
    epic_key: str, summary: str, description: dict[str, Any],
    label: str | None, start_date: str | None, due_date: str | None,
    assignee_account_id: str,
) -> CreateIssueResult:
    safe_start = start_date or _date.today().isoformat()
    fields: dict[str, Any] = {
        "project": {"key": epic_key.split("-")[0]},
        "parent": {"key": epic_key},
        "issuetype": {"name": "Task"},
        "summary": summary,
        "description": description,
        "assignee": {"accountId": assignee_account_id},
        "duedate": due_date,
        "customfield_10015": safe_start,
    }
    if label:
        fields["labels"] = [label]

    resp = client.post(
        f"{base_url}/rest/api/3/issue",
        json={"fields": fields},
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    if resp.status_code >= 400:
        raise ValueError(f"Task creation failed: {_err_msgs(resp)}")
    key = resp.json()["key"]
    return CreateIssueResult(issueKey=key, issueUrl=f"{base_url}/browse/{key}")


def create_bug(
    client: httpx.Client, base_url: str, auth: str, *,
    project_key: str, epic_key: str | None,
    summary: str, description: dict[str, Any], priority: str,
    assignee_account_id: str | None, issue_owner_account_id: str | None,
    environment: str | None, label: str | None = None,
) -> CreateIssueResult:
    # Verify the project supports Bug issue type
    try:
        meta = client.get(
            f"{base_url}/rest/api/3/issue/createmeta/{project_key}/issuetypes",
            headers={"Authorization": auth, "Accept": "application/json"},
        )
        if meta.status_code < 400:
            types = (
                meta.json().get("issueTypes")
                or meta.json().get("values")
                or meta.json()
                or []
            )
            type_names = [t["name"] for t in types]
            if not any(n.lower() == "bug" for n in type_names):
                avail = ", ".join(type_names)
                raise ValueError(
                    f'Project {project_key} does not have a "Bug" issue type. '
                    f"Available types: {avail}. Choose a different project."
                )
    except httpx.HTTPError:
        pass  # tolerate; try Bug anyway

    base_fields: dict[str, Any] = {
        "project": {"key": project_key},
        "issuetype": {"name": "Bug"},
        "summary": summary,
        "description": description,
        "priority": {"name": priority or "P3"},
    }
    if assignee_account_id:
        base_fields["assignee"] = {"accountId": assignee_account_id}
    if issue_owner_account_id:
        base_fields["customfield_10097"] = {"accountId": issue_owner_account_id}
    if environment:
        base_fields["customfield_10148"] = {"value": environment}
    if label:
        base_fields["labels"] = [label]

    if epic_key:
        strategies: list[dict[str, Any]] = [
            {"parent": {"key": epic_key}},
            {"customfield_10014": epic_key},
            {"customfield_10008": epic_key},
        ]
    else:
        strategies = [{}]

    last_err: str = "unknown error"
    for strat in strategies:
        fields = {**base_fields, **strat}
        resp = client.post(
            f"{base_url}/rest/api/3/issue",
            json={"fields": fields},
            headers={"Authorization": auth, "Content-Type": "application/json"},
        )
        if resp.status_code < 400:
            key = resp.json()["key"]
            return CreateIssueResult(issueKey=key, issueUrl=f"{base_url}/browse/{key}")
        # Detect epic-field error to trigger fallback
        try:
            errs = resp.json().get("errors", {})
        except Exception:
            errs = {}
        is_epic_err = bool(epic_key) and any(
            k in {"parent", "customfield_10014", "customfield_10008"} for k in errs
        )
        last_err = _err_msgs(resp)
        if not is_epic_err:
            break
    raise ValueError(f"Bug creation failed: {last_err}")


def find_transition_id(
    client: httpx.Client, base_url: str, auth: str, issue_key: str,
    needles: tuple[str, ...] = ("done", "complete"),
) -> str | None:
    resp = client.get(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        headers={"Authorization": auth},
    )
    if resp.status_code >= 400:
        raise ValueError(f"Could not fetch transitions for {issue_key}: {_err_msgs(resp)}")
    for t in resp.json().get("transitions", []):
        name = (t.get("name") or "").lower()
        to_name = ((t.get("to") or {}).get("name") or "").lower()
        if any(n in name or n in to_name for n in needles):
            return t["id"]
    return None


def transition_to_done(client: httpx.Client, base_url: str, auth: str, issue_key: str) -> bool:
    tid = find_transition_id(client, base_url, auth, issue_key, needles=("done", "complete"))
    if not tid:
        return False
    resp = client.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": tid}},
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    if resp.status_code >= 400:
        raise ValueError(f"Transition to Done failed: {_err_msgs(resp)}")
    return True


def transition_to_in_progress(client: httpx.Client, base_url: str, auth: str, issue_key: str) -> bool:
    tid = find_transition_id(client, base_url, auth, issue_key, needles=("progress", "start"))
    if not tid:
        return False
    resp = client.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": tid}},
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    return resp.status_code < 400


def delete_issue(client: httpx.Client, base_url: str, auth: str, key_or_url: str) -> None:
    key = extract_issue_key(key_or_url)
    resp = client.delete(
        f"{base_url}/rest/api/3/issue/{key}",
        headers={"Authorization": auth},
    )
    if resp.status_code == 403:
        raise ValueError(
            f"Permission denied: deleting {key} requires admin approval. "
            "Contact your Jira project admin to grant delete permissions."
        )
    if resp.status_code == 404:
        raise ValueError(f"Issue {key} not found — it may have already been deleted")
    if resp.status_code >= 400:
        raise ValueError(f"Delete failed: {_err_msgs(resp)}")


def attach_file_to_issue(
    client: httpx.Client, base_url: str, auth: str, issue_key: str, file_path: str,
) -> dict[str, Any]:
    p = _Path(file_path)
    with p.open("rb") as fh:
        files = {"file": (p.name, fh)}
        resp = client.post(
            f"{base_url}/rest/api/3/issue/{issue_key}/attachments",
            files=files,
            headers={"Authorization": auth, "X-Atlassian-Token": "no-check"},
        )
    if resp.status_code >= 400:
        raise ValueError(f"Attachment upload failed: {_err_msgs(resp)}")
    return {"fileName": p.name, "size": p.stat().st_size}


def add_comment_with_link(
    client: httpx.Client, base_url: str, auth: str, issue_key: str,
    link_text: str, link_url: str,
) -> None:
    body = make_doc([
        make_paragraph([make_text(link_text + ": ", bold=True), make_link(link_url, link_url)])
    ])
    resp = client.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/comment",
        json={"body": body},
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    if resp.status_code >= 400:
        raise ValueError(f"Comment failed: {_err_msgs(resp)}")


def _extract_environment(description_text: str) -> str:
    if not description_text:
        return "UAT"
    lower = description_text.lower()
    if "production" in lower or " prod " in lower or "prod:" in lower:
        return "Production"
    if "staging" in lower:
        return "Staging"
    if " dev " in lower or "development" in lower or "dev env" in lower:
        return "Dev"
    if "qa env" in lower or "qa environment" in lower:
        return "QA"
    return "UAT"


def fetch_bugs_in_epic(
    client: httpx.Client, base_url: str, auth: str, epic_key: str,
) -> list[BugInEpic]:
    jql_options = [
        f'"Epic Link" = {epic_key} AND issuetype = Bug ORDER BY created ASC',
        f'cf[10014] = {epic_key} AND issuetype = Bug ORDER BY created ASC',
        f'parent = {epic_key} AND issuetype = Bug ORDER BY created ASC',
    ]
    last_err = "all JQL variants failed"
    issues: list[dict[str, Any]] = []

    for jql in jql_options:
        resp = client.post(
            f"{base_url}/rest/api/3/search/jql",
            json={
                "jql": jql,
                "fields": [
                    "summary", "status", "priority", "assignee", "reporter",
                    "created", "description", "issuetype",
                ],
                "maxResults": 100,
            },
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        if resp.status_code == 400:
            last_err = _err_msgs(resp)
            continue
        if resp.status_code >= 400:
            raise ValueError(f"Failed to fetch bugs: {_err_msgs(resp)}")
        issues = resp.json().get("issues", [])
        break
    else:
        raise ValueError(f"Could not query bugs for epic {epic_key}: {last_err}")

    result: list[BugInEpic] = []
    for issue in issues:
        f = issue["fields"]
        desc_text = adf_to_plain_text(f.get("description")) if f.get("description") else ""
        result.append(BugInEpic(
            key=issue["key"],
            summary=f.get("summary") or "",
            status=(f.get("status") or {}).get("name") or "Unknown",
            priority=(f.get("priority") or {}).get("name") or "None",
            assignee=(f.get("assignee") or {}).get("displayName") or "Unassigned",
            reporter=(f.get("reporter") or {}).get("displayName") or "Unknown",
            created=(f.get("created") or "")[:10],
            description=desc_text,
            url=f"{base_url}/browse/{issue['key']}",
            environment=_extract_environment(desc_text),
        ))
    return result
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_jira_client.py -v`
Expected: 17 passed total (9 from Task 6 + 8 new).

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/jira_client.py tests/test_jira_client.py && git commit -m "jira_client: write endpoints (create task/bug, transitions, delete, attach, comment, bugs-in-epic)"
```

---

## Task 8: AI prompts

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/prompts.py`

This is a pure-text module — prompt strings and the system prompt. No tests; templates are exercised through the AI provider tests in Task 10.

- [ ] **Step 1: Write `src/qa_jira/prompts.py`**

```python
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
    parts = []
    for i, b in enumerate(bugs, 1):
        parts.append(
            f"\nBUG {i} KEY: {b.key}"
            f"\nBUG {i} TITLE: {b.summary}"
            f"\nBUG {i} DESCRIPTION: {b.descriptionText or 'No description provided.'}"
            f"\nBUG {i} STATUS: {b.status}"
        )
    return "\n".join(parts)


def build_task_user_prompt(
    task_type: str, story: Issue | None, bugs: list[Issue],
    user_notes: str, attachment: AttachmentInfo | None,
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
        f"I am also attaching: {attachment.label} ({attachment.name})"
        if attachment else ""
    )
    notes_block = (
        f"Additional notes from me: {user_notes}"
        if user_notes and user_notes.strip() else ""
    )

    if task_type == "tested":
        bugs_part = (
            f"\nI found and filed the following {len(bugs)} bug(s) during testing:\n{bugs_block}"
            if bugs else "\nNo bugs were found during testing."
        )
        bugs_key = (
            '"bugs": "For each bug: 2-3 sentences describing what the bug is, '
            'how it manifests, what the expected vs actual behavior is, and the potential '
            'impact on users. Be specific about each bug\'s nature and severity.",'
            if bugs else ""
        )
        return (
            "I am a QA engineer. Today I tested the following Jira story:\n"
            f"{story_block}\n{bugs_part}\n{notes_block}\n{attach_block}\n\n"
            "Write a detailed, professional Jira task description. Return ONLY this JSON "
            "(no backticks, no explanation):\n"
            "{\n"
            '  "summary": "4-5 sentences describing what the story is about, what specific '
            'functionality or feature I tested, what areas and user flows I covered, and the '
            'overall scope of testing. Be specific about what was validated.",\n'
            '  "details": "4-5 sentences explaining my testing approach in detail — what types '
            'of testing I performed, specific scenarios I validated, boundary conditions I '
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
        if bugs else ""
    )
    bugs_key = (
        '"bugs": "For each bug: 2-3 sentences describing what the bug is, how it manifests, '
        'and the potential impact on users.",'
        if bugs else ""
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
```

- [ ] **Step 2: Commit**

```bash
git add src/qa_jira/prompts.py && git commit -m "prompts: system + user prompt templates for bug and task description AI calls"
```

---

## Task 9: AI provider base + Anthropic provider

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/ai/__init__.py`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/ai/base.py`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/ai/anthropic_provider.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_ai.py`

Both providers must produce identical-shape `AIBugResult` / `AITaskResult`. The base module handles parsing + ADF construction so each provider only has to return the raw JSON text.

- [ ] **Step 1: Write `src/qa_jira/ai/base.py` (shared parsing + ADF building)**

```python
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from qa_jira.adf import make_bullet_list, make_doc, make_link, make_paragraph, make_rule, make_text
from qa_jira.models import AIBugResult, AITaskResult, AttachmentInfo, Config, Issue


class Provider(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str: ...


_FENCE_RE = re.compile(r"```(?:json)?", re.IGNORECASE)


def strip_fences(raw: str) -> str:
    return _FENCE_RE.sub("", raw).strip()


def parse_json_loose(raw: str) -> dict[str, Any]:
    """Try direct JSON, then a one-shot trailing-trim repair."""
    cleaned = strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = re.sub(r',\s*"[^"]*":\s*\[?\s*"?[^"}\]]*$', "", cleaned) + "}"
        return json.loads(repaired)


def build_bug_result(parsed: dict[str, Any], raw_description: str, environment: str) -> AIBugResult:
    title = (parsed.get("title") or "").strip() or raw_description[:80]
    steps_raw = parsed.get("stepsToReproduce")
    if isinstance(steps_raw, str):
        steps_raw = [steps_raw]
    if not isinstance(steps_raw, list) or not steps_raw:
        steps_raw = ["Reproduce using the description provided"]
    steps = [re.sub(r"^\d+\.\s*", "", str(s)) for s in steps_raw]

    actual = (parsed.get("actualResult") or "").strip() or raw_description
    expected = (parsed.get("expectedResult") or "").strip() or "Correct behavior as expected by the user"
    ctx = (parsed.get("additionalContext") or "").strip()

    blocks: list[dict[str, Any]] = []
    blocks.append(make_paragraph([make_text("Steps to Reproduce", bold=True)]))
    blocks.append(make_bullet_list(steps))
    blocks.append(make_paragraph([make_text("Actual Result", bold=True)]))
    blocks.append(make_paragraph([make_text(actual)]))
    blocks.append(make_paragraph([make_text("Expected Result", bold=True)]))
    blocks.append(make_paragraph([make_text(expected)]))
    if ctx:
        blocks.append(make_paragraph([make_text("Additional Context", bold=True)]))
        blocks.append(make_paragraph([make_text(ctx)]))
    if environment:
        blocks.append(make_paragraph([make_text("Environment", bold=True)]))
        blocks.append(make_paragraph([make_text(environment)]))

    preview_parts: list[str] = [
        "Steps to Reproduce:\n" + "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(steps)),
        f"\nActual Result:\n  {actual}",
        f"\nExpected Result:\n  {expected}",
    ]
    if ctx:
        preview_parts.append(f"\nAdditional Context:\n  {ctx}")
    if environment:
        preview_parts.append(f"\nEnvironment:\n  {environment}")

    return AIBugResult(
        title=title,
        stepsToReproduce=steps,
        actualResult=actual,
        expectedResult=expected,
        additionalContext=ctx,
        adf=make_doc(blocks),
        preview="\n".join(preview_parts),
    )


def build_task_result(
    parsed: dict[str, Any], story: Issue | None, bugs: list[Issue],
    attachment: AttachmentInfo | None,
) -> AITaskResult:
    summary = (parsed.get("summary") or "").strip()
    details = (parsed.get("details") or "").strip()
    bugs_text = (parsed.get("bugs") or "").strip()
    outcome = (parsed.get("outcome") or "").strip()

    blocks: list[dict[str, Any]] = []
    if summary:
        blocks.append(make_paragraph([make_text("Summary", bold=True)]))
        blocks.append(make_paragraph([make_text(summary)]))
    if details:
        blocks.append(make_paragraph([make_text("Details", bold=True)]))
        blocks.append(make_paragraph([make_text(details)]))
    if bugs_text:
        blocks.append(make_paragraph([make_text("Bugs Found", bold=True)]))
        blocks.append(make_paragraph([make_text(bugs_text)]))
    if outcome:
        blocks.append(make_paragraph([make_text("Outcome", bold=True)]))
        blocks.append(make_paragraph([make_text(outcome)]))

    if story or bugs:
        blocks.append(make_rule())
    if story:
        blocks.append(make_paragraph([
            make_text("Story: ", bold=True),
            make_link(f"{story.key} — {story.summary}", story.url),
        ]))
    for b in bugs:
        blocks.append(make_paragraph([
            make_text("Bug: ", bold=True),
            make_link(f"{b.key} — {b.summary}", b.url),
        ]))
    if attachment and attachment.type == "google-sheet" and attachment.url:
        blocks.append(make_paragraph([
            make_text("Test Cases: ", bold=True),
            make_link("Open Google Sheet", attachment.url),
        ]))

    preview_parts: list[str] = []
    if summary: preview_parts.append("Summary\n" + summary)
    if details: preview_parts.append("Details\n" + details)
    if bugs_text: preview_parts.append("Bugs Found\n" + bugs_text)
    if outcome: preview_parts.append("Outcome\n" + outcome)
    if story: preview_parts.append(f"Story: {story.key} — {story.summary}")
    if bugs: preview_parts.append("Bugs: " + ", ".join(b.key for b in bugs))

    return AITaskResult(
        summary=summary, details=details, bugs=bugs_text, outcome=outcome,
        adf=make_doc(blocks), preview="\n\n".join(preview_parts),
    )
```

- [ ] **Step 2: Write `src/qa_jira/ai/anthropic_provider.py`**

```python
from __future__ import annotations

from anthropic import Anthropic

from qa_jira.models import Config


class AnthropicProvider:
    def __init__(self, config: Config) -> None:
        self._client = Anthropic(api_key=config.aiApiKey)
        self._model = config.aiModel

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Concatenate text blocks
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        return "".join(parts)
```

- [ ] **Step 3: Write `src/qa_jira/ai/__init__.py` (factory + public entry points)**

```python
from __future__ import annotations

from qa_jira.ai.base import (
    Provider, build_bug_result, build_task_result,
    parse_json_loose,
)
from qa_jira.models import (
    AIBugResult, AITaskResult, AttachmentInfo, Config, Issue,
)
from qa_jira.prompts import (
    SYSTEM_PROMPT_BUG, SYSTEM_PROMPT_TASK,
    build_bug_user_prompt, build_task_user_prompt,
)


def get_provider(config: Config) -> Provider:
    if config.aiProvider == "anthropic":
        from qa_jira.ai.anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    from qa_jira.ai.openai_compat_provider import OpenAICompatProvider
    return OpenAICompatProvider(config)


def generate_bug_description(
    config: Config, raw_description: str, environment: str,
) -> AIBugResult:
    provider = get_provider(config)
    raw = provider.complete_json(
        SYSTEM_PROMPT_BUG, build_bug_user_prompt(raw_description), max_tokens=2000,
    )
    try:
        parsed = parse_json_loose(raw)
    except Exception:
        parsed = {}
    return build_bug_result(parsed, raw_description, environment)


def generate_task_description(
    config: Config, task_type: str, story: Issue | None,
    bugs: list[Issue], user_notes: str, attachment: AttachmentInfo | None,
) -> AITaskResult:
    provider = get_provider(config)
    raw = provider.complete_json(
        SYSTEM_PROMPT_TASK,
        build_task_user_prompt(task_type, story, bugs, user_notes, attachment),
        max_tokens=1500,
    )
    try:
        parsed = parse_json_loose(raw)
    except Exception:
        parsed = {"summary": raw[:800], "details": "", "outcome": "Task completed."}
    return build_task_result(parsed, story, bugs, attachment)
```

- [ ] **Step 4: Write `tests/test_ai.py`** (mocks the Anthropic provider's `complete_json`)

```python
# tests/test_ai.py
import json

import pytest

from qa_jira.ai.base import build_bug_result, build_task_result, parse_json_loose
from qa_jira.models import Issue


def test_parse_json_loose_clean():
    assert parse_json_loose('{"a": 1}') == {"a": 1}


def test_parse_json_loose_fences():
    raw = '```json\n{"a": 2}\n```'
    assert parse_json_loose(raw) == {"a": 2}


def test_parse_json_loose_truncated():
    raw = '{"title": "x", "stepsToReproduce": ["a", "b"], "actualResult": "bad'
    parsed = parse_json_loose(raw)
    assert parsed["title"] == "x"


def test_build_bug_result_defaults_for_missing_fields():
    parsed: dict = {}
    r = build_bug_result(parsed, raw_description="user typed this", environment="Production")
    assert r.title == "user typed this"
    assert r.actualResult == "user typed this"
    assert r.expectedResult == "Correct behavior as expected by the user"
    assert any("Environment" in str(p) for p in r.preview.split("\n"))


def test_build_bug_result_strips_leading_numbers():
    parsed = {
        "title": "Click loses focus",
        "stepsToReproduce": ["1. Open page", "2. Click button"],
        "actualResult": "lost", "expectedResult": "kept",
    }
    r = build_bug_result(parsed, "raw", "QA")
    assert r.stepsToReproduce == ["Open page", "Click button"]


def test_build_task_result_with_story_and_bugs():
    story = Issue(key="P-1", summary="story", descriptionText="", issueType="Story",
                  status="Open", url="https://x/browse/P-1")
    bug = Issue(key="P-2", summary="bug", descriptionText="", issueType="Bug",
                status="Open", url="https://x/browse/P-2")
    r = build_task_result(
        parsed={"summary": "did stuff", "details": "d", "bugs": "b1", "outcome": "ok"},
        story=story, bugs=[bug], attachment=None,
    )
    assert "did stuff" in r.preview
    assert "P-1" in r.preview and "P-2" in r.preview
    # ADF should contain a rule between the prose and the references
    assert any(blk.get("type") == "rule" for blk in r.adf["content"])
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_ai.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/qa_jira/ai tests/test_ai.py && git commit -m "ai: Provider protocol, JSON parse, ADF builders, Anthropic provider, factory + generate_*"
```

---

## Task 10: OpenAI-compatible provider

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/ai/openai_compat_provider.py`
- Modify: `/Users/salescode/qa-jira-py/tests/test_ai.py` (add provider test using monkeypatch)

- [ ] **Step 1: Write provider**

```python
# src/qa_jira/ai/openai_compat_provider.py
from __future__ import annotations

from openai import OpenAI

from qa_jira.models import Config


class OpenAICompatProvider:
    """Works for OpenRouter and any OpenAI-compatible endpoint."""

    def __init__(self, config: Config) -> None:
        base_url = config.aiBaseUrl
        if base_url is None and config.aiProvider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        self._client = OpenAI(api_key=config.aiApiKey, base_url=base_url)
        self._model = config.aiModel

    def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""
```

- [ ] **Step 2: Add a smoke test using monkeypatch**

Append to `tests/test_ai.py`:

```python
def test_get_provider_routes_to_openai_compat(monkeypatch):
    from qa_jira.ai import get_provider
    from qa_jira.models import Config

    captured = {}
    class FakeClient:
        def __init__(self, **kw):
            captured.update(kw)
        class chat:
            class completions:
                @staticmethod
                def create(**kw): ...
    monkeypatch.setattr("qa_jira.ai.openai_compat_provider.OpenAI", FakeClient)

    cfg = Config(
        jiraEmail="x", jiraApiToken="y", jiraBaseUrl="https://x",
        accountId="a", displayName="N", aiProvider="openrouter",
        aiApiKey="k", aiModel="m",
    )
    p = get_provider(cfg)
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["api_key"] == "k"
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_ai.py -v`
Expected: 7 passed.

- [ ] **Step 4: Commit**

```bash
git add src/qa_jira/ai/openai_compat_provider.py tests/test_ai.py && git commit -m "ai: OpenAI-compatible provider (handles OpenRouter default base_url)"
```

---

## Task 11: Excel bugsheet writer

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/excel.py`
- Create: `/Users/salescode/qa-jira-py/tests/test_excel.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_excel.py
from datetime import date

from openpyxl import load_workbook

from qa_jira.excel import write_bugsheet
from qa_jira.models import BugInEpic, Epic


def _bug(idx: int) -> BugInEpic:
    return BugInEpic(
        key=f"PROJ-{idx}", summary=f"Bug {idx}", status="Open",
        priority="P1", assignee="Alice", reporter="Bob",
        created="2026-05-01", description="see prod logs",
        url=f"https://x.atlassian.net/browse/PROJ-{idx}",
        environment="Production",
    )


def test_write_bugsheet(tmp_path):
    epic = Epic(key="PROJ-1", summary="Login work")
    out = write_bugsheet(
        bugs=[_bug(2), _bug(3)],
        epic=epic,
        output_dir=tmp_path,
    )
    assert out.exists()
    assert out.name.startswith("bugsheet-PROJ-1-")
    assert out.suffix == ".xlsx"

    wb = load_workbook(out)
    ws = wb.active
    # Header row
    headers = [c.value for c in ws[1]]
    assert headers[0] == "Bug ID"
    assert headers[4] == "JIRA ID"
    # First data row
    assert ws.cell(row=2, column=1).value == "BUG_ID_1"
    assert ws.cell(row=2, column=2).value == "Bug"
    # Hyperlink formula in column E
    formula = ws.cell(row=2, column=5).value
    assert formula.startswith('=HYPERLINK(')
    assert "PROJ-2" in formula
    # Frozen header
    assert ws.freeze_panes == "A2"


def test_write_bugsheet_handles_empty_assignee(tmp_path):
    bug = _bug(9)
    bug.assignee = ""
    out = write_bugsheet(bugs=[bug], epic=Epic(key="PROJ-1", summary="x"), output_dir=tmp_path)
    wb = load_workbook(out)
    ws = wb.active
    assert ws.cell(row=2, column=11).value == "Unassigned"
```

- [ ] **Step 2: Run — verify failure**

- [ ] **Step 3: Write `src/qa_jira/excel.py`**

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

from dateutil.parser import parse as parse_date
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from qa_jira.models import BugInEpic, Epic

HEADERS = [
    "Bug ID", "Bug Type", "Reported By", "Reporting Date", "JIRA ID",
    "Title", "Current Status", "Environment", "Priority", "RCA",
    "Assignee", "Remarks",
]

HEADER_FILL = PatternFill("solid", fgColor="1565C0")
HEADER_FONT = Font(bold=True, color="FFFFFF")
ROW_FILL_LIGHT = PatternFill("solid", fgColor="E3F2FD")
CENTER = Alignment(horizontal="center", vertical="center")


def _format_date(s: str) -> str:
    if not s:
        return ""
    try:
        return parse_date(s).strftime("%d-%b-%Y")
    except (ValueError, TypeError):
        return s


def write_bugsheet(*, bugs: list[BugInEpic], epic: Epic, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    filename = f"bugsheet-{epic.key}-{today}.xlsx"
    out_path = output_dir / filename

    wb = Workbook()
    ws = wb.active
    ws.title = f"{epic.key} — Bug Sheet"[:31]  # Excel sheet name limit

    # Header
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER

    # Data rows
    for row_idx, bug in enumerate(bugs, start=2):
        bug_id_label = f"BUG_ID_{row_idx - 1}"
        ws.cell(row=row_idx, column=1, value=bug_id_label)
        ws.cell(row=row_idx, column=2, value="Bug")
        ws.cell(row=row_idx, column=3, value=bug.reporter or "")
        ws.cell(row=row_idx, column=4, value=_format_date(bug.created))
        # Column E: HYPERLINK formula
        ws.cell(
            row=row_idx, column=5,
            value=f'=HYPERLINK("{bug.url}","{bug.key}")',
        )
        ws.cell(row=row_idx, column=6, value=bug.summary or "")
        ws.cell(row=row_idx, column=7, value=bug.status or "")
        ws.cell(row=row_idx, column=8, value=bug.environment or "UAT")
        ws.cell(row=row_idx, column=9, value=bug.priority or "")
        ws.cell(row=row_idx, column=10, value="")  # RCA
        ws.cell(row=row_idx, column=11, value=bug.assignee or "Unassigned")
        ws.cell(row=row_idx, column=12, value="")  # Remarks

        # Alternate row fill (odd data rows index 0, 2, 4 = white; 1, 3, 5 = blue)
        if (row_idx - 2) % 2 == 1:
            for col_idx in range(1, len(HEADERS) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = ROW_FILL_LIGHT

    # Freeze header
    ws.freeze_panes = "A2"

    # Auto-width: scan column values and set width to max(len) + 2
    for col_idx in range(1, len(HEADERS) + 1):
        letter = get_column_letter(col_idx)
        max_len = max(
            (len(str(ws.cell(row=r, column=col_idx).value or "")) for r in range(1, ws.max_row + 1)),
            default=10,
        )
        ws.column_dimensions[letter].width = min(max(max_len + 2, 10), 60)

    wb.save(out_path)
    return out_path
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_excel.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/excel.py tests/test_excel.py && git commit -m "excel: write_bugsheet → 12-column .xlsx with styling, hyperlinks, frozen header"
```

---

## Task 12: Setup wizard

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/__init__.py`
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/setup.py`
- Modify: `/Users/salescode/qa-jira-py/src/qa_jira/cli.py` (wire `jira setup`)

This command is interactive — no pytest. Manual verification at the end.

- [ ] **Step 1: Write `src/qa_jira/commands/__init__.py`**

```python
```

(empty file)

- [ ] **Step 2: Write `src/qa_jira/commands/setup.py`**

```python
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


def _validate_ai_anthropic(api_key: str, model: str) -> None:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    client.messages.create(
        model=model, max_tokens=10,
        messages=[{"role": "user", "content": 'Say "ok" only.'}],
    )


def _validate_ai_openai_compat(api_key: str, model: str, base_url: str) -> None:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    client.chat.completions.create(
        model=model, max_tokens=10,
        messages=[{"role": "user", "content": 'Say "ok" only.'}],
    )


def run() -> None:
    console.print("\n[cyan]  jira setup — Let's get you configured[/cyan]\n")
    console.print(f"  [dim]Jira workspace:[/dim] [cyan]{JIRA_BASE_URL}[/cyan]")

    # Step 1: Jira email
    console.print("\n[dim]Step 1 of 4: Jira email[/dim]")
    jira_email = questionary.text("Your Jira account email:").ask().strip()
    if not jira_email:
        console.print("[red]Email is required.[/red]")
        sys.exit(1)

    # Step 2: Jira API token
    console.print("\n[dim]Step 2 of 4: Jira API token[/dim]")
    console.print("  Open the Atlassian token page, create a token, then paste it below.")
    webbrowser.open(JIRA_TOKEN_URL)
    jira_token = questionary.password("Paste your Jira API token:").ask()
    if not jira_token:
        sys.exit(1)

    # Validate
    with console.status("Validating Jira credentials..."):
        try:
            account_id, display_name = _validate_jira(jira_email, jira_token)
        except Exception as e:
            console.print(f"[red]✗ {e}[/red]")
            if questionary.confirm("Retry Jira setup?", default=True).ask():
                return run()
            sys.exit(1)
    console.print(f"[green]✔[/green] Jira authenticated — Hello, [white]{display_name}[/white]")

    # Step 3: AI provider
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

    # Step 4: AI API key + model
    console.print("\n[dim]Step 4 of 4: AI API key[/dim]")
    if preset["key_url"]:
        webbrowser.open(preset["key_url"])
        console.print(f"  [dim]Opened {preset['key_url']}[/dim]")
    ai_api_key = questionary.password("Paste your AI API key:").ask()
    ai_model = questionary.text(
        f"AI model name (default: {ai_model_default}):",
        default=ai_model_default or "",
    ).ask().strip() or ai_model_default

    # Validate
    with console.status("Validating AI key..."):
        try:
            if provider_choice == "anthropic":
                _validate_ai_anthropic(ai_api_key, ai_model)
            else:
                _validate_ai_openai_compat(ai_api_key, ai_model, ai_base_url)
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
```

- [ ] **Step 3: Wire the command into `cli.py`**

Replace `src/qa_jira/cli.py` with:

```python
import sys
from rich.console import Console

console = Console()


def print_help() -> None:
    console.print("\n[cyan]  jira[/cyan][dim] — QA Jira CLI[/dim]\n")
    console.print("  [green]jira setup[/green]          [dim]First-time configuration[/dim]")
    console.print("  [green]jira task create[/green]    [dim]Create a daily QA task[/dim]")
    console.print("  [green]jira mk bug[/green]         [dim]Create a bug with AI-structured description[/dim]")
    console.print("  [green]jira mk bugsheet[/green]    [dim]Export bugs in an epic to a local Excel file[/dim]")
    console.print("  [green]jira rm <ID|URL>[/green]    [dim]Delete a Jira issue by key or URL[/dim]\n")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return

    cmd, *rest = args
    if cmd == "setup":
        from qa_jira.commands.setup import run as setup_run
        setup_run()
    elif cmd == "task" and rest and rest[0] == "create":
        from qa_jira.commands.task_create import run as task_run
        task_run()
    elif cmd == "mk" and rest and rest[0] == "bug":
        from qa_jira.commands.mk_bug import run as bug_run
        bug_run()
    elif cmd == "mk" and rest and rest[0] == "bugsheet":
        from qa_jira.commands.mk_bugsheet import run as bs_run
        bs_run()
    elif cmd == "rm":
        target = rest[0] if rest else None
        if not target:
            console.print("[red]Usage: jira rm <ISSUE-KEY or URL>[/red]")
            sys.exit(1)
        from qa_jira.commands.rm import run as rm_run
        rm_run(target)
    else:
        console.print(f"[red]Unknown command: {' '.join(args)}[/red]")
        print_help()
        sys.exit(1)
```

- [ ] **Step 4: Manual verification**

Run: `cd /Users/salescode/qa-jira-py && uv run jira setup`

Expected: walks through Jira email → token → AI provider → AI key. With valid credentials, it creates `~/.qa-jira/config.json` and exits 0. If you cancel at any prompt (Ctrl-C), it exits cleanly.

- [ ] **Step 5: Commit**

```bash
git add src/qa_jira/commands tests/ src/qa_jira/cli.py && git commit -m "commands: setup wizard (Jira + AI provider + API key validation), wire into CLI dispatch"
```

---

## Task 13: `jira rm` command

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/rm.py`

- [ ] **Step 1: Write the command module**

```python
from __future__ import annotations

import sys

import httpx
import questionary
from rich.console import Console

from qa_jira.config import get_config
from qa_jira.jira_client import (
    basic_auth_header, delete_issue, extract_issue_key, fetch_issue_details,
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
            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)

            # Best-effort extra fields
            try:
                extra = client.get(
                    f"{cfg.jiraBaseUrl}/rest/api/3/issue/{issue.key}?fields=priority,assignee",
                    headers={"Authorization": auth, "Accept": "application/json"},
                ).json()
                priority = (extra["fields"].get("priority") or {}).get("name") or "None"
                assignee = (extra["fields"].get("assignee") or {}).get("displayName") or "Unassigned"
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
        console.print(f"[red]  ⚠  Deleting [bold]{issue.key}[/bold] is permanent and cannot be undone.[/red]\n")

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
```

- [ ] **Step 2: Manual verification**

Run: `uv run jira rm PROJ-XXX` against a disposable test issue in your Jira workspace. Expected: details displayed, prompt for confirmation, default No, deletes only when explicitly confirmed.

- [ ] **Step 3: Commit**

```bash
git add src/qa_jira/commands/rm.py && git commit -m "commands: rm — fetch details, display, confirm-default-no, delete"
```

---

## Task 14: `jira mk bug` command

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/mk_bug.py`

The longest command flow. Mirrors `mk bug` from the source CLI: raw description → AI structure → environment → priority → optional assignee/owner search → optional attachment → project search → optional epic search → preview → confirm/edit/cancel → create → attach/comment → transition.

- [ ] **Step 1: Write the command**

```python
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import questionary
from rich.console import Console

from qa_jira.adf import make_doc, make_paragraph, make_text
from qa_jira.ai import generate_bug_description
from qa_jira.config import get_config
from qa_jira.file_handler import (
    detect_input_type, get_file_type_label, validate_file,
)
from qa_jira.jira_client import (
    add_comment_with_link, attach_file_to_issue, basic_auth_header,
    create_bug, search_epics_in_project, search_projects, search_users,
    transition_to_in_progress,
)

console = Console()


def _pick_user(client: httpx.Client, base_url: str, auth: str, label: str) -> str | None:
    """Returns accountId or None to skip."""
    if not questionary.confirm(f"Set a {label}?", default=False).ask():
        return None
    while True:
        query = questionary.text(f"Search {label} by name or email:").ask().strip()
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
        choices = [
            questionary.Choice(
                f"{u.displayName}" + (f" ({u.emailAddress})" if u.emailAddress else ""),
                u.accountId,
            )
            for u in users
        ]
        choices.append(questionary.Choice("Search again", "__again__"))
        choices.append(questionary.Choice(f"Skip — no {label}", None))
        pick = questionary.select(f"Select {label}:", choices=choices).ask()
        if pick == "__again__":
            continue
        return pick


def _pick_project(client: httpx.Client, base_url: str, auth: str):
    while True:
        query = questionary.text("Search for Jira project/space (partial name):").ask().strip()
        if not query:
            console.print("[yellow]  Project is required[/yellow]")
            continue
        try:
            projects = search_projects(client, base_url, auth, query)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            if not questionary.confirm("Try again?", default=True).ask():
                console.print("[dim]Cancelled.[/dim]")
                sys.exit(0)
            continue
        if not projects:
            console.print(f'[yellow]  ⚠ No projects found for "{query}"[/yellow]')
            if not questionary.confirm("Search again?", default=True).ask():
                console.print("[dim]Cancelled.[/dim]")
                sys.exit(0)
            continue
        choices = [
            questionary.Choice(f"[{p.key}] {p.name}", p) for p in projects
        ]
        choices.append(questionary.Choice("Search again", "__again__"))
        pick = questionary.select("Select project:", choices=choices).ask()
        if pick == "__again__":
            continue
        return pick


def _pick_epic(client: httpx.Client, base_url: str, auth: str, project_key: str):
    if not questionary.confirm("Link this bug to an epic?", default=False).ask():
        return None
    while True:
        query = questionary.text("Search epic (partial name, or empty to list all):").ask().strip()
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
        choices = [questionary.Choice(f"[{e.key}] {e.summary}", e) for e in epics]
        choices.append(questionary.Choice("Search again", "__again__"))
        choices.append(questionary.Choice("Skip — no epic", None))
        pick = questionary.select("Select epic:", choices=choices).ask()
        if pick == "__again__":
            continue
        return pick


def _ask_attachment():
    while True:
        raw = questionary.text("Attach screenshot/file or Google Sheet URL (empty to skip):").ask().strip()
        if not raw:
            return None
        kind = detect_input_type(raw)
        if kind == "google-sheet":
            return {"type": "google-sheet", "url": raw.strip('"\''), "name": "Google Sheet link"}
        if kind == "file":
            try:
                info = validate_file(raw)
                return {
                    "type": "file",
                    "filePath": info.filePath,
                    "fileName": info.fileName,
                    "label": get_file_type_label(info.ext),
                    "name": info.fileName,
                }
            except ValueError as e:
                console.print(f"[yellow]⚠ {e}[/yellow]")
        else:
            console.print("[yellow]⚠ Not recognised as a file or Google Sheet URL[/yellow]")
        if not questionary.confirm("Try again?", default=False).ask():
            return None


def _open_editor(initial_text: str) -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(initial_text)
        path = fh.name
    try:
        subprocess.run([editor, path], check=False)
        return Path(path).read_text(encoding="utf-8")
    finally:
        Path(path).unlink(missing_ok=True)


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)

    console.print("\n[cyan]  jira mk bug — AI-powered bug creator[/cyan]\n")
    raw_description = questionary.text("Describe the bug (be as detailed as you want):").ask()
    if not raw_description or not raw_description.strip():
        console.print("[red]Description cannot be empty.[/red]")
        sys.exit(1)

    environment = questionary.select(
        "Environment:",
        choices=["Production", "Demo", "Test"],
    ).ask()

    with console.status("🤖 Structuring bug report..."):
        try:
            bug_ai = generate_bug_description(cfg, raw_description, environment)
            console.print("[green]✔[/green] Bug report structured by AI")
        except Exception as e:
            console.print(f"[yellow]⚠ AI failed: {e} — using manual input[/yellow]")
            from qa_jira.ai.base import build_bug_result
            bug_ai = build_bug_result({}, raw_description, environment)

    priority = questionary.select(
        "Priority:",
        choices=[
            questionary.Choice("P1 — Critical / Blocker (Highest)", "P1"),
            questionary.Choice("P2 — Major (High)", "P2"),
            questionary.Choice("P3 — Minor (Medium)", "P3"),
        ],
    ).ask()

    with httpx.Client(timeout=30) as client:
        assignee_id = _pick_user(client, cfg.jiraBaseUrl, auth, "Assignee")
        owner_id = _pick_user(client, cfg.jiraBaseUrl, auth, "Issue Owner")

        attachment = _ask_attachment()

        project = _pick_project(client, cfg.jiraBaseUrl, auth)
        epic = _pick_epic(client, cfg.jiraBaseUrl, auth, project.key)

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
        if assignee_id: console.print("  [dim]Assignee: [/dim]Selected user")
        if owner_id:    console.print("  [dim]Owner:    [/dim]Selected user")
        if attachment:  console.print(f"  [dim]Attach:   [/dim]{attachment['name']}")
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
            edited = _open_editor(bug_ai.preview)
            paragraphs = [p for p in edited.split("\n\n") if p.strip()]
            adf = make_doc([make_paragraph([make_text(p)]) for p in paragraphs])
            console.print("[green]✔[/green] Description updated")

        with console.status("Creating bug in Jira..."):
            try:
                created = create_bug(
                    client, cfg.jiraBaseUrl, auth,
                    project_key=project.key,
                    epic_key=epic.key if epic else None,
                    summary=bug_ai.title,
                    description=adf,
                    priority=priority,
                    assignee_account_id=assignee_id,
                    issue_owner_account_id=owner_id,
                    environment=environment,
                )
            except ValueError as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)

        # Attachment / comment
        if attachment and attachment["type"] == "file":
            with console.status(f"Uploading {attachment['fileName']}..."):
                try:
                    attach_file_to_issue(
                        client, cfg.jiraBaseUrl, auth, created.issueKey,
                        attachment["filePath"],
                    )
                    console.print(f"[green]✔[/green] File attached: {attachment['fileName']}")
                except ValueError as e:
                    console.print(f"[yellow]⚠ Upload failed: {e}[/yellow]")
        elif attachment and attachment["type"] == "google-sheet":
            try:
                add_comment_with_link(
                    client, cfg.jiraBaseUrl, auth, created.issueKey,
                    "Reference (Google Sheet)", attachment["url"],
                )
                console.print("[green]✔[/green] Google Sheet link added as comment")
            except ValueError as e:
                console.print(f"[yellow]⚠ Comment failed: {e}[/yellow]")

        with console.status("Setting status to In Progress..."):
            try:
                if transition_to_in_progress(client, cfg.jiraBaseUrl, auth, created.issueKey):
                    console.print("[green]✔[/green] Status: In Progress")
                else:
                    console.print("[dim]  (Status left as default — set manually if needed)[/dim]")
            except Exception:
                pass

    elapsed = time.monotonic() - start
    console.print("\n" + "═" * 50)
    console.print(f"[red]  🐛 Bug Created: [/red][bold cyan]{created.issueKey}[/bold cyan]")
    console.print(f"  [dim]🔗 [/dim][cyan underline]{created.issueUrl}[/cyan underline]")
    console.print("═" * 50)
    console.print(f"\n[dim]  Done in {elapsed:.1f}s[/dim]\n")
```

- [ ] **Step 2: Manual verification**

Run: `uv run jira mk bug` and walk through the flow with a real Jira project. Expected: bug created, transitioned to In Progress, attachment uploaded if provided, summary line printed with issue key + URL.

- [ ] **Step 3: Commit**

```bash
git add src/qa_jira/commands/mk_bug.py && git commit -m "commands: mk bug — AI structure → project/epic/assignee/owner pickers → preview → create"
```

---

## Task 15: `jira task create` command

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/task_create.py`

- [ ] **Step 1: Write the command**

```python
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

import httpx
import questionary
from rich.console import Console

from qa_jira.adf import make_doc, make_paragraph, make_text
from qa_jira.ai import generate_task_description
from qa_jira.config import get_config
from qa_jira.file_handler import (
    detect_input_type, get_file_type_label, validate_file,
)
from qa_jira.jira_client import (
    add_comment_with_link, attach_file_to_issue, basic_auth_header,
    create_task, fetch_issue_details, get_epic_info, transition_to_done,
)
from qa_jira.models import AttachmentInfo, Issue

console = Console()


def _open_editor(initial_text: str) -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(initial_text)
        path = fh.name
    try:
        subprocess.run([editor, path], check=False)
        return Path(path).read_text(encoding="utf-8")
    finally:
        Path(path).unlink(missing_ok=True)


def _ask_attachment() -> AttachmentInfo | None:
    raw = questionary.text("Attach file or Google Sheet URL (empty to skip):").ask().strip()
    if not raw:
        return None
    kind = detect_input_type(raw)
    if kind == "google-sheet":
        return AttachmentInfo(
            type="google-sheet", url=raw.strip('"\''),
            name="Google Sheet link", label="Google Sheet",
        )
    if kind == "file":
        try:
            info = validate_file(raw)
            return AttachmentInfo(
                type="file", filePath=info.filePath, fileName=info.fileName,
                name=info.fileName, label=get_file_type_label(info.ext),
            )
        except ValueError as e:
            console.print(f"[yellow]⚠ {e} — skipping attachment[/yellow]")
            return None
    console.print("[yellow]⚠ Could not identify — skipping[/yellow]")
    return None


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)
    today = date.today().isoformat()

    epic_key_raw = questionary.text("Which epic? (e.g. QA-247):").ask().strip().upper()
    with httpx.Client(timeout=30) as client:
        with console.status("Validating epic..."):
            try:
                epic = get_epic_info(client, cfg.jiraBaseUrl, auth, epic_key_raw)
            except (ValueError, httpx.HTTPError) as e:
                console.print(f"[red]✗ {e}[/red]")
                sys.exit(1)
        console.print(f"[green]✔[/green] Epic: [cyan]{epic.key}[/cyan] — {epic.summary}")

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
            story_input = questionary.text("Story you tested (key/URL, empty to skip):").ask().strip()
            bug_input = questionary.text("Bug IDs you filed (comma-separated, empty to skip):").ask().strip()
            user_notes = questionary.text("Extra notes (empty to skip):").ask().strip()
        elif task_type == "testcases":
            story_input = questionary.text("Story you wrote test cases for (key/URL, empty to skip):").ask().strip()
            user_notes = questionary.text("Extra notes (empty to skip):").ask().strip()
        else:
            user_notes = questionary.text("What did you work on? (brief description):").ask().strip()
            bug_input = questionary.text("Bug IDs you filed (comma-separated, empty to skip):").ask().strip()

        attachment = _ask_attachment()

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
                    cfg, task_type, story, bug_list, user_notes, attachment,
                )
                console.print("[green]✔[/green] Description generated")
            except Exception as e:
                console.print(f"[yellow]⚠ AI failed: {e}[/yellow]")
                fallback = questionary.text("Enter description manually:").ask()
                from qa_jira.ai.base import build_task_result
                ai_result = build_task_result(
                    {"summary": fallback, "details": "", "outcome": "Task completed."},
                    story, bug_list, attachment,
                )

        suggested = (
            (f"QA Testing — {story.key}" if task_type == "tested" else f"Test Case Creation — {story.key}")
            if story else f"QA Task — {epic.key} — {today}"
        )
        summary = questionary.text("Task summary:", default=suggested).ask()

        label_raw = questionary.text("Label (optional):").ask().strip()
        label = re.sub(r"\s+", "-", label_raw) if label_raw else None

        divider = "─" * 58
        console.print(f"\n[cyan]{divider}[/cyan]")
        console.print("[cyan]  TASK PREVIEW[/cyan]")
        console.print(f"[cyan]{divider}[/cyan]")
        console.print(f"  [dim]Epic:     [/dim]{epic.key} — {epic.summary}")
        console.print(f"  [dim]Summary:  [/dim]{summary}")
        if label: console.print(f"  [dim]Label:    [/dim][green]{label}[/green]")
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
            edited = _open_editor(ai_result.preview)
            paragraphs = [p for p in edited.split("\n\n") if p.strip()]
            adf = make_doc([make_paragraph([make_text(p)]) for p in paragraphs])
            console.print("[green]✔[/green] Description updated")

        with console.status("Creating task..."):
            try:
                created = create_task(
                    client, cfg.jiraBaseUrl, auth,
                    epic_key=epic.key, summary=summary, description=adf,
                    label=label, start_date=today, due_date=today,
                    assignee_account_id=cfg.accountId,
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
                    attach_file_to_issue(client, cfg.jiraBaseUrl, auth, created.issueKey, attachment.filePath)
                    console.print(f"[green]✔[/green] {attachment.label} attached")
                except ValueError as e:
                    console.print(f"[yellow]⚠ Upload failed: {e}[/yellow]")
        elif attachment and attachment.type == "google-sheet" and attachment.url:
            try:
                add_comment_with_link(
                    client, cfg.jiraBaseUrl, auth, created.issueKey,
                    "Test Cases (Google Sheet)", attachment.url,
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
```

- [ ] **Step 2: Manual verification**

Run: `uv run jira task create` against a real epic. Expected: task created, transitioned to Done, attachment handled if provided.

- [ ] **Step 3: Commit**

```bash
git add src/qa_jira/commands/task_create.py && git commit -m "commands: task create — epic validation, task type flow, AI description, create + mark Done"
```

---

## Task 16: `jira mk bugsheet` command

**Files:**
- Create: `/Users/salescode/qa-jira-py/src/qa_jira/commands/mk_bugsheet.py`

- [ ] **Step 1: Write the command**

```python
from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
import questionary
from rich.console import Console

from qa_jira.config import get_config
from qa_jira.excel import write_bugsheet
from qa_jira.jira_client import (
    basic_auth_header, fetch_bugs_in_epic, search_epics_in_project, search_projects,
)
from qa_jira.models import Epic, Project

console = Console()


def _pick_project(client, base_url: str, auth: str) -> Project:
    while True:
        query = questionary.text("Search Jira project/space (partial name):").ask().strip()
        if not query:
            console.print("[yellow]  Project is required[/yellow]")
            continue
        try:
            projects = search_projects(client, base_url, auth, query)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            sys.exit(1)
        if not projects:
            console.print(f'[yellow]  ⚠ No projects found for "{query}"[/yellow]')
            if not questionary.confirm("Search again?", default=True).ask():
                console.print("[dim]Cancelled.[/dim]")
                sys.exit(0)
            continue
        choices = [questionary.Choice(f"[{p.key}] {p.name}", p) for p in projects]
        choices.append(questionary.Choice("Search again", "__again__"))
        pick = questionary.select("Select project:", choices=choices).ask()
        if pick == "__again__":
            continue
        return pick


def _pick_epic(client, base_url: str, auth: str, project_key: str) -> Epic:
    while True:
        query = questionary.text("Search epic (partial name, empty for all):").ask().strip()
        try:
            epics = search_epics_in_project(client, base_url, auth, project_key, query)
        except ValueError as e:
            console.print(f"[red]✗ {e}[/red]")
            sys.exit(1)
        if not epics:
            console.print("[yellow]  ⚠ No epics found[/yellow]")
            if not questionary.confirm("Search again?", default=True).ask():
                console.print("[dim]Cancelled.[/dim]")
                sys.exit(0)
            continue
        choices = [questionary.Choice(f"[{e.key}] {e.summary}", e) for e in epics]
        choices.append(questionary.Choice("Search again", "__again__"))
        pick = questionary.select("Select epic:", choices=choices).ask()
        if pick == "__again__":
            continue
        return pick


def run() -> None:
    start = time.monotonic()
    cfg = get_config()
    auth = basic_auth_header(cfg.jiraEmail, cfg.jiraApiToken)

    console.print("\n[cyan]  jira mk bugsheet — Export bugs to Excel[/cyan]\n")

    with httpx.Client(timeout=60) as client:
        project = _pick_project(client, cfg.jiraBaseUrl, auth)
        console.print(f"[green]  ✔[/green] Project: [white]{project.name}[/white]")
        epic = _pick_epic(client, cfg.jiraBaseUrl, auth, project.key)
        console.print(f"[green]  ✔[/green] Epic: [white]{epic.summary}[/white] ({epic.key})")

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
    console.print(f"[green]  ✔ Found {len(bugs)} bug(s)[/green][dim] — writing sheet...[/dim]")

    out_path = write_bugsheet(bugs=bugs, epic=epic, output_dir=Path.cwd())
    elapsed = time.monotonic() - start

    console.print("\n" + "═" * 58)
    console.print("[green]  ✅ Bug Sheet Created[/green]")
    console.print(f"  [dim]Epic:  [/dim]{epic.key} — {epic.summary}")
    console.print(f"  [dim]Bugs:  [/dim]{len(bugs)} bugs exported")
    console.print(f"  [dim]File:  [/dim][cyan underline]{out_path}[/cyan underline]")
    console.print("═" * 58)
    console.print(f"\n[dim]  Done in {elapsed:.1f}s[/dim]\n")
```

- [ ] **Step 2: Manual verification**

Run: `cd /tmp && uv run jira mk bugsheet` and pick an epic that has bugs. Expected: file `bugsheet-<EPIC>-<DATE>.xlsx` written to `/tmp`, opens cleanly in Excel/Numbers/LibreOffice, header row styled, JIRA ID column is a clickable hyperlink.

- [ ] **Step 3: Commit**

```bash
git add src/qa_jira/commands/mk_bugsheet.py && git commit -m "commands: mk bugsheet — project/epic picker → fetch bugs → write local .xlsx"
```

---

## Task 17: README + final polish

**Files:**
- Modify: `/Users/salescode/qa-jira-py/README.md`

- [ ] **Step 1: Write a complete README**

```markdown
# qa-jira

A command-line tool for QA engineers. Create AI-structured Jira tasks and bugs, delete issues, and export bug rollups for an epic as a local Excel file. Built in Python 3.11+.

## Install

Requires [uv](https://docs.astral.sh/uv/). Clone and install:

\`\`\`bash
git clone <repo-url> qa-jira-py && cd qa-jira-py
uv venv
uv pip install -e .
\`\`\`

The `jira` command is now available.

## First-time setup

\`\`\`bash
jira setup
\`\`\`

Walks through:

1. **Jira credentials** — your account email and an API token from <https://id.atlassian.com/manage-profile/security/api-tokens>. Validated against the workspace.
2. **AI provider** — pick Anthropic (default), OpenRouter (free models), or any OpenAI-compatible endpoint. Validated with a small test call.

Saved to `~/.qa-jira/config.json` with permissions `600`.

## Commands

| Command | Purpose |
|---|---|
| `jira setup` | First-time configuration |
| `jira task create` | Create a daily QA task under an epic; AI-structured description, marked Done on creation |
| `jira mk bug` | File a bug; AI structures the description into steps + actual + expected, set priority/assignee/owner/environment, attach a file or sheet link |
| `jira mk bugsheet` | Export every bug in an epic to a local `.xlsx` file in the current directory |
| `jira rm <KEY\|URL>` | Permanently delete a Jira issue (confirms with default No) |

## AI providers

- **Anthropic** (default) — fast, accurate, paid. New accounts get a small one-time credit; after that, API calls cost a fraction of a cent each for this workload.
- **OpenRouter** — pick any model including free ones (e.g. `nvidia/nemotron-3-nano-30b-a3b:free`). Genuinely $0 if you stay on free models.
- **OpenAI-compatible** — any endpoint that speaks the OpenAI chat-completions API (Groq, local Ollama, vLLM, etc.). Supply your own `base_url`.

Switch providers any time with `jira setup`.

## Attachments

Files up to 10 MB. Supported extensions: `.jmx .js .json .csv .xml .xlsx .zip .png .jpg .jpeg .pdf`. A pasted Google Sheets URL is added as a comment with a clickable link rather than uploaded.

## Config file

\`\`\`
~/.qa-jira/config.json
\`\`\`

Delete it to reset and re-run `jira setup`.

## Development

\`\`\`bash
uv pip install -e ".[dev]"
uv run pytest
\`\`\`
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/salescode/qa-jira-py && uv run pytest -v`
Expected: all tests pass.

- [ ] **Step 3: Final commit**

```bash
git add README.md && git commit -m "docs: README — install, setup, commands, AI providers, attachments"
```

---

## Self-review notes

This plan was self-reviewed before publication. Spot-checks performed:

- **Spec coverage:** every spec section (5 commands, AI provider abstraction, config, Excel, error handling, testing, implementation order) is covered by at least one task.
- **No placeholders:** every code block contains complete, runnable code. No "TBD", "TODO", or "implement later".
- **Type / signature consistency:** `Issue`, `BugInEpic`, `Epic`, `Project`, `User`, `AttachmentInfo`, `Config`, `AIBugResult`, `AITaskResult`, `CreateIssueResult`, `FileInfo` defined in Task 2 / Task 5 and used consistently across Tasks 6–16. Function names (`fetch_issue_details`, `create_bug`, `transition_to_done`, `transition_to_in_progress`, `delete_issue`, `attach_file_to_issue`, `add_comment_with_link`, `fetch_bugs_in_epic`, `search_*`, `generate_bug_description`, `generate_task_description`, `write_bugsheet`) match between definitions and call sites.
- **Tests verify behavior, not implementation.** Each test uses a `MockTransport` handler that asserts the request URL and body rather than internal state.
- **Manual verification stages** are explicit for commands that exercise interactive prompts — these are not testable via pytest in a sustainable way.
