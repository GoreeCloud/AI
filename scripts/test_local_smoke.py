#!/usr/bin/env python3
"""Synthetic loopback HTTP/CLI contracts for opt-in local inference smoke test."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SyntheticOllama(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def respond(self):
        self.server.calls.append((self.command, self.path))
        if self.command == "GET":
            code, body = self.server.catalog
        else:
            length = int(self.headers.get("Content-Length", "0"))
            self.server.requests.append(json.loads(self.rfile.read(length)))
            code, body = self.server.answer
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = respond
    do_POST = respond


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SyntheticOllama)
        self.server.catalog = (200, {"models": [{"name": "tiny:1"}]})
        self.server.answer = (200, {
            "model": "tiny:1", "done": True,
            "message": {"role": "assistant", "content": "READY"},
        })
        self.server.calls = []
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_probe(self, *args, endpoint=None):
        return subprocess.run([
            sys.executable, str(ROOT / "scripts/ai_smoke.py"),
            "--endpoint", self.endpoint if endpoint is None else endpoint,
            "--model", "tiny:1", *args,
        ], capture_output=True, text=True, timeout=10)

    def test_one_synthetic_inference_after_catalog_preflight(self):
        result = self.run_probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.server.calls, [("GET", "/api/tags"), ("POST", "/api/chat")])
        self.assertEqual(len(self.server.requests), 1)
        payload = self.server.requests[0]
        self.assertEqual(payload["model"], "tiny:1")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"], [
            {"role": "user", "content": "Reply with the single word READY."}
        ])
        self.assertNotIn("READY", result.stdout)

    def test_structured_success_redacts_model_and_generated_text(self):
        result = self.run_probe("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "code": "ok", "inference_attempted": True,
            "inference_verified": True, "processing": "local", "status": "passed"
        })
        self.assertNotIn("tiny:1", result.stdout)

    def test_missing_model_aborts_before_chat(self):
        self.server.catalog = (200, {"models": []})
        result = self.run_probe("--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["code"], "model_not_installed")
        self.assertFalse(json.loads(result.stdout)["inference_attempted"])
        self.assertEqual(self.server.calls, [("GET", "/api/tags")])

    def test_empty_inference_fails_without_printing_response(self):
        self.server.answer = (200, {
            "model": "tiny:1", "done": True,
            "message": {"role": "assistant", "content": "  "},
        })
        result = self.run_probe("--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["code"], "invalid_inference")
        self.assertTrue(json.loads(result.stdout)["inference_attempted"])
        self.assertFalse(json.loads(result.stdout)["inference_verified"])

    def test_provider_error_payload_is_never_disclosed(self):
        self.server.answer = (500, {"error": "SECRET_PROMPT_OR_MODEL_TEXT"})
        result = self.run_probe("--json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["code"], "runtime_error")
        self.assertNotIn("SECRET_PROMPT_OR_MODEL_TEXT", result.stdout + result.stderr)

    def test_invalid_endpoint_or_model_never_reaches_runtime(self):
        for override in ("http://127.0.0.2:11434", "http://example.invalid:11434"):
            result = self.run_probe(endpoint=override)
            self.assertEqual(result.returncode, 1)
        result = self.run_probe("--model", "invalid model")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.server.calls, [])

    def test_streamed_or_tool_output_is_not_claimed_success(self):
        for body in (
            {"model": "tiny:1", "done": False,
             "message": {"role": "assistant", "content": "partial"}},
            {"model": "tiny:1", "done": True,
             "message": {"role": "assistant", "content": "OK", "tool_calls": []}},
        ):
            with self.subTest(body=body):
                self.server.answer = (200, body)
                result = self.run_probe("--json")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)["code"], "invalid_response")


if __name__ == "__main__":
    unittest.main()
