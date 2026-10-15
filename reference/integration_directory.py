"""Extensible, non-executing integration directory for GoreeCloud AI Development.

Records represent backend-owned configuration, not user-authorized access.
No credentials, arbitrary URLs, network requests or OAuth flows are handled here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_TRANSPORTS = frozenset({"native", "mcp", "api", "webhook", "plugin"})
_STATES = frozenset({"disconnected", "connected", "disabled"})


class IntegrationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _slug(value: object) -> bool:
    return type(value) is str and _SLUG.fullmatch(value) is not None


@dataclass(frozen=True)
class Integration:
    id: str
    title: str
    transports: tuple[str, ...]
    operations: tuple[str, ...]

    def __post_init__(self):
        if (not _slug(self.id) or type(self.title) is not str
                or not 1 <= len(self.title) <= 96 or "\x00" in self.title
                or type(self.transports) is not tuple
                or not 1 <= len(self.transports) <= 5
                or len(set(self.transports)) != len(self.transports)
                or any(t not in _TRANSPORTS for t in self.transports)
                or type(self.operations) is not tuple
                or not 1 <= len(self.operations) <= 64
                or len(set(self.operations)) != len(self.operations)
                or any(not _slug(op) for op in self.operations)):
            raise IntegrationError("invalid_integration")


@dataclass(frozen=True)
class PublicIntegration:
    id: str
    title: str
    transports: tuple[str, ...]
    connected: bool
    available_operations: tuple[str, ...]


@dataclass(frozen=True)
class PinnedRoute:
    """Backend-only routing information. Never put into model context."""
    service: str
    connection_id: str
    transport: str
    operation: str


class IntegrationDirectory:
    """Trusted operator populates the catalog, then links approved connections.

    The AI gets a filtered public view, never backend connection IDs. Execution
    must still pass Identity/Policy, per-resource authorization and approval.
    """
    def __init__(self):
        self._definitions: dict[str, Integration] = {}
        self._connections: dict[str, tuple[str, str, str]] = {}

    def register(self, definition: Integration):
        if type(definition) is not Integration:
            raise IntegrationError("invalid_integration")
        if definition.id in self._definitions:
            raise IntegrationError("duplicate_integration")
        self._definitions[definition.id] = definition

    def bind(self, service: str, *, connection_id: str, transport: str,
             state: str = "connected"):
        """Trusted administrative action; not callable from a model tool."""
        if service not in self._definitions:
            raise IntegrationError("unknown_integration")
        definition = self._definitions[service]
        if (not _slug(connection_id) or type(transport) is not str
                or transport not in definition.transports
                or type(state) is not str or state not in _STATES):
            raise IntegrationError("invalid_connection")
        self._connections[service] = (connection_id, transport, state)

    def disable(self, service: str):
        if service not in self._definitions:
            raise IntegrationError("unknown_integration")
        self._connections.pop(service, None)

    def list_for(self, permitted_services: frozenset[str],
                 permitted_operations: frozenset[str]) -> tuple[PublicIntegration, ...]:
        if type(permitted_services) is not frozenset or type(permitted_operations) is not frozenset:
            raise IntegrationError("invalid_permissions")
        views = []
        for key, definition in sorted(self._definitions.items()):
            if key not in permitted_services:
                continue
            binding = self._connections.get(key)
            active = bool(binding and binding[2] == "connected")
            operations = tuple(op for op in definition.operations
                               if active and f"{key}:{op}" in permitted_operations)
            views.append(PublicIntegration(key, definition.title, definition.transports,
                                           active, operations))
        return tuple(views)

    def resolve(self, service: str, operation: str, *,
                permitted_services: frozenset[str],
                permitted_operations: frozenset[str]) -> PinnedRoute:
        """Resolve only backend-approved service and operation, without execution."""
        if type(permitted_services) is not frozenset or type(permitted_operations) is not frozenset:
            raise IntegrationError("invalid_permissions")
        definition = self._definitions.get(service)
        if definition is None or service not in permitted_services:
            raise IntegrationError("integration_unavailable")
        binding = self._connections.get(service)
        if (binding is None or binding[2] != "connected"
                or operation not in definition.operations
                or f"{service}:{operation}" not in permitted_operations):
            raise IntegrationError("integration_unavailable")
        return PinnedRoute(service, binding[0], binding[1], operation)


EXAMPLE_SERVICES = (
    Integration("github", "GitHub", ("mcp", "api", "plugin"), ("repos.read", "issues.write", "pulls.write")),
    Integration("gitlab", "GitLab", ("mcp", "api", "plugin"), ("repos.read", "merge-requests.write")),
    Integration("tinyfish", "TinyFish", ("mcp", "api", "plugin"), ("browser.run",)),
    Integration("remote-desktop-commander", "Remote Desktop Commander", ("mcp", "plugin"), ("files.read", "process.run")),
    Integration("dropbox", "Dropbox", ("mcp", "api", "plugin"), ("files.read", "files.write")),
    Integration("google-drive", "Google Drive", ("mcp", "api", "plugin"), ("files.read", "files.write")),
    Integration("todoist", "Todoist", ("mcp", "api", "plugin"), ("tasks.read", "tasks.write")),
    Integration("linear", "Linear", ("mcp", "api", "plugin"), ("issues.read", "issues.write")),
    Integration("sentry", "Sentry", ("mcp", "api", "plugin"), ("errors.read",)),
    Integration("gmail", "Gmail", ("mcp", "api", "plugin"), ("mail.read", "mail.send")),
    Integration("notion", "Notion", ("mcp", "api", "plugin"), ("pages.read", "pages.write")),
)


def example_directory() -> IntegrationDirectory:
    """Examples are DISCONNECTED until the owning backend binds them."""
    directory = IntegrationDirectory()
    for definition in EXAMPLE_SERVICES:
        directory.register(definition)
    return directory
