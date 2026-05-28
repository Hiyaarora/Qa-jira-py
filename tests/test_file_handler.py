import pytest

from qa_jira.file_handler import (
    detect_input_type,
    get_file_type_label,
    validate_file,
)


def test_detect_google_sheet():
    assert detect_input_type("https://docs.google.com/spreadsheets/d/abc") == "google-sheet"


def test_detect_url():
    assert detect_input_type("https://example.com/x") == "url"


def test_detect_unknown():
    assert detect_input_type("nope") == "unknown"
    assert detect_input_type("") == "unknown"


def test_detect_file(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text("a,b\n1,2")
    assert detect_input_type(str(p)) == "file"


def test_validate_file_strips_quotes(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}")
    info = validate_file(f'"{p}"')
    assert info.fileName == "x.json"
    assert info.ext == ".json"


def test_validate_file_too_large(tmp_path, monkeypatch):
    p = tmp_path / "big.csv"
    p.write_bytes(b"x" * 100)
    monkeypatch.setattr("qa_jira.file_handler.MAX_FILE_SIZE", 50)
    with pytest.raises(ValueError, match="too large"):
        validate_file(str(p))


def test_validate_file_missing():
    with pytest.raises(ValueError, match="not found"):
        validate_file("/no/such/file.csv")


def test_label_known():
    assert get_file_type_label(".jmx") == "JMeter Load Test Script"
    assert get_file_type_label(".unknown") == "Attachment"
