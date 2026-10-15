"""Permission-filtered, non-executing discovery of backend-pinned capabilities.

No credentials, arbitrary network endpoints, tool execution, authentication,
manifest signature verification, or model-authored registration occur here.
The caller must supply permissions established by trusted backend authorities.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from reference.integration_directory import IntegrationDirectory, IntegrationError
from reference.capability_requirements import RequirementCatalog, RequirementError

_CURSOR = re.compile(r"^[a-z][a-z0-9_.-]{0,95}:[a-z][a-z0-9_.-]{0,95}$")


class DiscoveryError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CapabilityDescriptor:
    """Safe metadata only; must not include connection or credential identifiers."""
    service: str
    operation: str
    title: str
    transport: str
    minimum_risk: str
    requirement_revision: str


@dataclass(frozen=True)
class DiscoveryPage:
    capabilities: tuple[CapabilityDescriptor, ...]
    next_cursor: str | None


def discover(
    directory: IntegrationDirectory,
    requirements: RequirementCatalog,
    *,
    permitted_services: frozenset[str],
    permitted_operations: frozenset[str],
    page_size: int = 50,
    after: str | None = None,
) -> DiscoveryPage:
    """List only connected, permitted, requirement-backed operations.

    Keyset cursors are public metadata for browsing, not authorization tokens.
    A changed directory may alter subsequent pages; callers should repeat
    discovery after an administrative configuration or permission change.
    """
    if (type(directory) is not IntegrationDirectory
            or type(requirements) is not RequirementCatalog
            or type(permitted_services) is not frozenset
            or type(permitted_operations) is not frozenset
            or type(page_size) is not int or not 1 <= page_size <= 100
            or (after is not None and (type(after) is not str
                                       or _CURSOR.fullmatch(after) is None))):
        raise DiscoveryError("invalid_discovery")
    try:
        visible = directory.list_for(permitted_services, permitted_operations)
        capabilities = []
        for item in visible:
            if not item.connected:
                continue
            for operation in item.available_operations:
                try:
                    route = directory.resolve(
                        item.id, operation,
                        permitted_services=permitted_services,
                        permitted_operations=permitted_operations,
                    )
                    requirement = requirements.resolve(item.id, operation, route.transport)
                except (IntegrationError, RequirementError):
                    # A disconnected or unapproved capability must not be advertised.
                    continue
                capabilities.append(CapabilityDescriptor(
                    item.id, operation, item.title, route.transport,
                    requirement.minimum_risk, requirement.revision,
                ))
        capabilities.sort(key=lambda c: (c.service, c.operation))
        if after is not None:
            capabilities = [c for c in capabilities
                            if f"{c.service}:{c.operation}" > after]
        batch = tuple(capabilities[:page_size])
        cursor = (f"{batch[-1].service}:{batch[-1].operation}"
                  if len(capabilities) > page_size and batch else None)
        return DiscoveryPage(batch, cursor)
    except (IntegrationError, RequirementError, TypeError, ValueError) as exc:
        raise DiscoveryError("discovery_unavailable") from exc
