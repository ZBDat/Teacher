"""Tests for the FastAPI endpoints (using TestClient / httpx)."""

import io
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# We need to patch the OpenAI client before importing the app so the lifespan
# doesn't fail when OPENAI_API_KEY is missing in the test environment.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with a mocked AgentLoop."""
    with patch("backend.main.AsyncOpenAI"):
        from backend.main import app
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model" in data


# ---------------------------------------------------------------------------
# /api/tools
# ---------------------------------------------------------------------------


def test_list_tools(client):
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    assert len(tools) >= 1
    names = [t["function"]["name"] for t in tools]
    assert "pdf_to_markdown" in names


# ---------------------------------------------------------------------------
# /api/upload
# ---------------------------------------------------------------------------


def _minimal_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF\n"
    )


def test_upload_pdf(client):
    pdf = _minimal_pdf()
    resp = client.post(
        "/api/upload",
        files={"file": ("homework.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    assert data["filename"] == "homework.pdf"
    assert data["size_bytes"] == len(pdf)


# ---------------------------------------------------------------------------
# /api/pdf-to-md  (via file_id returned from upload)
# ---------------------------------------------------------------------------


def test_pdf_to_md_via_file_id(client):
    # First upload
    pdf = _minimal_pdf()
    upload_resp = client.post(
        "/api/upload",
        files={"file": ("hw.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["file_id"]

    # Then convert
    resp = client.post("/api/pdf-to-md", json={"file_id": file_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["markdown"], str)


def test_pdf_to_md_missing_params(client):
    resp = client.post("/api/pdf-to-md", json={})
    assert resp.status_code == 422


def test_pdf_to_md_unknown_file_id(client):
    resp = client.post("/api/pdf-to-md", json={"file_id": "00000000-dead-beef-0000-000000000000"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /api/pdf-to-md/upload  (direct multipart)
# ---------------------------------------------------------------------------


def test_pdf_to_md_direct_upload(client):
    pdf = _minimal_pdf()
    resp = client.post(
        "/api/pdf-to-md/upload",
        files={"file": ("direct.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


# ---------------------------------------------------------------------------
# /api/chat  – mocked agent
# ---------------------------------------------------------------------------


def test_chat_no_api_key(client):
    """Without OPENAI_API_KEY the endpoint returns 503."""
    import backend.main as m
    original = m.settings.OPENAI_API_KEY
    m.settings.OPENAI_API_KEY = ""
    try:
        resp = client.post("/api/chat", json={"message": "Hello"})
        assert resp.status_code == 503
    finally:
        m.settings.OPENAI_API_KEY = original


def test_chat_with_mocked_agent(client):
    """With a mocked agent loop the endpoint returns the agent reply."""
    import backend.main as m
    mock_run = AsyncMock(return_value={"reply": "Test reply", "history": []})
    original_key = m.settings.OPENAI_API_KEY
    m.settings.OPENAI_API_KEY = "sk-test"
    original_run = m.agent_loop.run
    m.agent_loop.run = mock_run
    try:
        resp = client.post("/api/chat", json={"message": "Grade this."})
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "Test reply"
        assert data["history"] == []
    finally:
        m.settings.OPENAI_API_KEY = original_key
        m.agent_loop.run = original_run
