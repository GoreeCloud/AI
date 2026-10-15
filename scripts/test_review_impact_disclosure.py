"""Review impact disclosure: secure, read-only synthetic HTML tests."""
import dataclasses
import unittest

import test_local_review_lifecycle as fixtures
from reference.local_review_html import render_review_html
from reference.local_review_lifecycle import ReviewError


class ImpactDisclosureTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.ReviewLifecycleTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_read_disclosure_has_explicit_decline_and_no_action(self):
        review = self.case.draft()
        markup = render_review_html(review)
        self.assertIn("Potential impact", markup)
        self.assertIn("intended to read information", markup)
        self.assertIn("To decline, close this local review", markup)
        self.assertIn("No action has been executed", markup)
        for tag in ("<script", "<form", "<button", "onclick=", "onload="):
            self.assertNotIn(tag, markup.lower())
        self.assertEqual(self.case.reserved(), 0)

    def test_write_discloses_mutation_and_separate_approval(self):
        self.case.operation = "items.write"
        self.case.update_model()
        markup = render_review_html(self.case.draft())
        self.assertIn("may create or change data", markup)
        self.assertIn("separate trusted approval is required", markup)
        self.assertIn("Execution disabled", markup)
        self.assertEqual(self.case.reserved(), 0)

    def test_sensitive_disclosure_does_not_claim_approval(self):
        review = dataclasses.replace(self.case.draft(), risk="sensitive")
        markup = render_review_html(review)
        self.assertIn("sensitive data or a higher-impact operation", markup)
        self.assertNotIn("<form", markup)
        self.assertEqual(self.case.reserved(), 0)

    def test_unknown_risk_is_rejected_instead_of_misrepresented(self):
        review = dataclasses.replace(self.case.draft(), risk="unknown")
        with self.assertRaisesRegex(ReviewError, "invalid_risk"):
            render_review_html(review)


if __name__ == "__main__":
    unittest.main()
