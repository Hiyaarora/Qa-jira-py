from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


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
