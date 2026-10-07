#!/usr/bin/env python3
"""Query-aware selection for accepted GoreeCloud Code repository file manifests."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from reference.code_repository_file_manifest import RepositoryFileManifestIntakeResult

MAX_QUERY_CHARS = 512
MAX_QUERY_TERMS = 32
MAX_SELECTION_ITEMS = 20


@dataclass(frozen=True)
class RepositoryFileCandidate:
    name: str
    path: str
    type: str
    score: int

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "score": self.score,
        }


def select_repository_file_candidates(
    intake: RepositoryFileManifestIntakeResult,
    query: str,
    *,
    limit: int = 12,
) -> tuple[RepositoryFileCandidate, ...]:
    if not intake.decision.accepted or intake.context is None:
        raise ValueError("accepted_repository_file_manifest_required")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise ValueError("valid_repository_file_query_required")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_SELECTION_ITEMS:
        raise ValueError("invalid_repository_file_selection_limit")

    normalized_query = " ".join(query.lower().split())
    terms = tuple(dict.fromkeys(re.findall(r"[a-z0-9_.:/-]+", normalized_query)))[:MAX_QUERY_TERMS]
    if not terms:
        raise ValueError("valid_repository_file_query_required")

    candidates: list[RepositoryFileCandidate] = []
    for entry in _items(intake.context.get("entries")):
        name = entry.get("name")
        path = entry.get("path")
        entry_type = entry.get("type")
        if not isinstance(name, str) or not isinstance(path, str) or not isinstance(entry_type, str):
            continue
        normalized_path = path.lower()
        normalized_name = name.lower()
        score = sum(normalized_path.count(term) + normalized_name.count(term) for term in terms)
        if normalized_query in normalized_path:
            score += max(2, len(terms))
        if score <= 0:
            continue
        candidates.append(RepositoryFileCandidate(name=name, path=path, type=entry_type, score=score))

    candidates.sort(key=lambda item: (-item.score, _type_order(item.type), item.path))
    return tuple(candidates[:limit])


def _items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _type_order(value: str) -> int:
    return {"file": 0, "directory": 1, "symlink": 2, "submodule": 3, "unknown": 4}.get(value, 99)
