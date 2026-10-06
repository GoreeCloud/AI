#!/usr/bin/env python3
"""Query-aware selection for accepted GoreeCloud Code repository context."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from reference.code_repository_context import RepositoryContextIntakeResult

MAX_QUERY_CHARS = 512
MAX_QUERY_TERMS = 32
MAX_RESULT_TEXT_CHARS = 600


@dataclass(frozen=True)
class RepositoryContextCandidate:
    kind: str
    key: str
    text: str
    web_url: str
    score: int

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "key": self.key,
            "text": self.text,
            "web_url": self.web_url,
            "score": self.score,
        }


def select_repository_context(
    intake: RepositoryContextIntakeResult,
    query: str,
    *,
    limit: int = 8,
) -> tuple[RepositoryContextCandidate, ...]:
    if not intake.decision.accepted or intake.context is None:
        raise ValueError("accepted_repository_context_required")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise ValueError("valid_repository_query_required")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("invalid_repository_context_selection_limit")

    normalized_query = " ".join(query.lower().split())
    terms = tuple(dict.fromkeys(re.findall(r"[a-z0-9_.:/-]+", normalized_query)))[:MAX_QUERY_TERMS]
    if not terms:
        raise ValueError("valid_repository_query_required")

    context = intake.context
    repository = _mapping(context.get("repository"))
    repository_url = repository.get("webUrl") if isinstance(repository.get("webUrl"), str) else ""
    candidates: list[RepositoryContextCandidate] = []

    description = repository.get("description")
    if isinstance(description, str) and description:
        candidates.append(_candidate("repository", str(repository.get("id") or "repository"), description, repository_url, normalized_query, terms))

    for branch in _items(context.get("branches")):
        name = branch.get("name")
        if isinstance(name, str) and name:
            candidates.append(_candidate("branch", name, name, repository_url, normalized_query, terms))

    for commit in _items(context.get("commits")):
        sha = commit.get("sha")
        message = commit.get("message")
        if isinstance(sha, str) and isinstance(message, str):
            author = commit.get("authorName")
            text = f"{message} {author}" if isinstance(author, str) and author else message
            candidates.append(_candidate("commit", sha, text, _web_url(commit, repository_url), normalized_query, terms))

    for issue in _items(context.get("issues")):
        number = issue.get("number")
        title = issue.get("title")
        if isinstance(number, int) and not isinstance(number, bool) and isinstance(title, str):
            candidates.append(_candidate("issue", f"issue:{number}", title, _web_url(issue, repository_url), normalized_query, terms))

    for pull_request in _items(context.get("pullRequests")):
        number = pull_request.get("number")
        title = pull_request.get("title")
        if isinstance(number, int) and not isinstance(number, bool) and isinstance(title, str):
            base = pull_request.get("base")
            head = pull_request.get("head")
            refs = " ".join(value for value in (base, head) if isinstance(value, str))
            text = f"{title} {refs}".strip()
            candidates.append(_candidate("pull_request", f"pull:{number}", text, _web_url(pull_request, repository_url), normalized_query, terms))

    ranked = [candidate for candidate in candidates if candidate.score > 0]
    ranked.sort(key=lambda candidate: (-candidate.score, _kind_order(candidate.kind), candidate.key))
    return tuple(ranked[:limit])


def _candidate(
    kind: str,
    key: str,
    text: str,
    web_url: str,
    normalized_query: str,
    terms: tuple[str, ...],
) -> RepositoryContextCandidate:
    normalized_text = " ".join(text.lower().split())
    score = sum(normalized_text.count(term) for term in terms)
    if normalized_query in normalized_text:
        score += max(2, len(terms))
    return RepositoryContextCandidate(
        kind=kind,
        key=key,
        text=text[:MAX_RESULT_TEXT_CHARS],
        web_url=web_url,
        score=score,
    )


def _items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _web_url(value: Mapping[str, object], fallback: str) -> str:
    candidate = value.get("webUrl")
    return candidate if isinstance(candidate, str) else fallback


def _kind_order(kind: str) -> int:
    return {
        "repository": 0,
        "branch": 1,
        "commit": 2,
        "issue": 3,
        "pull_request": 4,
    }.get(kind, 99)
