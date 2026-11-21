"""Untrusted uploads are parsed in a separate limited Linux process, not ASGI."""
import asyncio
import io
import os

import pytest
from docx import Document
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import main as api

os.environ["GOREECLOUD_AI_TOKEN"] = "test-owner-token"
OWNER = {"Authorization": "Bearer test-owner-token"}
client = TestClient(api.app)


def test_plain_text_worker_preserves_unicode():
    response = client.post(
        "/api/v1/documents/extract", headers=OWNER,
        files={"file": ("notes.txt", "Private café notes".encode(),
                        "text/plain")})
    assert response.status_code == 200
    assert response.json() == {
        "name": "notes.txt", "text": "Private café notes", "truncated": False
    }


def test_docx_worker_roundtrip():
    doc = Document()
    doc.add_paragraph("A private but synthetic test note.")
    payload = io.BytesIO()
    doc.save(payload)
    response = client.post(
        "/api/v1/documents/extract", headers=OWNER,
        files={"file": ("sample.docx", payload.getvalue(),
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code == 200
    assert response.json()["text"] == "A private but synthetic test note."


def test_pdf_worker_smoke():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    payload = io.BytesIO()
    writer.write(payload)
    response = client.post("/api/v1/documents/extract", headers=OWNER,
                           files={"file": ("sample.pdf", payload.getvalue(), "application/pdf")})
    assert response.status_code == 200
    assert response.json()["text"] == ""


@pytest.mark.parametrize("name,content", [
    ("invalid.pdf", b"not a pdf"),
    ("invalid.docx", b"not a DOCX"),
    ("invalid.md", b"\xff\xfe"),
])
def test_malformed_document_fails_closed(name, content):
    response = client.post("/api/v1/documents/extract", headers=OWNER,
                           files={"file": (name, content, "application/octet-stream")})
    assert response.status_code == 422
    assert response.json()["detail"] == "Document could not be parsed"


def test_document_without_owner_cannot_trigger_worker(monkeypatch):
    async def unneeded(*_args, **_kwargs):
        raise AssertionError("Unauthenticated users must not execute a worker")
    monkeypatch.setattr(api.asyncio, "create_subprocess_exec", unneeded)
    response = client.post("/api/v1/documents/extract",
                           files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_worker_timeout_kills_process_and_scrubs_secrets(monkeypatch):
    class FakeSlowProcess:
        returncode = None
        killed = False

        async def communicate(self, input):
            await asyncio.sleep(0.5)
            return b"{}", b""

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            return self.returncode

    process = FakeSlowProcess()
    monkeypatch.setenv("OPENROUTER_API_KEY", "never-propagated")
    async def fake_spawn(*args, **kwargs):
        assert args[1] == "-I"
        assert kwargs["env"].get("OPENROUTER_API_KEY") is None
        assert kwargs["env"].get("GOREECLOUD_AI_TOKEN") is None
        return process
    monkeypatch.setattr(api.asyncio, "create_subprocess_exec", fake_spawn)
    with pytest.raises(HTTPException) as error:
        await api.parse_document_isolated(b"synthetic", "txt", timeout_seconds=0.01)
    assert error.value.status_code == 408
    assert process.killed


@pytest.mark.asyncio
async def test_worker_output_rejected_if_unbounded(monkeypatch):
    class FakeLargeOutput:
        returncode = 0

        async def communicate(self, input):
            return b"x" * 1_200_001, b""
    async def fake_spawn(*args, **kwargs):
        return FakeLargeOutput()
    monkeypatch.setattr(api.asyncio, "create_subprocess_exec", fake_spawn)
    with pytest.raises(HTTPException) as error:
        await api.parse_document_isolated(b"synthetic", "txt")
    assert error.value.status_code == 502


@pytest.mark.asyncio
async def test_worker_cancel_propagates_and_process_is_killed(monkeypatch):
    class FakeRunning:
        returncode = None
        killed = False
        async def communicate(self, input):
            await asyncio.Event().wait()

        def kill(self):
            self.killed = True
            self.returncode = -9

        async def wait(self):
            return self.returncode

    process = FakeRunning()
    async def fake_spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(api.asyncio, "create_subprocess_exec", fake_spawn)
    task = asyncio.create_task(api.parse_document_isolated(b"test", "txt", timeout_seconds=60))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.killed



@pytest.mark.asyncio
async def test_document_import_capacity_rejects_parallel_surge(monkeypatch):
    from fastapi import UploadFile

    slots = asyncio.Semaphore(1)
    monkeypatch.setattr(api, "import_slots", slots)
    await slots.acquire()
    try:
        with pytest.raises(HTTPException) as error:
            await api.extract_document(UploadFile(filename="test.txt",
                                                  file=io.BytesIO(b"synthetic")))
        assert error.value.status_code == 429
    finally:
        slots.release()
    assert slots._value == 1
