"""Tests for the PDF to Markdown converter tool."""

import os
import pytest

from backend.tools.pdf_converter import PdfToMarkdownTool


def _make_minimal_pdf() -> bytes:
    """Return a minimal valid PDF byte string for smoke-testing."""
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


@pytest.fixture
def pdf_path(tmp_path):
    """Write a minimal PDF to a temp file and return the path."""
    p = tmp_path / "test.pdf"
    p.write_bytes(_make_minimal_pdf())
    return str(p)


@pytest.fixture
def tool():
    return PdfToMarkdownTool()


# ---------------------------------------------------------------------------
# Property / schema tests (no PDF parsing needed)
# ---------------------------------------------------------------------------


def test_tool_name(tool):
    assert tool.name == "pdf_to_markdown"


def test_tool_description_non_empty(tool):
    assert tool.description


def test_tool_parameters_schema(tool):
    params = tool.parameters
    assert params["type"] == "object"
    assert "file_path" in params["properties"]
    assert params["required"] == ["file_path"]


def test_openai_function_schema(tool):
    schema = tool.to_openai_function()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "pdf_to_markdown"


# ---------------------------------------------------------------------------
# run() – error handling (file not found)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_missing_file_returns_error(tool):
    result = await tool.run(file_path="/nonexistent/path/file.pdf")
    assert result["success"] is False
    assert "error" in result


# ---------------------------------------------------------------------------
# run() – happy path with a real (minimal) PDF
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_valid_pdf(tool, pdf_path):
    result = await tool.run(file_path=pdf_path)
    assert result["success"] is True
    assert "markdown" in result
    assert isinstance(result["markdown"], str)
    assert result["pages"] >= 1


# ---------------------------------------------------------------------------
# convert_bytes() – happy path
# ---------------------------------------------------------------------------


def test_convert_bytes_valid_pdf():
    result = PdfToMarkdownTool.convert_bytes(_make_minimal_pdf())
    assert result["success"] is True
    assert isinstance(result["markdown"], str)


def test_convert_bytes_invalid_bytes():
    result = PdfToMarkdownTool.convert_bytes(b"not a pdf")
    assert result["success"] is False
    assert "error" in result
