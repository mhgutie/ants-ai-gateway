from fastapi.testclient import TestClient

import app.main as main
from app.auth import require_gateway_api_key
from app.main import app

client = TestClient(app)


def _allow_gateway() -> None:
    app.dependency_overrides[require_gateway_api_key] = lambda: None


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _fake_result(markdown: str, title: str | None = None, source_type: str = "pdf"):
    def _fn(*_args, **_kwargs):
        return {
            "markdown": markdown,
            "title": title,
            "source_type": source_type,
            "char_count": len(markdown),
            "conversion_time_ms": 1,
        }

    return _fn


def test_ingest_convert_url_returns_markdown(monkeypatch):
    monkeypatch.setattr(main, "ingest_convert_url", _fake_result("# Hello\nWorld", source_type="url"))
    _allow_gateway()
    try:
        response = client.post("/ingest/convert", data={"url": "https://example.com/doc"})
    finally:
        _clear_overrides()
    assert response.status_code == 200
    body = response.json()
    assert body["markdown"] == "# Hello\nWorld"
    assert body["source_type"] == "url"
    assert body["char_count"] == 13


def test_ingest_convert_file_returns_markdown(monkeypatch):
    monkeypatch.setattr(
        main, "ingest_convert_bytes", _fake_result("# PDF Content", title="My Doc", source_type="pdf")
    )
    _allow_gateway()
    try:
        response = client.post(
            "/ingest/convert",
            files={"file": ("report.pdf", b"%PDF-1.4 dummy", "application/pdf")},
        )
    finally:
        _clear_overrides()
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "My Doc"
    assert "PDF Content" in body["markdown"]
    assert body["source_type"] == "pdf"


def test_ingest_convert_missing_input_returns_422():
    _allow_gateway()
    try:
        response = client.post("/ingest/convert")
    finally:
        _clear_overrides()
    assert response.status_code == 422


def test_ingest_convert_requires_auth():
    response = client.post("/ingest/convert", data={"url": "https://example.com"})
    assert response.status_code in (401, 403, 503)
