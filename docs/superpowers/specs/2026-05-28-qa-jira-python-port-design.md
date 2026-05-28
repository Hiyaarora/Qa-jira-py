# QA Jira CLI (Python)

**Date:** 2026-05-28
**Status:** Draft — awaiting user review
**Target project:** `/Users/salescode/qa-jira-py` (Python 3.11+)

## Goal

A command-line tool for QA engineers. Five commands, all interactive, all running against a real Jira Cloud workspace. Daily QA tasks and bug reports are structured by an AI provider; bug rollups for an epic are exported as a local Excel file.

## Commands

| Command | Behavior |
|---|---|
| `jira setup` | Interactive wizard: Jira email + API token (validated against the workspace), AI provider choice (Anthropic / OpenRouter / OpenAI-compatible) + API key (validated with a test call), default model name. Saves to `~/.qa-jira/config.json` with `chmod 600`. |
| `jira task create` | Create a daily QA task under an epic. Asks for epic key, task type (tested a story / wrote test cases / other), optional story key, optional bug IDs, free-form notes, optional attachment. AI generates a structured description. Preview → confirm/edit/cancel → create the task → mark Done. |
| `jira mk bug` | Plain-English bug description → AI structures into title + steps to reproduce + actual result + expected result. Asks for environment, priority, optional assignee, optional issue owner, optional attachment, project, optional epic. Preview → confirm/edit-in-`$EDITOR`/cancel → create the bug → transition to In Progress. |
| `jira mk bugsheet` | Search project → search epic → fetch all bugs in epic → write a 12-column `.xlsx` file to the current working directory named `bugsheet-{EPIC_KEY}-{YYYY-MM-DD}.xlsx`. Print the absolute path. |
| `jira rm <KEY\|URL>` | Fetch full issue details → display them → confirm (default No) → delete via Jira REST. Permanent. |

## AI provider

**Default:** Anthropic Claude, via the official `anthropic` Python SDK. The Anthropic API has no permanent free tier — new accounts get a small one-time credit (~$5 of usage), then the API is pay-as-you-go. Cost for this CLI's workload is low (a typical bug-structuring call uses a few thousand tokens), but the user should be aware before configuring.

**Alternatives** (offered in the setup wizard):
- **OpenRouter** — uses the `openai` SDK with `base_url=https://openrouter.ai/api/v1`. Has free models (e.g. `nvidia/nemotron-3-nano-30b-a3b:free`) for users who want zero cost.
- **OpenAI-compatible** — any endpoint that speaks the OpenAI chat-completions API (Groq, local Ollama, vLLM, etc.). User supplies their own `base_url` and key.

All three providers feed the same prompt templates and return the same structured output shape.

## Non-goals

- Not building an agentic / LLM-driven CLI. The flow is prompt-driven; the AI is used only to structure descriptions.
- No Google Sheets integration, no OAuth, no Drive API.
- No new commands, fields, or integrations beyond what is listed in the Commands table.

## Architecture

```
qa-jira-py/
├── pyproject.toml              # uv + console_scripts: jira = qa_jira.cli:main
├── README.md
├── src/qa_jira/
│   ├── __init__.py
│   ├── __main__.py             # python -m qa_jira
│   ├── cli.py                  # arg parsing, command dispatch, help
│   ├── config.py               # load/save ~/.qa-jira/config.json (chmod 600)
│   ├── models.py               # pydantic v2: Config, Issue, Bug, User, Project, Epic, AttachmentInfo, AIBugResult, AITaskResult
│   ├── jira_client.py          # httpx-based REST client
│   ├── adf.py                  # Atlassian Document Format builder (make_doc / make_paragraph / make_text)
│   ├── file_handler.py         # detect_input_type, validate_file
│   ├── excel.py                # write_bugsheet(bugs, epic, path) → .xlsx
│   ├── prompts.py              # system + user prompt templates for AI
│   ├── ai/
│   │   ├── __init__.py         # get_provider(config) factory
│   │   ├── base.py             # Provider protocol
│   │   ├── anthropic_provider.py
│   │   └── openai_compat_provider.py
│   └── commands/
│       ├── __init__.py
│       ├── setup.py
│       ├── task_create.py
│       ├── mk_bug.py
│       ├── mk_bugsheet.py
│       └── rm.py
└── tests/
    ├── test_config.py
    ├── test_jira_client.py     # uses httpx mock transport
    ├── test_ai.py              # mocks both providers
    ├── test_excel.py           # writes to tmp_path, verifies cells/styling
    ├── test_file_handler.py
    └── test_adf.py
```

### Library choices

| Concern | Library |
|---|---|
| HTTP client | `httpx` |
| Interactive prompts | `questionary` |
| Terminal styling | `rich` |
| Dates | `python-dateutil` |
| Excel | `openpyxl` |
| Anthropic | `anthropic` |
| OpenRouter / OpenAI-compatible | `openai` (with custom `base_url`) |
| Data models | `pydantic` v2 |
| Multipart upload | `httpx` (built-in `files=`) |

### AI provider abstraction

`ai/base.py` defines a `Provider` protocol with two methods:

```python
class Provider(Protocol):
    def generate_bug_description(self, raw_description: str, environment: str) -> AIBugResult: ...
    def generate_task_description(self, task_type: str, story: Issue | None, bugs: list[Issue], user_notes: str, attachment: AttachmentInfo | None) -> AITaskResult: ...
```

Each provider implementation returns an `AIBugResult` / `AITaskResult` Pydantic model containing the structured fields plus the ADF document. The Anthropic provider uses the official SDK with prompt caching enabled on the system prompt. The OpenAI-compatible provider uses the `openai` SDK with a configurable `base_url` (for OpenRouter or any compatible endpoint). The same prompt templates from `prompts.py` feed both providers, parsed into the same `AIBugResult` / `AITaskResult` shape. If the AI call fails (network, timeout, invalid JSON), the calling command surfaces a yellow warning and falls back to manual-input — the bug or task still gets created.

### Config

`~/.qa-jira/config.json`. Fields:

```
{
  "jiraEmail": "...",
  "jiraApiToken": "...",
  "jiraBaseUrl": "https://<workspace>.atlassian.net",
  "accountId": "...",
  "aiProvider": "anthropic" | "openrouter" | "openai-compatible",
  "aiApiKey": "...",
  "aiModel": "claude-sonnet-4-6" | "nvidia/nemotron-3-nano-30b-a3b:free" | ...,
  "aiBaseUrl": "https://openrouter.ai/api/v1" | null
}
```

`aiBaseUrl` is only set for the `openai-compatible` provider. The file is created with `chmod 600`. Loaded once per command via `config.get_config()`.

### Excel bugsheet

`excel.write_bugsheet(bugs, epic, output_path)` writes 12 columns: **Bug ID, Bug Type, Reported By, Reporting Date, JIRA ID, Title, Current Status, Environment, Priority, RCA, Assignee, Remarks**. Styling: bold dark-blue header row with white text, alternating white/light-blue data rows, hyperlink in the JIRA ID column, frozen first row, auto-width columns. Returns the absolute path written.

### Error handling

- Network and HTTP errors from `httpx` surface as a one-line red error and `sys.exit(1)`.
- AI provider failures (timeout, non-JSON output, schema mismatch) trigger a yellow warning and fall back to manual input — bug/task creation continues.
- Jira validation errors (e.g. project has no `Bug` issue type, missing delete permission) print a tip line with a remediation hint and `sys.exit(1)`.
- File-attachment failures are non-fatal — yellow warning, issue still gets created.
- Transition failures (e.g. no "In Progress" transition available) are non-fatal — dim status message.

### Testing

`pytest` with `httpx.MockTransport` for the Jira client, `pytest-mock` for the AI providers (no real API calls), `tmp_path` for the Excel writer. Aim: unit coverage on `jira_client`, `excel`, `adf`, `file_handler`, `ai/*`, and the config load/save round-trip. Command flow tests are minimal smoke tests — the interactive UI is manually verified by running each command against a real Jira workspace.

## Implementation order

1. **Scaffold:** `pyproject.toml`, `src/qa_jira/__init__.py`, console_script entry point. Verify `uv tool install --editable .` exposes `jira --help`.
2. **Foundation:** `models.py`, `config.py`, `adf.py`, `file_handler.py`. Tests for each.
3. **Jira client:** `jira_client.py` — auth, fetch issue, create task, create bug, transition, search projects/epics/users, attach file, comment, delete, fetch bugs in epic. Tests with `MockTransport`.
4. **AI layer:** `prompts.py`, `ai/base.py`, `ai/anthropic_provider.py`, `ai/openai_compat_provider.py`, `ai/__init__.py` factory. Tests mocking the SDKs.
5. **Excel:** `excel.py`. Tests verify cell values, styling, hyperlinks.
6. **Setup wizard:** `commands/setup.py` and wire into `cli.py`. Manual verification: run `jira setup` end-to-end.
7. **Commands:** `commands/rm.py` → `commands/mk_bug.py` → `commands/task_create.py` → `commands/mk_bugsheet.py`, in that order (simplest first). Each one gets a manual end-to-end run against a real Jira workspace before moving on.
8. **README** with install and usage instructions.

## Open questions

None — all decisions resolved during brainstorming:

- Five commands in scope, all interactive
- Anthropic Claude as default AI provider; OpenRouter + OpenAI-compatible as alternatives
- Local `.xlsx` for `mk bugsheet` (save only)
- uv + `pyproject.toml`, exposes `jira` console_script
- Built sequentially in this session
