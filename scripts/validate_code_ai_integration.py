#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "code.repository-context.schema.json"
SOURCE = ROOT / "reference" / "code_repository_context.py"
SELECTOR = ROOT / "reference" / "repository_context_selection.py"
BRIEF = ROOT / "reference" / "repository_context_brief.py"
BRIEF_TESTS = ROOT / "scripts" / "test_repository_context_brief.py"
BRIEF_DOC = ROOT / "docs" / "READ_ONLY_REPOSITORY_BRIEFS.md"
EXPORT = ROOT / "reference" / "repository_brief_export.py"
EXPORT_TESTS = ROOT / "scripts" / "test_repository_brief_export.py"
TESTS = ROOT / "scripts" / "test_code_repository_context.py"
DOC = ROOT / "docs" / "CODE_REPOSITORY_CONTEXT.md"
README = ROOT / "README.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"GoreeCloud AI Code-context validation failed: {message}")


def main() -> None:
    for path in (CONTRACT, SOURCE, SELECTOR, BRIEF, EXPORT, TESTS, BRIEF_TESTS, EXPORT_TESTS, DOC, BRIEF_DOC, README):
        require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}")

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    selector = SELECTOR.read_text(encoding="utf-8")
    brief = BRIEF.read_text(encoding="utf-8")
    export = EXPORT.read_text(encoding="utf-8")
    for token in ("MAX_EXPORT_CHARS = 40_000", "untrusted repository data", "invalid_repository_brief_export_url", "_escape_md", "write_authorized"):
        require(token in export, f"repository export missing invariant: {token}")
    docs = (DOC.read_text(encoding="utf-8") + "\n" + BRIEF_DOC.read_text(encoding="utf-8") + "\n" + README.read_text(encoding="utf-8")).lower()

    properties = contract.get("properties") or {}
    require(properties.get("contractVersion", {}).get("const") == "0.1.0", "unexpected contract version")
    require(properties.get("recordType", {}).get("const") == "repository_context", "unexpected record type")
    require(contract.get("additionalProperties") is False, "top-level contract must reject extra fields")

    producer = properties.get("producer", {}).get("properties") or {}
    require(producer.get("service", {}).get("const") == "goreecloud-code-api", "unexpected producer")
    require(producer.get("authoritative", {}).get("const") is False, "Code envelope must not claim repository authority")

    for collection in ("branches", "commits", "issues", "pullRequests"):
        require(properties.get(collection, {}).get("maxItems") == 20, f"{collection} must remain bounded to 20")

    for token in (
        'CODE_REPOSITORY_CONTEXT_CONTRACT_VERSION = "0.1.0"',
        'MAX_CONTEXT_ITEMS = 20',
        '"repository_context_contains_sensitive_key"',
        "repository_context_fingerprint",
        "snapshot_sha256",
        '"repository_context_stale"',
        '"repository_context_provider_unhealthy"',
        'content_trust: str = "untrusted_repository_data"',
        "execution_authorized: bool = False",
        "write_authorized: bool = False",
    ):
        require(token in source, f"consumer boundary missing invariant: {token}")

    for token in (
        "MAX_QUERY_CHARS = 512",
        "MAX_QUERY_TERMS = 32",
        "MAX_RESULT_TEXT_CHARS = 600",
        "ranked.sort",
    ):
        require(token in selector, f"repository selection missing invariant: {token}")

    for token in ("MAX_BRIEF_ITEMS = 8", "MAX_EXCERPT_CHARS = 280", "untrusted_repository_data", "write_authorized: bool = False", "select_repository_context", "repository_brief_snapshot_changed", "evaluate_repository_context"):
        require(token in brief, f"repository brief missing invariant: {token}")

    for phrase in (
        "provider-neutral",
        "untrusted repository content",
        "not an execution authorization",
        "goreecloud code",
        "forgejo credentials",
        "identity",
        "mesh",
    ):
        require(phrase in docs, f"documentation missing boundary: {phrase}")

    print("GoreeCloud AI repository-context integration validation passed.")


if __name__ == "__main__":
    main()
