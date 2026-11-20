"""GoreeCloud AI owner-only API: paid calls and external tools are explicit actions."""
import base64
import binascii
import io
import os
import re
from typing import Literal
from uuid import UUID

from docx import Document
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import mcp_tools, providers, storage
from .security import require_owner

app = FastAPI(title="GoreeCloud AI", version="0.1.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")

origins = [x.strip() for x in os.getenv("GOREeCLOUD_AI_CORS_ORIGINS", "").split(",") if x.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"])


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=50000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=32)
    model: str = Field(default="openrouter/auto", min_length=1, max_length=128)
    provider: Literal["auto", "openrouter", "ollama"] = "auto"
    allow_local_fallback: bool = False


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=5000)
    model: str = Field(default="bytedance-seed/seedream-4.5", min_length=3, max_length=128)
    reference_data_url: str | None = Field(default=None, max_length=8_000_000)
    approve_paid_generation: bool = False


class DocRequest(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    body: str = Field(max_length=250000)


class AgentPlanRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=5000)
    provider: Literal["auto", "openrouter", "ollama"] = "auto"


class AgentRunRequest(BaseModel):
    action: Literal["document.read"]
    document_id: UUID
    approved: bool = False


class MCPToolCall(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    arguments: dict = Field(default_factory=dict)
    approved: bool = False


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "goreecloud-ai", "version": "0.1.0"}


@app.get("/api/v1/models", dependencies=[Depends(require_owner)])
def models():
    return {
        "default": "openrouter/auto", "openrouter_enabled": bool(os.getenv("OPENROUTER_API_KEY")),
        "ollama_enabled": bool(os.getenv("OLLAMA_MODEL")),
        "models": ["openrouter/auto"] + ([os.environ["OLLAMA_MODEL"]] if os.getenv("OLLAMA_MODEL") else []),
        "note": "OpenRouter usage may incur paid model costs. OpenRouter Auto selects the actual model."
    }


@app.post("/api/v1/chat", dependencies=[Depends(require_owner)])
async def chat(request: ChatRequest):
    return await providers.chat([m.model_dump() for m in request.messages],
                                request.model, request.provider, request.allow_local_fallback)


def checked_reference(value: str | None) -> str | None:
    if not value:
        return None
    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})", value)
    if not match:
        raise HTTPException(422, "Reference must be a base64 PNG, JPEG or WebP data URL")
    try:
        binary = base64.b64decode(match.group(2), validate=True)
    except binascii.Error as exc:
        raise HTTPException(422, "Invalid reference image encoding") from exc
    if len(binary) > 5_000_000 or len(binary) < 8:
        raise HTTPException(413, "Reference image size is not supported")
    if not (binary.startswith(b"\x89PNG\r\n\x1a\n") or binary.startswith(b"\xff\xd8\xff")
            or binary.startswith(b"RIFF") and binary[8:12] == b"WEBP"):
        raise HTTPException(422, "Reference is not a supported image")
    return value


@app.post("/api/v1/images", dependencies=[Depends(require_owner)])
async def images(request: ImageRequest):
    if not request.approve_paid_generation:
        raise HTTPException(403, "Image requests require explicit paid-call approval")
    return await providers.image_request(request.prompt, request.model,
                                         checked_reference(request.reference_data_url))


@app.get("/api/v1/documents", dependencies=[Depends(require_owner)])
def list_documents():
    return storage.list_documents()


@app.post("/api/v1/documents", dependencies=[Depends(require_owner)], status_code=201)
def create_document(request: DocRequest):
    return storage.create_document(request.title, request.body)


@app.get("/api/v1/documents/{document_id}", dependencies=[Depends(require_owner)])
def read_document(document_id: UUID):
    result = storage.get_document(str(document_id))
    if not result:
        raise HTTPException(404, "Document not found")
    return result


@app.put("/api/v1/documents/{document_id}", dependencies=[Depends(require_owner)])
def edit_document(document_id: UUID, request: DocRequest):
    result = storage.update_document(str(document_id), request.title, request.body)
    if not result:
        raise HTTPException(404, "Document not found")
    return result


@app.get("/api/v1/documents/{document_id}/export", dependencies=[Depends(require_owner)])
def export_document(document_id: UUID, format: Literal["md", "docx"] = "md"):
    item = storage.get_document(str(document_id))
    if not item:
        raise HTTPException(404, "Document not found")
    filename = re.sub(r"[^a-zA-Z0-9_-]+", "-", item["title"])[:64] or "document"
    if format == "md":
        payload = item["body"].encode("utf-8")
        media = "text/markdown; charset=utf-8"
    else:
        doc = Document()
        doc.add_heading(item["title"], 0)
        for line in item["body"].splitlines():
            doc.add_paragraph(line)
        buffer = io.BytesIO()
        doc.save(buffer)
        payload = buffer.getvalue()
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(payload, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"',
                             "X-Content-Type-Options": "nosniff"})


@app.post("/api/v1/documents/extract", dependencies=[Depends(require_owner)])
async def extract_document(file: UploadFile = File(...)):
    from pypdf import PdfReader
    contents = await file.read(6_000_001)
    if len(contents) > 6_000_000:
        raise HTTPException(413, "Document exceeds 6MB limit")
    if not file.filename or not file.filename.lower().endswith((".pdf", ".docx", ".txt", ".md")):
        raise HTTPException(415, "Only PDF, DOCX and plain text are supported")
    suffix = file.filename.lower().rsplit(".", 1)[-1]
    try:
        if suffix == "pdf":
            text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(contents)).pages[:100])
        elif suffix == "docx":
            text = "\n".join(p.text for p in Document(io.BytesIO(contents)).paragraphs)
        else:
            text = contents.decode("utf-8")
    except Exception as exc:
        raise HTTPException(422, "Document could not be parsed") from exc
    return {"name": file.filename[:160], "text": text[:250000],
            "truncated": len(text) > 250000}


@app.post("/api/v1/agents/plan", dependencies=[Depends(require_owner)])
async def agent_plan(request: AgentPlanRequest):
    answer = await providers.chat([
        {"role": "system", "content": (
            "You plan tasks for a user-operated assistant. Return a short numbered plan. "
            "You cannot execute tools or claim to have performed actions. "
            "Mark external, destructive and paid steps as requiring explicit approval."
        )},
        {"role": "user", "content": request.goal}
    ], "openrouter/auto", request.provider, False)
    return {"plan": answer["content"], "executed": False, "model": answer["model"]}


@app.post("/api/v1/agents/run", dependencies=[Depends(require_owner)])
def agent_run(request: AgentRunRequest):
    if not request.approved:
        raise HTTPException(403, "Tool action requires explicit approval")
    item = storage.get_document(str(request.document_id))
    if not item:
        raise HTTPException(404, "Document not found")
    return {"action": request.action, "result": item, "executed": True}


@app.get("/api/v1/mcp/tools", dependencies=[Depends(require_owner)])
async def list_mcp_tools():
    return await mcp_tools.access_mcp()


@app.post("/api/v1/mcp/call", dependencies=[Depends(require_owner)])
async def call_mcp_tool(request: MCPToolCall):
    if not request.approved:
        raise HTTPException(403, "MCP tool execution requires explicit approval")
    return await mcp_tools.access_mcp(request.name, request.arguments)
