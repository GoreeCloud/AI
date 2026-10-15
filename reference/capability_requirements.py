"""Trusted operation requirements for the development-only GoreeCloud AI broker.

Backend operators must source, review, pin, and register manifests independently
of model output and service-provided descriptions. This is not a signing,
provenance, credential, or runtime-execution implementation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_RISK = {"read": 0, "write": 1, "sensitive": 2}
_TRANSPORT = frozenset({"native", "mcp", "api", "webhook", "plugin"})


class RequirementError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _id(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


@dataclass(frozen=True)
class OperationRequirement:
    service: str
    operation: str
    minimum_risk: str
    allowed_transports: tuple[str, ...]
    revision: str

    def __post_init__(self) -> None:
        if (not all(_id(value) for value in (self.service, self.operation, self.revision))
                or type(self.minimum_risk) is not str or self.minimum_risk not in _RISK
                or type(self.allowed_transports) is not tuple
                or not 1 <= len(self.allowed_transports) <= len(_TRANSPORT)
                or any(type(value) is not str or value not in _TRANSPORT
                       for value in self.allowed_transports)
                or len(set(self.allowed_transports)) != len(self.allowed_transports)):
            raise RequirementError("invalid_requirement")


class RequirementCatalog:
    """Operator-configured fail-closed requirements; never accepts model grants."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], OperationRequirement] = {}

    def register(self, requirement: OperationRequirement) -> None:
        if type(requirement) is not OperationRequirement:
            raise RequirementError("invalid_requirement")
        key = (requirement.service, requirement.operation)
        if key in self._items:
            raise RequirementError("duplicate_requirement")
        self._items[key] = requirement

    def resolve(self, service: str, operation: str, transport: str) -> OperationRequirement:
        if not all(_id(value) for value in (service, operation)):
            raise RequirementError("untrusted_operation")
        if type(transport) is not str or transport not in _TRANSPORT:
            raise RequirementError("untrusted_transport")
        requirement = self._items.get((service, operation))
        if requirement is None or transport not in requirement.allowed_transports:
            raise RequirementError("requirement_unavailable")
        return requirement


def effective_risk(minimum_risk: str, policy_risk: str) -> str:
    """A Policy decision may elevate risk, never silently downgrade it."""
    if (type(minimum_risk) is not str or minimum_risk not in _RISK
            or type(policy_risk) is not str or policy_risk not in _RISK
            or _RISK[policy_risk] < _RISK[minimum_risk]):
        raise RequirementError("risk_downgrade")
    return policy_risk
