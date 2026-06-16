# qa-jira

A command-line tool for QA engineers. Create AI-structured Jira tasks and bugs, delete issues, and export bug rollups for an epic as a local Excel file. Built in Python 3.11+.

---

## Install

Requires [uv](https://docs.astral.sh/uv/). Clone and install:

```bash
git clone <repo-url> qa-jira-py && cd qa-jira-py
uv venv
uv pip install -e .
```

Or install globally so `jira` is available everywhere:

```bash
uv tool install .
```

---

## First-time setup

```bash
jira setup
```

Walks through:

1. **Jira credentials** — your account email and an API token from <https://id.atlassian.com/manage-profile/security/api-tokens>. Validated against the workspace before saving.
2. **AI provider** — pick Anthropic, OpenRouter (free models available), or any OpenAI-compatible endpoint. Key is validated with a test call.

Saved to `~/.qa-jira/config.json` with permissions `600` (only you can read it).

---

## Commands

### `jira task create`

Create a daily QA task under an epic.

```bash
jira task create
```

**Flow:**
1. Enter the epic key (e.g. `PROJ-315`) or paste the Jira URL
2. Pick what you worked on: tested a story / wrote test cases / other
3. Enter story key/URL, bug IDs, notes, and optional attachment
4. AI generates a professional task description
5. Preview → confirm → task created and marked Done

Supports attaching files (screenshots, JMX, CSV, etc.) and Google Sheet links.

---

### `jira mk bug`

File a bug with an AI-structured description.

```bash
jira mk bug
```

**Flow:**
1. Describe the bug in plain English
2. Pick environment (Production / Demo / Test)
3. AI structures it into: title, steps to reproduce, actual result, expected result
4. Pick priority (P1 / P2 / P3)
5. Optionally assign Assignee and Issue Owner
6. Optionally attach a file or Google Sheet link
7. Search and select a Jira project and optional epic
8. Preview the full bug → confirm, edit in `$EDITOR`, or cancel
9. Bug is created and transitioned to In Progress

---

### `jira mk bugsheet`

Export all bugs in an epic to a local Excel file.

```bash
jira mk bugsheet
```

**Flow:**
1. Search for a Jira project by partial name
2. Search for an epic by name, key (e.g. `PROJ-27`), or paste a Jira URL
3. All bugs in the epic are fetched from Jira
4. An Excel file is written to your current directory named `bugsheet-{EPIC}-{DATE}.xlsx`

**Columns:** Bug ID, Bug Type, Reported By, Reporting Date, JIRA ID (clickable link), Title, Current Status, Environment, Priority, RCA, Assignee, Remarks

**Styling:** Bold dark-blue header, alternating row colours, frozen header row, auto-width columns.

---

### `jira rm <KEY|URL>`

Delete a Jira issue permanently.

```bash
jira rm PROJ-123
jira rm https://yourcompany.atlassian.net/browse/PROJ-123
```

- Shows full issue details before asking for confirmation
- Default answer is **No** — you must explicitly confirm
- Requires delete permissions on the project

---

## AI providers

| Provider | Cost | How to get a key |
|---|---|---|
| **Anthropic** (default) | Paid — small free credit on sign-up | <https://console.anthropic.com/settings/keys> |
| **OpenRouter** | Free models available (no card needed) | <https://openrouter.ai/keys> |
| **OpenAI-compatible** | Depends on provider | Your provider's dashboard |

The CLI automatically tries backup free models if your configured model is temporarily unavailable on OpenRouter.

Switch providers any time with `jira setup`.

---

## Attachments

| Input | What happens |
|---|---|
| Google Sheet URL | Added as a comment with a clickable link |
| `.png`, `.jpg`, `.pdf`, `.csv`, `.xlsx`, `.zip`, `.jmx`, `.json`, `.xml` | Uploaded as a file attachment (max 10 MB) |

---

## Config file

```
~/.qa-jira/config.json
```

Delete it to reset, then run `jira setup` again.

---

## Development

```bash
uv pip install -e ".[dev]"
uv run pytest
```
