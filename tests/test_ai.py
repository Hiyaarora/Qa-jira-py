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
    r = build_bug_result({}, raw_description="user typed this", environment="Production")
    assert r.title == "user typed this"
    assert r.actualResult == "user typed this"
    assert r.expectedResult == "Correct behavior as expected by the user"
    assert "Environment" in r.preview


def test_build_bug_result_strips_leading_numbers():
    parsed = {
        "title": "Click loses focus",
        "stepsToReproduce": ["1. Open page", "2. Click button"],
        "actualResult": "lost",
        "expectedResult": "kept",
    }
    r = build_bug_result(parsed, "raw", "QA")
    assert r.stepsToReproduce == ["Open page", "Click button"]


def test_build_task_result_with_story_and_bugs():
    story = Issue(
        key="P-1",
        summary="story",
        descriptionText="",
        issueType="Story",
        status="Open",
        url="https://x/browse/P-1",
    )
    bug = Issue(
        key="P-2",
        summary="bug",
        descriptionText="",
        issueType="Bug",
        status="Open",
        url="https://x/browse/P-2",
    )
    r = build_task_result(
        parsed={"summary": "did stuff", "details": "d", "bugs": "b1", "outcome": "ok"},
        story=story,
        bugs=[bug],
        attachment=None,
    )
    assert "did stuff" in r.preview
    assert "P-1" in r.preview and "P-2" in r.preview
    assert any(blk.get("type") == "rule" for blk in r.adf["content"])


def test_get_provider_routes_to_openai_compat(monkeypatch):
    from qa_jira.ai import get_provider
    from qa_jira.models import Config

    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kw):
            captured.update(kw)

        class chat:
            class completions:
                @staticmethod
                def create(**kw): ...

    monkeypatch.setattr("qa_jira.ai.openai_compat_provider.OpenAI", FakeClient)

    cfg = Config(
        jiraEmail="x",
        jiraApiToken="y",
        jiraBaseUrl="https://x",
        accountId="a",
        displayName="N",
        aiProvider="openrouter",
        aiApiKey="k",
        aiModel="m",
    )
    get_provider(cfg)
    assert captured["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["api_key"] == "k"
