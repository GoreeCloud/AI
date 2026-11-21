"""Resource-limited Linux document parser. Never import through the API process.

This is NOT a sandbox: it shares the operator's filesystem privileges and
network namespace. The separate process reduces parser crash/resource impact.
"""
import io
import json
import os
import resource
import sys
import zipfile

MAX_INPUT_BYTES = 6_000_000
MAX_TEXT_CHARS = 250_000
MAX_DOCX_EXPANSION = 25_000_000
MAX_DOCX_MEMBERS = 500
MAX_PDF_PAGES = 100


class InputTooLarge(Exception):
    pass


def limit_process() -> None:
    os.umask(0o077)
    memory = 512 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (6, 7))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def limited_paragraphs(paragraphs):
    parts = []
    length = 0
    truncated = False
    for paragraph in paragraphs:
        part = paragraph or ""
        if length >= MAX_TEXT_CHARS:
            if part:
                truncated = True
            break
        if parts:
            part = "\n" + part
        remaining = MAX_TEXT_CHARS + 1 - length
        parts.append(part[:remaining])
        length += len(parts[-1])
        if length > MAX_TEXT_CHARS:
            truncated = True
            break
    result = "".join(parts)
    return result[:MAX_TEXT_CHARS], truncated


def extract_pdf(source: bytes) -> tuple[str, bool]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(source))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF unsupported")
    pages = reader.pages
    selected = min(len(pages), MAX_PDF_PAGES)
    text, truncated = limited_paragraphs(
        pages[i].extract_text() or "" for i in range(selected)
    )
    return text, truncated or len(pages) > MAX_PDF_PAGES


def extract_docx(source: bytes) -> tuple[str, bool]:
    from docx import Document

    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_DOCX_MEMBERS:
            raise InputTooLarge()
        expanded = 0
        for info in entries:
            expanded += info.file_size
            if expanded > MAX_DOCX_EXPANSION:
                raise InputTooLarge()
            if info.flag_bits & 1 or info.compress_type not in (
                zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED
            ):
                raise ValueError("Unsupported or encrypted DOCX member")
    doc = Document(io.BytesIO(source))
    return limited_paragraphs(p.text for p in doc.paragraphs)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("pdf", "docx", "txt", "md"):
        return 2
    try:
        limit_process()
        contents = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(contents) > MAX_INPUT_BYTES:
            raise InputTooLarge()
        suffix = sys.argv[1]
        if suffix == "pdf":
            text, truncated = extract_pdf(contents)
        elif suffix == "docx":
            text, truncated = extract_docx(contents)
        else:
            text = contents.decode("utf-8")
            truncated = len(text) > MAX_TEXT_CHARS
            text = text[:MAX_TEXT_CHARS]
        sys.stdout.write(json.dumps({"text": text, "truncated": truncated},
                                    ensure_ascii=False, separators=(",", ":")))
        sys.stdout.flush()
        return 0
    except InputTooLarge:
        sys.stdout.write('{"error":"too_large"}')
    except (Exception, SystemExit):
        # No user content, environment or traceback reaches caller.
        sys.stdout.write('{"error":"invalid"}')
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
