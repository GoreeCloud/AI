"""Document dispatch checks reject mislabeled/binary content before worker spawn.

Synthetic test bytes only; signature checks never claim full MIME safety.
"""
import io

import pytest
from docx import Document
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import upload_validation
from app.main import app

OWNER = {"Authorization": "Bearer synthetic-owner-token"}


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "synthetic-owner-token")


def test_plain_utf8_markdown_and_bom_are_accepted():
    for suffix in ("txt", "md"):
        for data in ("Private café", "Notes\r\nsecond line", "\ufeffValid text"):
            upload_validation.preflight_document(data.encode("utf-8"), suffix)


def test_real_pdf_and_docx_byte_prefix_accepted():
    writer = PdfWriter()
    writer.add_blank_page(width=150, height=150)
    pdf = io.BytesIO()
    writer.write(pdf)
    upload_validation.preflight_document(pdf.getvalue(), "pdf")

    document = Document()
    document.add_paragraph("Only synthetic text")
    docx = io.BytesIO()
    document.save(docx)
    upload_validation.preflight_document(docx.getvalue(), "docx")


@pytest.mark.parametrize("suffix,data,code", [
    ("pdf", b"leading polyglot bytes%PDF-1.7", 422),
    ("pdf", b"%PDF-z.y\n", 422),
    ("pdf", b"not a pdf", 422),
    ("docx", b"PK\x05\x06empty-central-directory", 422),
    ("docx", b"not a DOCX", 422),
    ("txt", b"invalid\xff", 422),
    ("md", b"binary\x00data", 422),
    ("txt", b"\xff\xfeT\x00", 422),
    ("txt", b"", 422),
    ("other", b"some text", 415),
    ("pdf", b"x" * 6_000_001, 413),
])
def test_invalid_dispatch_rejected_with_bounded_generic_error(suffix, data, code):
    with pytest.raises(HTTPException) as error:
        upload_validation.preflight_document(data, suffix)
    assert error.value.status_code == code
    assert "polyglot" not in error.value.detail
    assert "private" not in error.value.detail.lower()


@pytest.mark.parametrize("filename,data", [
    ("report.pdf", b"#!/bin/sh\necho PRIVATE"),
    ("report.docx", b"PK\x05\x06"),
    ("report.txt", b"binary\x00buffer"),
    ("report.md", b"\xff\xfe"),
])
def test_invalid_upload_denied_before_subprocess(filename, data, monkeypatch):
    from app import main as api

    async def forbid_worker(*_args, **_kwargs):
        raise AssertionError("Invalid signature must not spawn a parser")
    monkeypatch.setattr(api, "parse_document_isolated", forbid_worker)
    response = TestClient(app).post(
        "/api/v1/documents/extract", headers=OWNER,
        files={"file": (filename, data, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Document could not be parsed"}


def test_unauthenticated_rejection_precedes_sniffing(monkeypatch):
    from app import main as api

    def forbid_preflight(*_args):
        raise AssertionError("Unauthenticated upload must not reach preflight")
    monkeypatch.setattr(api.upload_validation, "preflight_document", forbid_preflight)
    response = TestClient(app).post(
        "/api/v1/documents/extract",
        files={"file": ("bad.pdf", b"spoofed", "application/pdf")},
    )
    assert response.status_code == 401
