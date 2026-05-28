from qa_jira.models import AIBugResult, Config, Issue


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
        key="PROJ-1",
        summary="x",
        descriptionText="",
        issueType="Bug",
        status="Open",
        url="https://x.atlassian.net/browse/PROJ-1",
    )
    assert i.key == "PROJ-1"
