"""All-or-nothing construction of a development-only approved capability catalog.

Caller must obtain manifest bytes and independently authenticated digest pins
from a trusted operator-controlled source. Building never mutates an existing
catalog, binds connections, grants permissions or performs live service work.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from reference.capability_manifest import ManifestError, parse_pinned_manifest
from reference.capability_requirements import RequirementCatalog, RequirementError
from reference.integration_directory import IntegrationDirectory, IntegrationError

_MAX_MANIFESTS = 2048
_MAX_OPERATIONS = 65536


class CatalogError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PinnedManifest:
    source: bytes
    expected_sha256: str


@dataclass(frozen=True)
class CatalogRevision:
    service: str
    manifest_sha256: str
    revision: str


@dataclass(frozen=True)
class StagedCatalog:
    """New disconnected registries, ready for an external controlled swap.

    This frozen record does NOT make the contained mutable Python registries
    immutable or safe to publish across untrusted threads/processes.
    """
    directory: IntegrationDirectory
    requirements: RequirementCatalog
    revisions: tuple[CatalogRevision, ...]
    catalog_sha256: str


def build_staged_catalog(sources: tuple[PinnedManifest, ...]) -> StagedCatalog:
    """Parse every operator-pinned source into entirely new registries.

    No partly assembled catalog is returned if any source is untrusted,
    incompatible, duplicated, malformed, or outside configured limits.
    A deployment must still atomically swap a trusted pointer after review.
    """
    if (type(sources) is not tuple
            or not 1 <= len(sources) <= _MAX_MANIFESTS
            or any(type(value) is not PinnedManifest for value in sources)):
        raise CatalogError("invalid_catalog_input")
    try:
        parsed = tuple(parse_pinned_manifest(source.source,
                                            expected_sha256=source.expected_sha256)
                       for source in sources)
    except ManifestError as exc:
        raise CatalogError("manifest_rejected") from exc
    count = sum(len(entry.requirements) for entry in parsed)
    if count > _MAX_OPERATIONS:
        raise CatalogError("catalog_too_large")
    directory = IntegrationDirectory()
    requirements = RequirementCatalog()
    revisions = []
    try:
        for entry in parsed:
            directory.register(entry.definition)
            for operation in entry.requirements:
                requirements.register(operation)
            revisions.append(CatalogRevision(
                entry.definition.id, entry.content_sha256,
                entry.requirements[0].revision,
            ))
    except (IntegrationError, RequirementError) as exc:
        raise CatalogError("conflicting_catalog") from exc
    revisions.sort(key=lambda entry: entry.service)
    metadata = [[r.service, r.revision, r.manifest_sha256] for r in revisions]
    catalog_bytes = json.dumps(metadata, ensure_ascii=True,
                               separators=(",", ":")).encode("ascii")
    return StagedCatalog(directory, requirements, tuple(revisions),
                         hashlib.sha256(catalog_bytes).hexdigest())
