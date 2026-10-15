"""Strict, non-executing capability-manifest parser with operator-pinned digests.

This module checks file integrity against an independently supplied pin. It
DOES NOT authenticate the pin's owner, verify signatures, install services,
load credentials, contact endpoints, or grant connector permissions.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import unicodedata
from dataclasses import dataclass
from reference.integration_directory import Integration, IntegrationError
from reference.capability_requirements import OperationRequirement, RequirementError

_SHA = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA = "goreecloud.ai.capability-manifest.v1"
_TOP_KEYS = frozenset({"schema", "service", "title", "revision", "transports", "operations"})
_OP_KEYS = frozenset({"id", "minimum_risk", "transports"})
_MAX_BYTES = 65536


class ManifestError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CapabilityManifest:
    """Reviewed registry input, not a registration or execution authority."""
    definition: Integration
    requirements: tuple[OperationRequirement, ...]
    content_sha256: str


def _object(pairs: list[tuple[str, object]]) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ManifestError("duplicate_key")
        obj[key] = value
    return obj


def _reject_constant(value: str) -> object:
    raise ManifestError("invalid_number")


def parse_pinned_manifest(raw: bytes, *, expected_sha256: str) -> CapabilityManifest:
    """Verify independently operator-pinned bytes, then parse a restrictive schema.

    The backend must authenticate the source of expected_sha256 and verify
    operator review. A model or client providing both the document and pin
    must never be treated as establishing manifest trust.
    """
    if (type(raw) is not bytes or not 1 <= len(raw) <= _MAX_BYTES
            or type(expected_sha256) is not str
            or _SHA.fullmatch(expected_sha256) is None):
        raise ManifestError("invalid_manifest_input")
    content_digest = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(content_digest, expected_sha256):
        raise ManifestError("digest_mismatch")
    try:
        doc = json.loads(raw.decode("utf-8", errors="strict"),
                         object_pairs_hook=_object,
                         parse_constant=_reject_constant)
    except ManifestError:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ManifestError("invalid_json") from exc
    if (type(doc) is not dict or frozenset(doc) != _TOP_KEYS
            or doc["schema"] != _SCHEMA
            or type(doc["title"]) is not str
            or not doc["title"].strip()
            or any(unicodedata.category(ch).startswith("C") for ch in doc["title"])
            or type(doc["transports"]) is not list
            or not 1 <= len(doc["transports"]) <= 5
            or type(doc["operations"]) is not list
            or not 1 <= len(doc["operations"]) <= 64):
        raise ManifestError("invalid_manifest_schema")

    transports = tuple(doc["transports"])
    try:
        definition = Integration(doc["service"], doc["title"], transports,
                                 tuple(op["id"] if type(op) is dict and "id" in op else None
                                       for op in doc["operations"]))
        requirements = []
        for item in doc["operations"]:
            if type(item) is not dict or frozenset(item) != _OP_KEYS:
                raise ManifestError("invalid_operation")
            if type(item["transports"]) is not list:
                raise ManifestError("invalid_operation")
            choices = tuple(item["transports"])
            if any(transport not in transports for transport in choices):
                raise ManifestError("transport_not_declared")
            requirements.append(OperationRequirement(
                doc["service"], item["id"], item["minimum_risk"], choices,
                doc["revision"],
            ))
    except (IntegrationError, RequirementError, TypeError, ValueError) as exc:
        raise ManifestError("invalid_manifest_schema") from exc
    return CapabilityManifest(definition, tuple(requirements), content_digest)
