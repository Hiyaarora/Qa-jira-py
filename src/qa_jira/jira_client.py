from __future__ import annotations

import base64
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from qa_jira.adf import adf_to_plain_text, make_doc, make_link, make_paragraph, make_text
from qa_jira.models import BugInEpic, CreateIssueResult, Epic, Issue, Project, User


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


# ─── Read-side endpoints ────────────────────────────────────────────────────


def fetch_issue_details(
    client: httpx.Client, base_url: str, auth: str, key_or_url: str
) -> Issue:
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


def get_epic_info(
    client: httpx.Client, base_url: str, auth: str, epic_key: str
) -> Epic:
    key = epic_key.strip().upper()
    url = f"{base_url}/rest/api/3/issue/{key}?fields=summary,issuetype"
    resp = client.get(url, headers={"Authorization": auth})
    resp.raise_for_status()
    data = resp.json()
    if data["fields"]["issuetype"]["name"] != "Epic":
        raise ValueError(f"{key} is not an Epic")
    return Epic(key=key, summary=data["fields"]["summary"])


def search_projects(
    client: httpx.Client, base_url: str, auth: str, query: str
) -> list[Project]:
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
    client: httpx.Client,
    base_url: str,
    auth: str,
    project_key: str,
    query: str,
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


def search_users(
    client: httpx.Client, base_url: str, auth: str, query: str
) -> list[User]:
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


# ─── Write-side endpoints ───────────────────────────────────────────────────


def create_task(
    client: httpx.Client,
    base_url: str,
    auth: str,
    *,
    epic_key: str,
    summary: str,
    description: dict[str, Any],
    label: str | None,
    start_date: str | None,
    due_date: str | None,
    assignee_account_id: str,
) -> CreateIssueResult:
    safe_start = start_date or date.today().isoformat()
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
    client: httpx.Client,
    base_url: str,
    auth: str,
    *,
    project_key: str,
    epic_key: str | None,
    summary: str,
    description: dict[str, Any],
    priority: str,
    assignee_account_id: str | None,
    issue_owner_account_id: str | None,
    environment: str | None,
    label: str | None = None,
) -> CreateIssueResult:
    # Verify the project supports Bug issue type
    try:
        meta = client.get(
            f"{base_url}/rest/api/3/issue/createmeta/{project_key}/issuetypes",
            headers={"Authorization": auth, "Accept": "application/json"},
        )
        if meta.status_code < 400:
            data = meta.json()
            types = data.get("issueTypes") or data.get("values") or data or []
            if isinstance(types, list):
                type_names = [t.get("name", "") for t in types]
                if type_names and not any(n.lower() == "bug" for n in type_names):
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

    last_err = "unknown error"
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
    client: httpx.Client,
    base_url: str,
    auth: str,
    issue_key: str,
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


def transition_to_done(
    client: httpx.Client, base_url: str, auth: str, issue_key: str
) -> bool:
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


def transition_to_in_progress(
    client: httpx.Client, base_url: str, auth: str, issue_key: str
) -> bool:
    tid = find_transition_id(
        client, base_url, auth, issue_key, needles=("progress", "start")
    )
    if not tid:
        return False
    resp = client.post(
        f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
        json={"transition": {"id": tid}},
        headers={"Authorization": auth, "Content-Type": "application/json"},
    )
    return resp.status_code < 400


def delete_issue(
    client: httpx.Client, base_url: str, auth: str, key_or_url: str
) -> None:
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
    client: httpx.Client,
    base_url: str,
    auth: str,
    issue_key: str,
    file_path: str,
) -> dict[str, Any]:
    p = Path(file_path)
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
    client: httpx.Client,
    base_url: str,
    auth: str,
    issue_key: str,
    link_text: str,
    link_url: str,
) -> None:
    body = make_doc([
        make_paragraph([
            make_text(link_text + ": ", bold=True),
            make_link(link_url, link_url),
        ])
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
    client: httpx.Client, base_url: str, auth: str, epic_key: str
) -> list[BugInEpic]:
    jql_options = [
        f'"Epic Link" = {epic_key} AND issuetype = Bug ORDER BY created ASC',
        f"cf[10014] = {epic_key} AND issuetype = Bug ORDER BY created ASC",
        f"parent = {epic_key} AND issuetype = Bug ORDER BY created ASC",
    ]
    last_err = "all JQL variants failed"
    issues: list[dict[str, Any]] = []
    fetched = False

    for jql in jql_options:
        resp = client.post(
            f"{base_url}/rest/api/3/search/jql",
            json={
                "jql": jql,
                "fields": [
                    "summary",
                    "status",
                    "priority",
                    "assignee",
                    "reporter",
                    "created",
                    "description",
                    "issuetype",
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
        fetched = True
        break

    if not fetched:
        raise ValueError(f"Could not query bugs for epic {epic_key}: {last_err}")

    result: list[BugInEpic] = []
    for issue in issues:
        f = issue["fields"]
        desc_text = adf_to_plain_text(f.get("description")) if f.get("description") else ""
        result.append(
            BugInEpic(
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
            )
        )
    return result
