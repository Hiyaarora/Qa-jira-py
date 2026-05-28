from __future__ import annotations

from typing import Any

BLOCK_TYPES = {
    "paragraph",
    "bulletList",
    "orderedList",
    "rule",
    "heading",
    "blockquote",
    "codeBlock",
    "listItem",
}
INLINE_TYPES = {"text", "emoji", "hardBreak", "mention", "inlineCard"}


def make_doc(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "doc", "version": 1, "content": [b for b in blocks if b]}


def make_paragraph(inline_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    filtered = [n for n in inline_nodes if n]
    if not filtered:
        return {"type": "paragraph", "content": [{"type": "text", "text": " "}]}
    return {"type": "paragraph", "content": filtered}


def make_text(text: str, bold: bool = False) -> dict[str, Any]:
    if not text or not isinstance(text, str):
        return {"type": "text", "text": " "}
    node: dict[str, Any] = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def make_link(text: str, url: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text or url,
        "marks": [{"type": "link", "attrs": {"href": url}}],
    }


def make_rule() -> dict[str, Any]:
    return {"type": "rule"}


def make_bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {"type": "listItem", "content": [make_paragraph([make_text(item)])]}
            for item in items
            if item
        ],
    }


def validate_adf(doc: dict[str, Any]) -> bool:
    if doc.get("type") != "doc":
        raise ValueError("ADF root must be type doc")
    for block in doc.get("content", []):
        if block["type"] not in BLOCK_TYPES:
            raise ValueError(f"Invalid block type: {block['type']}")
        for inline in block.get("content", []):
            if inline["type"] not in BLOCK_TYPES | INLINE_TYPES:
                raise ValueError(f"Invalid inline type: {inline['type']}")
    return True


def adf_to_plain_text(node: dict[str, Any] | None) -> str:
    if not node:
        return ""
    t = node.get("type")
    if t == "text":
        return node.get("text", "")
    if t == "hardBreak":
        return "\n"
    if t in {"doc", "paragraph", "blockquote", "heading"}:
        return "".join(adf_to_plain_text(c) for c in node.get("content", [])) + "\n"
    if t in {"bulletList", "orderedList"}:
        return "".join(adf_to_plain_text(c) for c in node.get("content", []))
    if t == "listItem":
        return "- " + "".join(adf_to_plain_text(c) for c in node.get("content", []))
    return "".join(adf_to_plain_text(c) for c in node.get("content", []))
