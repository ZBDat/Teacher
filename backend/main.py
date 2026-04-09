"""FastAPI application – entry point for the Teacher grading agent backend.

Endpoints
---------
GET  /api/health           – liveness check
GET  /api/tools            – list registered tools
POST /api/chat             – single-turn or multi-turn agent interaction
POST /api/upload           – upload a file (PDF, etc.) for later use
POST /api/pdf-to-md        – convert an uploaded or on-disk PDF to Markdown
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.agent.loop import AgentLoop
from backend.config import settings
from backend.tools.pdf_converter import PdfToMarkdownTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------

agent_loop: AgentLoop


@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_loop
    openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or None)
    agent_loop = AgentLoop(openai_client=openai_client, model=settings.OPENAI_MODEL)
    logger.info("Agent loop initialised with model '%s'.", settings.OPENAI_MODEL)
    yield


# ---------------------------------------------------------------------------
# App construction
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Teacher Grading Agent",
    description="AI-assisted grading tool for teachers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend as static files when the directory exists
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/ui", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = None
    """Optional conversation history returned by a previous /api/chat call."""


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    file_path: str
    size_bytes: int


class PdfToMdRequest(BaseModel):
    file_id: Optional[str] = None
    """ID returned by /api/upload, OR provide file_path directly."""
    file_path: Optional[str] = None
    """Absolute path to a PDF already on disk."""


class PdfToMdResponse(BaseModel):
    success: bool
    markdown: Optional[str] = None
    pages: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["System"])
async def health() -> dict:
    """Liveness check."""
    return {"status": "ok", "model": settings.OPENAI_MODEL}


@app.get("/api/tools", tags=["System"])
async def list_tools() -> list[dict]:
    """Return the OpenAI function schema for all registered tools."""
    return agent_loop.tool_registry.to_openai_tools()


@app.post("/api/chat", response_model=ChatResponse, tags=["Agent"])
async def chat(req: ChatRequest) -> ChatResponse:
    """Send a message to the agent and receive a response.

    Pass the ``history`` field from the previous response to maintain context
    across multiple turns.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

    result = await agent_loop.run(
        user_message=req.message,
        history=req.history,
    )
    return ChatResponse(reply=result["reply"], history=result["history"])


@app.post("/api/upload", response_model=UploadResponse, tags=["Files"])
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    """Upload a file (PDF, image, etc.) and receive a ``file_id`` for later use."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit.",
        )

    file_id = str(uuid.uuid4())
    original_name = file.filename or "upload"
    # Preserve extension for tools that need it (e.g. pymupdf)
    ext = os.path.splitext(original_name)[1] or ".bin"
    dest_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    with open(dest_path, "wb") as fh:
        fh.write(content)

    logger.info("Uploaded '%s' → %s (%d bytes)", original_name, dest_path, len(content))
    return UploadResponse(
        file_id=file_id,
        filename=original_name,
        file_path=dest_path,
        size_bytes=len(content),
    )


@app.post("/api/pdf-to-md", response_model=PdfToMdResponse, tags=["Files"])
async def pdf_to_md(req: PdfToMdRequest) -> PdfToMdResponse:
    """Convert a PDF file to Markdown.

    Supply either a ``file_id`` (from /api/upload) or a ``file_path``
    (absolute path on the server).
    """
    if req.file_id:
        # Find the file by scanning the upload directory for a name starting with file_id
        matched = [
            f
            for f in os.listdir(settings.UPLOAD_DIR)
            if f.startswith(req.file_id)
        ]
        if not matched:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No file found for file_id '{req.file_id}'.",
            )
        file_path = os.path.join(settings.UPLOAD_DIR, matched[0])
    elif req.file_path:
        file_path = req.file_path
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide either 'file_id' or 'file_path'.",
        )

    converter = PdfToMarkdownTool()
    result = await converter.run(file_path=file_path)
    return PdfToMdResponse(**result)


# ---------------------------------------------------------------------------
# Convenience: also accept multipart uploads directly to /api/pdf-to-md
# ---------------------------------------------------------------------------


@app.post("/api/pdf-to-md/upload", response_model=PdfToMdResponse, tags=["Files"])
async def pdf_to_md_upload(file: UploadFile = File(...)) -> PdfToMdResponse:
    """Upload a PDF and immediately convert it to Markdown in one request."""
    content = await file.read()
    result = PdfToMarkdownTool.convert_bytes(content)
    return PdfToMdResponse(**result)
