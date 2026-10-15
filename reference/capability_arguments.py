"""Bounded canonical JSON arguments for non-executing AI capability planning.

The trusted backend must schema-validate and authorize the same argument object
before using its digest. This does not authenticate a model or perform effects.
Binary, Decimal and out-of-range integers need explicit operation-specific
encoding; no implicit object-to-string conversion is allowed.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field

_MAX_BYTES = 65536
_MAX_DEPTH = 16
_MAX_NODES = 8192
_SAFE_INT = 2**53 - 1


class ArgumentError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CanonicalArguments:
    encoded: bytes = field(repr=False)
    sha256: str


def canonical_arguments(value: object) -> CanonicalArguments:
    """Deterministic backend-Python serialization of a validated JSON object.

    NOT an implementation of RFC 8785 and not portable across independent
    languages without an explicitly matched encoding contract.
    """
    if type(value) is not dict:
        raise ArgumentError("invalid_arguments")
    pending: list[tuple[object, int]] = [(value, 0)]
    seen: set[int] = set()
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > _MAX_NODES or depth > _MAX_DEPTH:
            raise ArgumentError("arguments_too_complex")
        kind = type(item)
        if kind in (dict, list):
            if id(item) in seen:
                raise ArgumentError("arguments_not_tree")
            seen.add(id(item))
            if kind is dict:
                for key, sub in item.items():
                    if type(key) is not str:
                        raise ArgumentError("invalid_arguments")
                    pending.append((sub, depth + 1))
            else:
                pending.extend((sub, depth + 1) for sub in item)
        elif kind is str:
            if any(0xD800 <= ord(ch) <= 0xDFFF for ch in item):
                raise ArgumentError("invalid_arguments")
        elif kind is int:
            if not -_SAFE_INT <= item <= _SAFE_INT:
                raise ArgumentError("unsafe_integer")
        elif kind is float:
            if not math.isfinite(item):
                raise ArgumentError("invalid_arguments")
        elif kind not in (bool, type(None)):
            raise ArgumentError("invalid_arguments")
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ArgumentError("invalid_arguments") from exc
    if len(raw) > _MAX_BYTES:
        raise ArgumentError("arguments_too_large")
    return CanonicalArguments(raw, hashlib.sha256(raw).hexdigest())
