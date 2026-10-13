"""Standalone test coverage for untrusted repository links."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.repository_navigation_url import is_safe_repository_navigation_url


class RepositoryNavigationUrlTests(unittest.TestCase):
    def test_regular_navigation(self):
        for url in (
            "https://code.example.test/GoreeCloud/AI",
            "https://code.example.test:443/GoreeCloud/AI/pulls/39",
            "https://code.example.test/search?q=code&tab=issues",
            "http://localhost:3000/GoreeCloud/AI#files",
            "https://code.example.test/search?q=plans%3Btesting&tab=code",
            "https://code.example.test/search?q=notes%26examples",
            "https://code.example.test/GoreeCloud/AI?view=diff;tab=commits",
        ):
            with self.subTest(url=url):
                self.assertTrue(is_safe_repository_navigation_url(url))

    def test_sensitive_query_or_fragment(self):
        for url in (
            "https://code.example.test/AI?access_token=example",
            "https://code.example.test/AI#refreshToken=example",
            "https://code.example.test/AI?api_key=example",
            "https://code.example.test/AI?X-Amz-Signature=example",
            "https://code.example.test/AI?session_id=example",
            "https://code.example.test/AI?auth=example",
            "https://code.example.test/AI?oauthCode=example",
            "https://code.example.test/AI?access%5Ftoken=example",
            "https://code.example.test/AI?access%255Ftoken=example",
            "https://code.example.test/AI#path?access_token=example",
            "https://code.example.test/AI?tab=files;access_token=example",
            "https://code.example.test/AI#file=readme;session_id=example",
            "https://code.example.test/AI?q=notes%26access_token%3Dexample",
            "https://code.example.test/AI?view=files%3Bapi_key%3Dexample",
            "https://code.example.test/AI#file=readme%26refresh_token%3Dexample",
            "https://code.example.test/AI?q=notes%2526access_token%253Dexample",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_safe_repository_navigation_url(url))

    def test_invalid_urls(self):
        for url in (
            None, "", 12, "file:///tmp/source", "https:///missing-host",
            "https://reader:example@code.example.test/AI",
            "https://code.example.test:bad/AI",
            "https://code.example.test:99999/AI",
            "https://code.example.test/unsafe path",
            "https://code.example.test/unsafe\\path",
            "https://code.example.test/unsafe\npath",
            "https://code.example.test/AI?" + "&".join("p=x" for _ in range(65)),
            "https://code.example.test/AI#" + "&".join("p=x" for _ in range(65)),
            "https://code.example.test/" + "x" * 4096,
        ):
            with self.subTest(url=url):
                self.assertFalse(is_safe_repository_navigation_url(url))


if __name__ == "__main__":
    unittest.main(verbosity=2)
