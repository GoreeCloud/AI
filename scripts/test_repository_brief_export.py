#!/usr/bin/env python3
"""Regression tests for GoreeCloud AI local repository brief export."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.repository_context_brief import RepositoryBriefItem, RepositoryContextBrief, build_repository_brief
from reference.repository_brief_export import export_repository_brief, MAX_EXPORT_CHARS
from scripts.test_repository_context_brief import intake
from scripts.test_code_repository_context import NOW


def sample(items=True):
    evidence = (
        RepositoryBriefItem("repo-1", "issue", "issue:7", "Fix <b>markup</b> [target](bad)",
                            "https://git.example.test/p/7", "item", 3),
        RepositoryBriefItem("repo-2", "branch", "topic/main", "Release notes",
                            "https://git.example.test/p", "repository_fallback", 2),
    ) if items else ()
    return RepositoryContextBrief(
        "GoreeCloud/code", "2026-10-12T20:00:00+00:00", "forgejo", evidence,
    )


class ExportTests(unittest.TestCase):
    def test_real_intake_and_brief_round_trip(self):
        brief = build_repository_brief(intake(), "example", now=NOW)
        exported = export_repository_brief(brief, format="text")
        self.assertIn("[repo-1]", exported)
        self.assertIn("GoreeCloud/code", exported)
        self.assertIn("untrusted repository data", exported)

    def test_text_export_and_attribution(self):
        content = export_repository_brief(sample(), format="text")
        self.assertIn("[repo-1] issue issue:7", content)
        self.assertIn("Attribution: repository_fallback", content)
        self.assertIn("untrusted repository data", content)

    def test_markdown_escapes_markup_and_links(self):
        output = export_repository_brief(sample())
        self.assertIn(r"\<b\>", output)
        self.assertIn(r"\[target\]\(bad\)", output)
        self.assertNotIn("<b>", output)
        self.assertLessEqual(len(output), MAX_EXPORT_CHARS)

    def test_empty_result_is_explicit(self):
        output = export_repository_brief(sample(False))
        self.assertIn("No matching repository evidence", output)
        self.assertNotIn("repo-1", output)

    def test_rejects_elevated_authority_and_format(self):
        with self.assertRaisesRegex(ValueError, "unsupported_repository_brief_export_format"):
            export_repository_brief(sample(), format="html")
        for invalid in (
            replace(sample(), write_authorized=True),
            replace(sample(), execution_authorized=True),
            replace(sample(), content_trust="trusted"),
        ):
            with self.assertRaisesRegex(ValueError, "untrusted_read_only_brief_required"):
                export_repository_brief(invalid)

    def test_rejects_changed_citation_and_url(self):
        original = sample()
        changed = replace(original.items[0], citation_id="repo-9")
        with self.assertRaisesRegex(ValueError, "invalid_repository_brief_export_citation"):
            export_repository_brief(replace(original, items=(changed, original.items[1])))
        changed = replace(original.items[0], evidence_url="https://git.example.test/p/7?extra=1")
        with self.assertRaisesRegex(ValueError, "invalid_repository_brief_export_url"):
            export_repository_brief(replace(original, items=(changed, original.items[1])))

    def test_rejects_multiline_and_wrong_attribution(self):
        original = sample()
        changed = replace(original.items[0], excerpt="one\nanother")
        with self.assertRaisesRegex(ValueError, "invalid_repository_brief_export_field"):
            export_repository_brief(replace(original, items=(changed, original.items[1])))
        changed = replace(original.items[1], attribution_scope="item")
        with self.assertRaisesRegex(ValueError, "invalid_repository_brief_export_attribution"):
            export_repository_brief(replace(original, items=(original.items[0], changed)))

    def test_requires_timezone_and_repeatable_output(self):
        with self.assertRaisesRegex(ValueError, "invalid_repository_brief_export_timestamp"):
            export_repository_brief(replace(sample(), generated_at="2026-10-12T20:00:00"))
        self.assertEqual(export_repository_brief(sample()), export_repository_brief(sample()))

    def test_rejects_more_than_eight_items(self):
        items = tuple(replace(sample().items[0], citation_id=f"repo-{i+1}") for i in range(9))
        with self.assertRaisesRegex(ValueError, "untrusted_read_only_brief_required"):
            export_repository_brief(replace(sample(), items=items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
