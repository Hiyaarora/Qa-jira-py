import pytest

from qa_jira.adf import (
    adf_to_plain_text,
    make_bullet_list,
    make_doc,
    make_link,
    make_paragraph,
    make_text,
    validate_adf,
)


def test_make_text_bold():
    assert make_text("hi", bold=True) == {
        "type": "text",
        "text": "hi",
        "marks": [{"type": "strong"}],
    }


def test_make_link():
    assert make_link("Google", "https://g.com") == {
        "type": "text",
        "text": "Google",
        "marks": [{"type": "link", "attrs": {"href": "https://g.com"}}],
    }


def test_make_doc_structure():
    doc = make_doc([make_paragraph([make_text("hi")])])
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert doc["content"][0]["type"] == "paragraph"


def test_make_paragraph_empty():
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
