"""Standalone offline canonical payload tests. No external service calls."""
import unittest

from reference.capability_arguments import ArgumentError, canonical_arguments


class CanonicalArgumentsTests(unittest.TestCase):
    def test_stable_key_order(self):
        a = canonical_arguments({"b": [False, None, 1.5], "a": 3})
        b = canonical_arguments({"a": 3, "b": [False, None, 1.5]})
        self.assertEqual(a.sha256, b.sha256)
        self.assertEqual(a.encoded, b.encoded)

    def test_changes_produce_distinct_digests(self):
        self.assertNotEqual(canonical_arguments({"page": 1}).sha256,
                            canonical_arguments({"page": 2}).sha256)
        self.assertNotEqual(canonical_arguments({"page": 1}).sha256,
                            canonical_arguments({"page": 1, "write": True}).sha256)

    def test_invalid_types_and_numbers(self):
        for value in ([], "text", {"bad": object()}, {"bad": float("nan")},
                      {"bad": float("inf")}, {"bad": 2**54},
                      {3: "integer-key"}, {"bad": ("list",)}):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ArgumentError):
                    canonical_arguments(value)

    def test_bounds_and_graph_cycles(self):
        deep = {}
        ref = deep
        for i in range(18):
            ref["x"] = {}
            ref = ref["x"]
        cycle = {}
        cycle["self"] = cycle
        for data in ({"value": "x" * 65536}, {"deep": deep}, {"cycle": cycle}):
            with self.assertRaises(ArgumentError):
                canonical_arguments(data)

    def test_invalid_unicode(self):
        with self.assertRaises(ArgumentError):
            canonical_arguments({"message": chr(0xD800)})


if __name__ == "__main__":
    unittest.main()
