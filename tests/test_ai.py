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


def test_get_provider_returns_http_provider():
    from qa_jira.ai import get_provider
    from qa_jira.ai.http_provider import HttpProvider
    from qa_jira.models import Config

    cfg = Config(
        jiraEmail="x", jiraApiToken="y", jiraBaseUrl="https://x",
        accountId="a", displayName="N", aiProvider="openrouter",
        aiApiKey="k", aiModel="m",
    )
    provider = get_provider(cfg)
    assert isinstance(provider, HttpProvider)
    assert provider._url == "https://openrouter.ai/api/v1/chat/completions"
    assert "Bearer k" in provider._headers["Authorization"]


def test_http_provider_uses_custom_base_url():
    from qa_jira.ai.http_provider import HttpProvider
    from qa_jira.models import Config

    cfg = Config(
        jiraEmail="x", jiraApiToken="y", jiraBaseUrl="https://x",
        accountId="a", displayName="N", aiProvider="openai-compatible",
        aiApiKey="k", aiModel="m",
        aiBaseUrl="https://my-endpoint.com/v1",
    )
    provider = HttpProvider(cfg)
    assert provider._url == "https://my-endpoint.com/v1/chat/completions"


def test_http_provider_falls_back_on_404(monkeypatch):
    import httpx
    import unittest.mock as mock
    from qa_jira.ai.http_provider import HttpProvider, FALLBACK_MODELS
    from qa_jira.models import Config

    calls = []
    good_model = FALLBACK_MODELS[0]

    def fake_post(model, system_prompt, user_prompt, max_tokens, image_paths=None):
        calls.append(model)
        if model != good_model:
            return httpx.Response(404, json={"error": {"message": "not found"}})
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"title": "ok"}'}}]
        })

    cfg = Config(
        jiraEmail="x", jiraApiToken="y", jiraBaseUrl="https://x",
        accountId="a", displayName="N", aiProvider="openrouter",
        aiApiKey="k", aiModel="bad-model:free",
    )
    provider = HttpProvider(cfg)

    # Patch _fetch_free_models to return empty (isolate from network)
    # and patch _post to simulate 404 then success
    with mock.patch("qa_jira.ai.http_provider._fetch_free_models", return_value=[]), \
         mock.patch.object(provider, "_post", side_effect=fake_post):
        result = provider.complete_json("sys", "user", 100)

    assert result == '{"title": "ok"}'
    assert calls[0] == "bad-model:free"
    assert calls[1] == good_model
