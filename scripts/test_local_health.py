#!/usr/bin/env python3
"""Offline end-to-end tests for the read-only local-model readiness probe."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_local_model_gateway import FakeOllama

ROOT = Path(__file__).resolve().parents[1]


class HealthProbeTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.requests = []
        self.server.received = []
        self.server.reply = (200, b'{"models":[{"name":"tiny:1"}]}', {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def probe(self, *args, endpoint=None):
        return subprocess.run([
            sys.executable, str(ROOT / "scripts/ai_health.py"),
            "--endpoint", self.endpoint if endpoint is None else endpoint,
            *args,
        ], capture_output=True, text=True, timeout=10)

    def test_reachable_with_installed_models_reports_count_without_names(self):
        self.server.reply = (200, json.dumps({
            "models": [{"name": "tiny:1"}, {"name": "other:1"}]
        }).encode(), {})
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 installed model", result.stdout)
        self.assertNotIn("tiny:1", result.stdout)
        self.assertIn("inference not tested", result.stdout)
        self.assertEqual(self.server.received, [("GET", "/api/tags")])
        self.assertEqual(self.server.requests, [])

    def test_matching_installed_model_preflight(self):
        result = self.probe("--model", "tiny:1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("installed", result.stdout)
        self.assertEqual(self.server.received, [("GET", "/api/tags")])

    def test_missing_model_not_ready_without_prompt(self):
        result = self.probe("--model", "absent:1")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not installed", result.stderr)
        self.assertFalse(self.server.requests)
        self.assertEqual(self.server.received, [("GET", "/api/tags")])

    def test_reachable_without_installed_models_is_not_ready(self):
        self.server.reply = (200, b'{"models":[]}', {})
        result = self.probe()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no installed models", result.stderr)

    def test_bad_model_and_endpoint_fail_without_network(self):
        for args in (("--model", "bad model"), ("--model", "bad\nname"),
                     ("--timeout", "0")):
            with self.subTest(args=args):
                result = self.probe(*args)
                self.assertNotEqual(result.returncode, 0)
        for endpoint in ("http://127.0.0.2:11434", "http://example.invalid:11434"):
            with self.subTest(endpoint=endpoint):
                result = self.probe(endpoint=endpoint)
                self.assertEqual(result.returncode, 1)
        self.assertEqual(self.server.received, [])

    def test_runtime_error_and_redirect_sanitized_and_no_fallback(self):
        self.server.reply = (500, b'{"error":"PRIVATE RUNTIME PAYLOAD"}', {})
        result = self.probe()
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("PRIVATE RUNTIME PAYLOAD", result.stderr)
        self.server.reply = (302, b'', {"Location": "https://example.invalid/collect"})
        result = self.probe()
        self.assertEqual(result.returncode, 1)
        self.assertIn("redirect_blocked", result.stderr)
        self.assertEqual(self.server.received, [("GET", "/api/tags")] * 2)

    def test_unavailable_runtime_fails_with_actionable_error(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            unused_port = probe.getsockname()[1]
        result = self.probe(endpoint=f"http://127.0.0.1:{unused_port}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("runtime_unavailable", result.stderr)


if __name__ == "__main__":
    unittest.main()
