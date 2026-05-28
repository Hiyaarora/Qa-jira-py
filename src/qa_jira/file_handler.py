from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".jmx",
    ".js",
    ".json",
    ".csv",
    ".xml",
    ".xlsx",
    ".zip",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
}

EXTENSION_LABELS = {
    ".jmx": "JMeter Load Test Script",
    ".js": "API Test Script",
    ".json": "Test Data / Config",
    ".csv": "Test Data",
    ".xml": "Test Config / Suite",
    ".xlsx": "Test Report / Sheet",
    ".zip": "Test Archive",
    ".png": "Screenshot",
    ".jpg": "Screenshot",
    ".jpeg": "Screenshot",
    ".pdf": "Document",
}


@dataclass
class FileInfo:
    filePath: str
    fileName: str
    size: int
    ext: str


def _clean_path(raw: str) -> str:
    s = (raw or "").strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s


def detect_input_type(raw: str) -> str:
    if not raw or not raw.strip():
        return "unknown"
    s = _clean_path(raw)
    if s.startswith("https://docs.google.com/spreadsheets"):
        return "google-sheet"
    if s.startswith("https://") or s.startswith("http://"):
        return "url"
    if Path(s).exists():
        return "file"
    return "unknown"


def validate_file(raw_path: str) -> FileInfo:
    p = Path(_clean_path(raw_path))
    if not p.exists():
        raise ValueError(f"File not found: {p}")
    size = p.stat().st_size
    if size > MAX_FILE_SIZE:
        mb = size / 1024 / 1024
        raise ValueError(f"File too large: {mb:.1f}MB (max 10MB for Jira attachments)")
    return FileInfo(filePath=str(p), fileName=p.name, size=size, ext=p.suffix.lower())


def get_file_type_label(ext: str | None) -> str:
    if not ext:
        return "Attachment"
    return EXTENSION_LABELS.get(ext.lower(), "Attachment")
