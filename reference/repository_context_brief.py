#!/usr/bin/env python3
"""Bounded, attributable read-only previews of accepted GoreeCloud Code context.

This source-only Development adapter does not fetch links, execute commands,
authorize repository changes, or elevate repository-controlled text into policy.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hmac import compare_digest
from typing import Mapping
from unicodedata import category
from urllib.parse import urlsplit, urlunsplit

from reference.code_repository_context import (
    RepositoryContextIntakeResult,
    RepositoryContextTarget,
    evaluate_repository_context,
    repository_context_fingerprint,
)
from reference.repository_context_selection import select_repository_context

MAX_BRIEF_ITEMS = 8
MAX_EXCERPT_CHARS = 280
UNTRUSTED = "untrusted_repository_data"


@dataclass(frozen=True)
class RepositoryBriefItem:
    citation_id: str
    kind: str
    identifier: str
    excerpt: str
    evidence_url: str
    attribution_scope: str
    relevance_score: int
    content_trust: str = UNTRUSTED

    def as_dict(self) -> dict:
        return {
            "citation_id": self.citation_id,
            "kind": self.kind,
            "identifier": self.identifier,
            "excerpt": self.excerpt,
            "evidence_url": self.evidence_url,
            "attribution_scope": self.attribution_scope,
            "relevance_score": self.relevance_score,
            "content_trust": self.content_trust,
        }


@dataclass(frozen=True)
class RepositoryContextBrief:
    repository: str
    generated_at: str
    source_provider: str
    items: tuple[RepositoryBriefItem, ...]
    content_trust: str = UNTRUSTED
    execution_authorized: bool = False
    write_authorized: bool = False

    def as_dict(self) -> dict:
        return {
            "repository": self.repository,
            "generated_at": self.generated_at,
            "source_provider": self.source_provider,
            "items": [item.as_dict() for item in self.items],
            "content_trust": self.content_trust,
            "execution_authorized": self.execution_authorized,
            "write_authorized": self.write_authorized,
        }


def _display_text(value: str, limit: int) -> str:
    # Collapse line breaks and remove invisible format/bidi and control chars;
    # repository-controlled text stays explicitly untrusted even after cleanup.
    printable = "".join(" " if category(ch) == "Cc" else
                        "" if category(ch) == "Cf" else ch for ch in value)
    return " ".join(printable.split())[:limit]


def _public_link(value: str) -> str | None:
    """Return a navigation-only URL without query/fragment credentials.

    This never performs network access. A malformed or credential-bearing URL
    is omitted rather than included as a clickable citation.
    """
    if not isinstance(value, str) or len(value) > 4096:
        return None
    if any(ch.isspace() or category(ch) in {"Cc", "Cf"} or ch == "\\" for ch in value):
        return None
    try:
        url = urlsplit(value)
        host = url.hostname
        port = url.port
    except ValueError:
        return None
    if (
        url.scheme not in {"http", "https"}
        or not host
        or any(ch.isspace() for ch in host)
        or url.username is not None
        or url.password is not None
        or (port is not None and not 1 <= port <= 65535)
    ):
        return None
    return urlunsplit((url.scheme, url.netloc, url.path, "", ""))


def build_repository_brief(
    intake: RepositoryContextIntakeResult,
    query: str,
    *,
    now: datetime | None = None,
    limit: int = MAX_BRIEF_ITEMS,
) -> RepositoryContextBrief:
    """Format relevance-ranked context as safe, explicitly untrusted evidence.

    Requires a previously accepted intake and never calls a provider or tool.
    This is a Development presentation boundary, not an Identity permission
    check, authorization for inference, or permission to access repository data.
    """
    decision = intake.decision
    if (
        not decision.accepted
        or intake.context is None
        or decision.content_trust != UNTRUSTED
        or decision.execution_authorized
        or decision.write_authorized
    ):
        raise ValueError("non_authorizing_accepted_context_required")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_BRIEF_ITEMS:
        raise ValueError("invalid_repository_brief_limit")

    # Intake acceptance is time-bound and its context is otherwise mutable.
    # Recheck exact captured bytes, original target and freshness at use time.
    if not isinstance(intake.target, RepositoryContextTarget):
        raise ValueError("repository_brief_target_required")
    if not isinstance(intake.snapshot_sha256, str) or len(intake.snapshot_sha256) != 64:
        raise ValueError("repository_brief_snapshot_unsealed")
    try:
        snapshot = deepcopy(dict(intake.context))
        fingerprint = repository_context_fingerprint(snapshot)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("repository_brief_snapshot_changed") from None
    if not compare_digest(fingerprint, intake.snapshot_sha256):
        raise ValueError("repository_brief_snapshot_changed")
    fresh = evaluate_repository_context(snapshot, intake.target, now=now)
    if (
        not fresh.accepted
        or fresh.generated_at != decision.generated_at
        or fresh.source_provider != decision.source_provider
    ):
        raise ValueError("repository_brief_snapshot_revalidation_failed")

    repo = snapshot.get("repository")
    if not isinstance(repo, Mapping):
        raise ValueError("repository_identity_required")
    owner, name = repo.get("owner"), repo.get("name")
    if not isinstance(owner, str) or not isinstance(name, str) or not owner or not name:
        raise ValueError("repository_identity_required")
    if not decision.generated_at or not decision.source_provider:
        raise ValueError("repository_provenance_required")

    verified = RepositoryContextIntakeResult(
        decision=fresh,
        context=snapshot,
        target=intake.target,
        snapshot_sha256=intake.snapshot_sha256,
    )
    selected = select_repository_context(verified, query, limit=limit)
    items = []
    for candidate in selected:
        safe_link = _public_link(candidate.web_url)
        if safe_link is None:
            continue
        excerpt = _display_text(candidate.text, MAX_EXCERPT_CHARS)
        identifier = _display_text(candidate.key, 256)
        if not excerpt or not identifier:
            continue
        items.append(RepositoryBriefItem(
            citation_id=f"repo-{len(items) + 1}",
            kind=candidate.kind,
            identifier=identifier,
            excerpt=excerpt,
            evidence_url=safe_link,
            attribution_scope="repository_fallback" if candidate.kind in {"branch", "repository"} else "item",
            relevance_score=candidate.score,
        ))
    return RepositoryContextBrief(
        repository=f"{_display_text(owner, 256)}/{_display_text(name, 256)}",
        generated_at=decision.generated_at,
        source_provider=_display_text(decision.source_provider, 256),
        items=tuple(items),
    )
