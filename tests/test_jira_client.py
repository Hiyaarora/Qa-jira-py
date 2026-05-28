import httpx
import pytest

from qa_jira.jira_client import (
    add_comment_with_link,
    basic_auth_header,
    create_bug,
    create_task,
    delete_issue,
    extract_issue_key,
    fetch_bugs_in_epic,
    fetch_issue_details,
    get_epic_info,
    search_epics_in_project,
    search_projects,
    search_users,
    transition_to_done,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ─── Auth + key extraction ──────────────────────────────────────────────────


def test_basic_auth_header():
    h = basic_auth_header("me@example.com", "tok")
    assert h.startswith("Basic ")


def test_extract_issue_key_plain():
    assert extract_issue_key("proj-12") == "PROJ-12"
    assert extract_issue_key("  PROJ-12  ") == "PROJ-12"


def test_extract_issue_key_url():
    assert extract_issue_key("https://x.atlassian.net/browse/PROJ-12") == "PROJ-12"


# ─── Read-side ──────────────────────────────────────────────────────────────


def test_fetch_issue_details_ok():
    def handler(req):
        assert "/rest/api/3/issue/PROJ-1" in str(req.url)
        return httpx.Response(
            200,
            json={
                "fields": {
                    "summary": "x",
                    "description": None,
                    "issuetype": {"name": "Bug"},
                    "status": {"name": "Open"},
                }
            },
        )

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
        return httpx.Response(
            200, json={"fields": {"summary": "s", "issuetype": {"name": "Task"}}}
        )

    with pytest.raises(ValueError, match="not an Epic"):
        get_epic_info(_client(handler), "https://x", "AUTH", "PROJ-1")


def test_search_projects():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "values": [
                    {"key": "A", "name": "Alpha", "id": "1"},
                    {"key": "B", "name": "Beta", "id": "2"},
                ]
            },
        )

    results = search_projects(_client(handler), "https://x", "AUTH", "a")
    assert [p.key for p in results] == ["A", "B"]


def test_search_epics_in_project_with_query():
    captured: dict[str, str] = {}

    def handler(req):
        body = req.read().decode()
        captured["body"] = body
        return httpx.Response(200, json={"issues": [{"key": "P-1", "fields": {"summary": "Epic one"}}]})

    results = search_epics_in_project(_client(handler), "https://x", "AUTH", "PROJ", "login")
    assert results[0].key == "P-1"
    assert "summary ~" in captured["body"]


def test_search_users():
    def handler(req):
        return httpx.Response(
            200,
            json=[
                {"accountId": "a1", "displayName": "Alice", "emailAddress": "a@x"},
                {"accountId": "a2", "displayName": "Andy", "emailAddress": ""},
            ],
        )

    users = search_users(_client(handler), "https://x", "AUTH", "a")
    assert len(users) == 2
    assert users[1].emailAddress == ""


# ─── Write-side ─────────────────────────────────────────────────────────────


def test_create_task_posts_correct_fields():
    captured: dict[str, str] = {}

    def handler(req):
        captured["url"] = str(req.url)
        captured["body"] = req.read().decode()
        return httpx.Response(201, json={"key": "PROJ-9"})

    res = create_task(
        _client(handler),
        "https://x",
        "AUTH",
        epic_key="PROJ-1",
        summary="s",
        description={"type": "doc"},
        label=None,
        start_date="2026-05-28",
        due_date="2026-05-28",
        assignee_account_id="me",
    )
    assert res.issueKey == "PROJ-9"
    assert "customfield_10015" in captured["body"]
    assert "PROJ-1" in captured["body"]


def test_create_bug_success_first_try():
    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(200, json={"issueTypes": [{"name": "Bug"}]})
        return httpx.Response(201, json={"key": "PROJ-2"})

    res = create_bug(
        _client(handler),
        "https://x",
        "AUTH",
        project_key="PROJ",
        epic_key="PROJ-1",
        summary="s",
        description={"type": "doc"},
        priority="P1",
        assignee_account_id=None,
        issue_owner_account_id=None,
        environment="Production",
    )
    assert res.issueKey == "PROJ-2"


def test_create_bug_no_bug_type_in_project():
    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(
                200, json={"issueTypes": [{"name": "Story"}, {"name": "Task"}]}
            )
        return httpx.Response(500)

    with pytest.raises(ValueError, match='does not have a "Bug"'):
        create_bug(
            _client(handler),
            "https://x",
            "AUTH",
            project_key="PROJ",
            epic_key=None,
            summary="s",
            description={"type": "doc"},
            priority="P3",
            assignee_account_id=None,
            issue_owner_account_id=None,
            environment=None,
        )


def test_create_bug_epic_field_fallback():
    calls: list[str] = []

    def handler(req):
        if req.url.path.endswith("/issuetypes"):
            return httpx.Response(200, json={"issueTypes": [{"name": "Bug"}]})
        body = req.read().decode()
        calls.append(body)
        if len(calls) < 3:
            return httpx.Response(400, json={"errors": {"parent": "Invalid"}})
        return httpx.Response(201, json={"key": "PROJ-3"})

    res = create_bug(
        _client(handler),
        "https://x",
        "AUTH",
        project_key="PROJ",
        epic_key="PROJ-1",
        summary="s",
        description={"type": "doc"},
        priority="P2",
        assignee_account_id=None,
        issue_owner_account_id=None,
        environment=None,
    )
    assert res.issueKey == "PROJ-3"
    assert len(calls) == 3


def test_transition_to_done_finds_match():
    def handler(req):
        if req.method == "GET":
            return httpx.Response(
                200,
                json={
                    "transitions": [
                        {"id": "10", "name": "In Progress"},
                        {"id": "11", "name": "Done"},
                    ]
                },
            )
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
        return httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "key": "PROJ-9",
                        "fields": {
                            "summary": "Bug nine",
                            "status": {"name": "Open"},
                            "priority": {"name": "P1"},
                            "assignee": {"displayName": "Alice"},
                            "reporter": {"displayName": "Bob"},
                            "created": "2026-05-01T10:00:00.000+0000",
                            "description": None,
                            "issuetype": {"name": "Bug"},
                        },
                    }
                ]
            },
        )

    bugs = fetch_bugs_in_epic(_client(handler), "https://x", "AUTH", "PROJ-1")
    assert bugs[0].key == "PROJ-9"
    assert bugs[0].created == "2026-05-01"
    assert bugs[0].environment == "UAT"


def test_add_comment_with_link_ok():
    captured: dict[str, str] = {}

    def handler(req):
        captured["body"] = req.read().decode()
        return httpx.Response(201, json={})

    add_comment_with_link(
        _client(handler), "https://x", "AUTH", "PROJ-1", "Sheet", "https://example.com"
    )
    assert "Sheet:" in captured["body"]
    assert "https://example.com" in captured["body"]
