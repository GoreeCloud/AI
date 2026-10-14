#!/usr/bin/env python3
"""Offline one-shot request validation: fail closed, no model service contacted."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from test_local_model_gateway import FakeOllama

ROOT = Path(__file__).resolve().parents[1]


class OfflineValidationTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, b'{"models":[]}', {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def command(self, raw=b"PRIVATE_DEVELOPMENT_PROMPT", *, model="tiny:1", extra=(), endpoint=None):
        args = [
            sys.executable, str(ROOT / "scripts/ai_local.py"),
            "--endpoint", endpoint or self.endpoint, "chat", "--model", model,
            "--validate-only", *extra
        ]
        return subprocess.run(args, input=raw, cwd=ROOT, capture_output=True, timeout=10)

    def assert_no_network(self):
        self.assertEqual(self.server.received, [])
        self.assertEqual(self.server.requests, [])

    def test_success_is_redacted_and_requires_no_inference(self):
        proc = self.command()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {
            "status": "valid", "network_attempted": False,
            "inference_attempted": False, "model_installed_verified": False,
            "processing": "local",
        })
        self.assertNotIn(b"PRIVATE_DEVELOPMENT_PROMPT", proc.stdout + proc.stderr)
        self.assertNotIn(b"tiny:1", proc.stdout + proc.stderr)
        self.assert_no_network()

    def test_stream_option_and_generation_cap_remain_offline(self):
        for mode in (("--stream", "--max-tokens", "1"),
                     ("--max-tokens", "512")):
            with self.subTest(mode=mode):
                proc = self.command(extra=mode)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertFalse(json.loads(proc.stdout)["network_attempted"])
        self.assert_no_network()

    def test_invalid_model_is_rejected_without_disclosure(self):
        proc = self.command(model="private INVALID model")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"invalid_model", proc.stderr)
        self.assertNotIn(b"PRIVATE_DEVELOPMENT_PROMPT", proc.stdout + proc.stderr)
        self.assertNotIn(b"private INVALID model", proc.stdout + proc.stderr)
        self.assert_no_network()

    def test_blank_and_nul_messages_rejected_before_network(self):
        for raw in (b"  \n ", b"SECRET\x00PROMPT"):
            with self.subTest(raw=raw):
                proc = self.command(raw)
                self.assertEqual(proc.returncode, 1)
                self.assertIn(b"invalid_messages", proc.stderr)
                self.assertNotIn(b"SECRET", proc.stdout + proc.stderr)
        self.assert_no_network()

    def test_malformed_utf8_rejected_before_network(self):
        proc = self.command(b"SECRET\xffPROMPT")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"invalid_messages", proc.stderr)
        self.assertNotIn(b"SECRET", proc.stdout + proc.stderr)
        self.assert_no_network()

    def test_oversized_prompt_rejected_before_network(self):
        proc = self.command(b"X" * (16 * 1024 + 1))
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"request_too_large", proc.stderr)
        self.assert_no_network()

    def test_invalid_endpoint_fails_without_network(self):
        proc = self.command(endpoint="http://example.invalid:11434")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"invalid_endpoint", proc.stderr)
        self.assertNotIn(b"PRIVATE_DEVELOPMENT_PROMPT", proc.stderr)
        self.assert_no_network()

    def test_invalid_token_limit_fails_without_network(self):
        for value in ("0", "513", "not-a-number"):
            with self.subTest(value=value):
                proc = self.command(extra=("--max-tokens", value))
                self.assertEqual(proc.returncode, 2)
                self.assertNotIn(b"PRIVATE_DEVELOPMENT_PROMPT", proc.stdout + proc.stderr)
        self.assert_no_network()


if __name__ == "__main__":
    unittest.main()
