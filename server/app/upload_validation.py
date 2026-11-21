"""Cheap bounded file-signature checks before starting the document parser.

These are denial/dispatch guards, not malware inspection, complete MIME
validation or a substitute for the isolated parser and resource limits.
"""
from fastapi import HTTPException

SUPPORTED_SUFFIXES = frozenset(("pdf", "docx", "txt", "md"))
MAX_INPUT_BYTES = 6_000_000


def preflight_document(data: bytes, suffix: str) -> None:
    """Reject obvious mislabeled/binary uploads before spawning a parser.

    The parser still checks ZIP expansion, encrypted/invalid formats and
    PDF/DOCX document structure under its own subprocess resource bounds.
    """
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(415, "Unsupported document type")
    if not isinstance(data, bytes) or len(data) > MAX_INPUT_BYTES:
        raise HTTPException(413, "Document exceeds 6MB limit")
    if not data:
        raise HTTPException(422, "Document could not be parsed")
    if suffix == "pdf":
        # PDF 1.x and 2.x header; disallow leading scripting/polyglot bytes.
        if (len(data) < 8 or data[:5] != b"%PDF-"
                or data[5] not in (49, 50) or data[6] != 46
                or not 48 <= data[7] <= 57):
            raise HTTPException(422, "Document could not be parsed")
    elif suffix == "docx":
        # Open XML is ZIP-based; no decompression in the API process.
        # The worker validates its archive and required Word structure.
        if not data.startswith(b"PK\x03\x04"):
            raise HTTPException(422, "Document could not be parsed")
    else:
        # Plain text and Markdown are explicitly UTF-8 (optional BOM).
        # Reject byte-oriented/UTF-16/binary content, not harmless Unicode.
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise HTTPException(422, "Document could not be parsed") from exc
        if b"\x00" in data:
            raise HTTPException(422, "Document could not be parsed")
