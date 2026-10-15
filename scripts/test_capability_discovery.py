"""Synthetic, network-free tests for permission-filtered capability discovery."""
import dataclasses
import unittest

from reference.capability_discovery import DiscoveryError, discover
from reference.capability_requirements import OperationRequirement, RequirementCatalog
from reference.integration_directory import Integration, IntegrationDirectory


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = IntegrationDirectory()
        self.directory.register(Integration("github", "GitHub", ("mcp", "api"),
                                            ("repos.read", "issues.write", "pulls.write")))
        self.directory.register(Integration("mail", "Mail", ("mcp",),
                                            ("messages.read", "messages.send")))
        self.directory.bind("github", connection_id="hidden-gh-id", transport="mcp")
        self.directory.bind("mail", connection_id="hidden-mail-id", transport="mcp")
        self.requirements = RequirementCatalog()
        for service, op, risk in (
            ("github", "repos.read", "read"),
            ("github", "issues.write", "write"),
            ("github", "pulls.write", "sensitive"),
            ("mail", "messages.read", "read"),
            ("mail", "messages.send", "sensitive"),
        ):
            self.requirements.register(OperationRequirement(service, op, risk,
                                                            ("mcp",), "v1"))
        self.services = frozenset({"github", "mail"})
        self.operations = frozenset({
            "github:repos.read", "github:issues.write", "github:pulls.write",
            "mail:messages.read", "mail:messages.send",
        })

    def discover(self, **changes):
        args = dict(permitted_services=self.services,
                    permitted_operations=self.operations)
        args.update(changes)
        return discover(self.directory, self.requirements, **args)

    def test_only_authorized_connected_capabilities_appear(self):
        view = self.discover(permitted_services=frozenset({"github"}),
                             permitted_operations=frozenset({"github:repos.read"}))
        self.assertEqual([(c.service, c.operation, c.minimum_risk) for c in view.capabilities],
                         [("github", "repos.read", "read")])
        self.assertEqual(view.next_cursor, None)

    def test_disconnected_and_revoked_are_invisible(self):
        self.directory.disable("mail")
        self.assertEqual(len(self.discover().capabilities), 3)
        self.assertEqual(len(self.discover(permitted_services=frozenset()).capabilities), 0)
        self.assertEqual(len(self.discover(permitted_operations=frozenset()).capabilities), 0)

    def test_missing_requirement_or_transport_change_is_hidden(self):
        catalog = RequirementCatalog()
        catalog.register(OperationRequirement("github", "repos.read", "read", ("mcp",), "v1"))
        page = discover(self.directory, catalog,
                        permitted_services=self.services,
                        permitted_operations=self.operations)
        self.assertEqual([(x.service, x.operation) for x in page.capabilities],
                         [("github", "repos.read")])
        self.directory.bind("github", connection_id="new-id", transport="api")
        page = discover(self.directory, catalog,
                        permitted_services=self.services,
                        permitted_operations=self.operations)
        self.assertEqual(page.capabilities, ())

    def test_no_connection_ids_exposed(self):
        page = self.discover()
        self.assertEqual(len(page.capabilities), 5)
        self.assertTrue(all("connection" not in vars(v) for v in page.capabilities))
        self.assertNotIn("hidden-gh-id", repr(page))
        self.assertEqual({d.requirement_revision for d in page.capabilities}, {"v1"})

    def test_paginated_order_and_last_cursor(self):
        seen = []
        cursor = None
        while True:
            page = self.discover(page_size=2, after=cursor)
            seen.extend((c.service, c.operation) for c in page.capabilities)
            if page.next_cursor is None:
                break
            self.assertNotEqual(cursor, page.next_cursor)
            cursor = page.next_cursor
        self.assertEqual(len(seen), 5)
        self.assertEqual(seen, sorted(set(seen)))
        self.assertEqual(self.discover(page_size=1, after="zzzz:zzzz").capabilities, ())

    def test_invalid_discovery_parameters(self):
        for options in (
            {"page_size": 0},
            {"page_size": 101},
            {"page_size": True},
            {"after": "../bad"},
            {"after": ""},
            {"after": "github:repos.read\n"},
            {"permitted_services": {"github"}},
        ):
            with self.assertRaisesRegex(DiscoveryError, "invalid_discovery"):
                self.discover(**options)

    def test_more_than_one_thousand_capabilities_using_generic_contract(self):
        directory = IntegrationDirectory()
        registry = RequirementCatalog()
        services = set()
        grants = set()
        for i in range(25):
            name = f"service{i:02d}"
            services.add(name)
            operations = tuple(f"op{j:02d}" for j in range(48))
            directory.register(Integration(name, name, ("mcp",), operations))
            directory.bind(name, connection_id=f"internal-{i}", transport="mcp")
            for operation in operations:
                registry.register(OperationRequirement(name, operation, "read",
                                                       ("mcp",), "r1"))
                grants.add(f"{name}:{operation}")
        result = []
        after = None
        while True:
            page = discover(directory, registry, permitted_services=frozenset(services),
                            permitted_operations=frozenset(grants), page_size=100, after=after)
            result.extend(page.capabilities)
            if page.next_cursor is None:
                break
            after = page.next_cursor
        self.assertEqual(len(result), 1200)
        self.assertEqual(len({(x.service, x.operation) for x in result}), 1200)


if __name__ == "__main__":
    unittest.main()
