import stat

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


def test_get_config_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_path / "missing.json")
    with pytest.raises(SystemExit):
        config_mod.get_config()
