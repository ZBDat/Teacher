"""PDF → Markdown conversion tool using pymupdf4llm.

pymupdf4llm is an open-source library built on top of PyMuPDF (fitz) that
converts PDF pages into well-structured Markdown, preserving headings, tables,
lists, code blocks, and images.

Source: https://github.com/pymupdf/RAG (part of the pymupdf ecosystem)
"""

import os
import tempfile
from typing import Any

try:
    import pymupdf4llm  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pymupdf4llm is required for PDF conversion. "
        "Install it with: pip install pymupdf4llm"
    ) from exc

from backend.tools.base import BaseTool


class PdfToMarkdownTool(BaseTool):
    """Converts a PDF file (given as a local path or raw bytes) to Markdown."""

    @property
    def name(self) -> str:
        return "pdf_to_markdown"

    @property
    def description(self) -> str:
        return (
            "Convert a PDF file to Markdown text. "
            "Provide either the absolute path to the PDF file or the name of a "
            "previously uploaded file. Returns the full Markdown string."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the PDF file on disk.",
                }
            },
            "required": ["file_path"],
        }

    async def run(self, file_path: str, **kwargs: Any) -> dict:
        """Convert *file_path* to Markdown and return the result."""
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            markdown_text: str = pymupdf4llm.to_markdown(file_path)
            return {
                "success": True,
                "markdown": markdown_text,
                "pages": markdown_text.count("\f") + 1,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Convenience helper for use outside the agent loop (e.g. REST endpoint)
    # ------------------------------------------------------------------

    @staticmethod
    def convert_bytes(pdf_bytes: bytes) -> dict:
        """Convert raw PDF *bytes* to Markdown without saving to disk permanently.

        The bytes are written to a temporary file, converted, then the temp
        file is immediately removed.
        """
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            markdown_text: str = pymupdf4llm.to_markdown(tmp_path)
            return {
                "success": True,
                "markdown": markdown_text,
                "pages": markdown_text.count("\f") + 1,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}
        finally:
            os.unlink(tmp_path)
