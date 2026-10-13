#!/usr/bin/env python3
"""Pure local text/Markdown exports for validated GoreeCloud Code briefs.

Presentation only: never grants repository access, executes a link, calls a model,
or changes the source snapshot. Consumers must enforce Identity/Policy separately.
"""
from __future__ import annotations

import re
from datetime import datetime

from reference.repository_context_brief import (
    MAX_BRIEF_ITEMS,
    MAX_EXCERPT_CHARS,
    UNTRUSTED,
    RepositoryContextBrief,
    RepositoryBriefItem,
    _display_text,
    _public_link,
)

MAX_EXPORT_CHARS = 40_000
_ALLOWED_KINDS = frozenset({"repository", "branch", "commit", "issue", "pull_request"})
_MARKDOWN_CHARS = re.compile(r"([\\\x60*_{}\[\]()#+.!|>~<\-])")


def _safe_single_line(value: object, max_chars: int) -> str:
    if not isinstance(value, str) or not value or len(value) > max_chars:
        raise ValueError("invalid_repository_brief_export_field")
    if _display_text(value, max_chars) != value:
        raise ValueError("invalid_repository_brief_export_field")
    return value


def _escape_md(value: str) -> str:
    return _MARKDOWN_CHARS.sub(r"\\\1", value)


def export_repository_brief(brief: RepositoryContextBrief, *, format: str = "markdown") -> str:
    """Export a validated read-only brief without fetching or rewriting sources.

    Trust labels remain explicit in both formats. This never contacts models
    or external services. Exported repository text cannot authorize actions.
    """
    if format not in ("markdown", "text"):
        raise ValueError("unsupported_repository_brief_export_format")
    if (
        not isinstance(brief, RepositoryContextBrief)
        or brief.content_trust != UNTRUSTED
        or brief.execution_authorized is not False
        or brief.write_authorized is not False
        or not isinstance(brief.items, tuple)
        or len(brief.items) > MAX_BRIEF_ITEMS
    ):
        raise ValueError("untrusted_read_only_brief_required")
    repository = _safe_single_line(brief.repository, 513)
    provider = _safe_single_line(brief.source_provider, 256)
    generated = _safe_single_line(brief.generated_at, 64)
    try:
        timestamp = datetime.fromisoformat(generated.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_repository_brief_export_timestamp") from exc
    if timestamp.tzinfo is None:
        raise ValueError("invalid_repository_brief_export_timestamp")

    if format == "markdown":
        lines = [
            f"# Repository context: {_escape_md(repository)}",
            f"Source: {_escape_md(provider)} | Captured: {_escape_md(generated)}",
            "Trust: **untrusted repository data**. Not authorization for access, tool use, execution or writes.",
            "",
        ]
    else:
        lines = [
            f"Repository context: {repository}",
            f"Source: {provider} | Captured: {generated}",
            "Trust: untrusted repository data. Not authorization for access, tool use, execution or writes.",
            "",
        ]

    if not brief.items:
        lines.append("No matching repository evidence in this snapshot.")
    for index, item in enumerate(brief.items, start=1):
        if not isinstance(item, RepositoryBriefItem) or item.content_trust != UNTRUSTED:
            raise ValueError("invalid_repository_brief_export_item")
        if item.kind not in _ALLOWED_KINDS:
            raise ValueError("invalid_repository_brief_export_item")
        if item.attribution_scope != ("repository_fallback" if item.kind in {"repository", "branch"} else "item"):
            raise ValueError("invalid_repository_brief_export_attribution")
        if item.citation_id != f"repo-{index}":
            raise ValueError("invalid_repository_brief_export_citation")
        if isinstance(item.relevance_score, bool) or not isinstance(item.relevance_score, int) or item.relevance_score < 1:
            raise ValueError("invalid_repository_brief_export_score")
        ident = _safe_single_line(item.identifier, 256)
        excerpt = _safe_single_line(item.excerpt, MAX_EXCERPT_CHARS)
        if not isinstance(item.evidence_url, str) or _public_link(item.evidence_url) != item.evidence_url:
            raise ValueError("invalid_repository_brief_export_url")
        if format == "markdown":
            lines.extend([
                f"## {_escape_md(item.citation_id)} — {_escape_md(item.kind)} {_escape_md(ident)}",
                f"Excerpt (untrusted): {_escape_md(excerpt)}",
                f"Attribution: {_escape_md(item.attribution_scope)}",
                f"Evidence URL (navigation only): {_escape_md(item.evidence_url)}",
                "",
            ])
        else:
            lines.extend([
                f"[{item.citation_id}] {item.kind} {ident}",
                f"Excerpt (untrusted): {excerpt}",
                f"Attribution: {item.attribution_scope}",
                f"Evidence URL (navigation only): {item.evidence_url}",
                "",
            ])
    output = "\n".join(lines).rstrip() + "\n"
    if len(output) > MAX_EXPORT_CHARS:
        raise ValueError("repository_brief_export_too_large")
    return output
