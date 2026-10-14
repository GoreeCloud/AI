#!/usr/bin/env python3
"""Deterministic HTTP contract tests; no live model or external network required."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import ChatMessage, LocalModelError, LocalOllamaGateway

ROOT = Path(__file__).resolve().parents[1]


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self):
        self.server.received.append((self.command, self.path))
        if self.command == "POST":
            length = int(self.headers.get("Content-Length", "0"))
            self.server.requests.append(json.loads(self.rfile.read(length)))
        status, body, headers = self.server.reply
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    do_GET = respond
    do_POST = respond


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, b'{"models":[]}', {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"
        self.gateway = LocalOllamaGateway(self.endpoint, 5)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def reply(self, value, status=200, headers=None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value).encode()
        self.server.reply = (status, value, headers or {})

    def assert_error(self, code, func):
        with self.assertRaises(LocalModelError) as caught:
            func()
        self.assertEqual(caught.exception.code, code)

    def test_model_discovery_is_local_sorted_and_normalized(self):
        self.reply({"models": [{"name": "z:latest", "size": 42}, {"name": "a:1"}]})
        models = self.gateway.list_models()
        self.assertEqual([m.name for m in models], ["a:1", "z:latest"])
        self.assertEqual([m.size_bytes for m in models], [None, 42])
        self.assertEqual(self.server.received, [("GET", "/api/tags")])

    def test_chat_normalizes_and_retains_role_order(self):
        self.reply({"done": True, "message": {"role": "assistant", "content": "Hello!"}})
        result = self.gateway.chat("llama3.2:3b", [
            ChatMessage("system", "Be concise."),
            ChatMessage("user", "Hello"),
            ChatMessage("assistant", "Hi"),
            ChatMessage("user", "Again"),
        ])
        self.assertEqual((result.provider, result.model, result.processing, result.content),
                         ("ollama", "llama3.2:3b", "local", "Hello!"))
        self.assertEqual(self.server.received, [("POST", "/api/chat")])
        self.assertEqual(self.server.requests[0]["stream"], False)
        self.assertEqual([m["role"] for m in self.server.requests[0]["messages"]],
                         ["system", "user", "assistant", "user"])
        self.assertEqual(set(self.server.requests[0]), {"model", "messages", "stream"})

    def test_no_external_hosts_credentials_or_paths(self):
        for endpoint in (
            "https://127.0.0.1:11434", "http://example.com:11434",
            "http://localhost:11434", "http://user:pass@127.0.0.1:11434",
            "http://127.0.0.1:11434/api", "http://127.0.0.1:11434?x=1",
            "http://127.0.0.1:11434#fragment", "http://127.0.0.1:0",
            "http://127.0.0.2:11434", "http://127.255.255.255:11434",
            "http://127.0.0.1:99999", "http://127.0.0.1:11434@evil.invalid",
            "http://127.0.0.1:11434\\@evil.invalid",
        ):
            with self.subTest(endpoint=endpoint):
                self.assert_error("invalid_endpoint", lambda: LocalOllamaGateway(endpoint))

    def test_literal_ipv4_and_ipv6_loopback_are_accepted(self):
        self.assertEqual(LocalOllamaGateway("http://127.0.0.1:11434").endpoint,
                         "http://127.0.0.1:11434")
        self.assertEqual(LocalOllamaGateway("http://[::1]:11434").endpoint,
                         "http://[::1]:11434")

    def test_no_redirect_follows_external_destination(self):
        self.reply(b"", 302, {"Location": "https://example.com/collect"})
        self.assert_error("redirect_blocked", self.gateway.list_models)
        self.assertEqual(self.server.received, [("GET", "/api/tags")])

    def test_invalid_models_fail_before_request(self):
        for model in ("", "bad model", "a\nb", "m" * 200):
            with self.subTest(model=model):
                self.assert_error("invalid_model", lambda: self.gateway.chat(model, [ChatMessage("user", "ok")]))
        self.assertEqual(self.server.received, [])

    def test_invalid_message_roles_and_order_fail_before_request(self):
        cases = [
            [], [ChatMessage("tool", "execute")],
            [ChatMessage("assistant", "answer")],
            [ChatMessage("user", "ok"), ChatMessage("system", "override")],
            [ChatMessage("user", "")], [ChatMessage("user", "\x00")],
            [ChatMessage("user", "x" * 16385)],
            [ChatMessage("user", "a")] * 33,
            [{"role": "user", "content": "dict is not approved"}],
        ]
        for messages in cases:
            expected = "request_too_large" if any(
                isinstance(m, ChatMessage) and len(m.content.encode()) > 16384 for m in messages
            ) else "invalid_messages"
            self.assert_error(expected, lambda: self.gateway.chat("model:latest", messages))
        self.assertEqual(self.server.received, [])

    def test_malformed_and_duplicate_catalogs_fail_closed(self):
        for value in (
            [], {}, {"models": "none"}, {"models": [{}]},
            {"models": [{"name": "valid"}, {"name": "valid"}]},
            {"models": [{"name": "x", "size": -1}]},
            {"models": [{"name": "x", "size": True}]},
            {"models": [{"name": "x"}] * 201},
        ):
            self.reply(value)
            self.assert_error("invalid_response", self.gateway.list_models)

    def test_incomplete_or_malformed_assistant_responses_rejected(self):
        for response in (
            {}, {"done": False, "message": {"role": "assistant", "content": "partial"}},
            {"done": True, "message": {"role": "tool", "content": "call"}},
            {"done": True, "message": {"role": "assistant", "content": 1}},
            {"done": "yes", "message": {"role": "assistant", "content": "ok"}},
        ):
            self.reply(response)
            self.assert_error(
                "invalid_response", lambda: self.gateway.chat("m", [ChatMessage("user", "hello")])
            )

    def test_size_bounded_catalog_response(self):
        self.reply(b" " * (1024 * 1024 + 1))
        self.assert_error("response_too_large", self.gateway.list_models)

    def test_nonstream_read_deadline_stops_trickle_without_leaking_private_request(self):
        class DripResponse:
            status = 200
            closed = False

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.closed = True

            def read(self, count):
                return b"{"  # Never finishes JSON; each byte arrives within socket timeout.

        for request in (
            self.gateway.list_models,
            lambda: self.gateway.chat("tiny:1", [ChatMessage("user", "PRIVATE_TEST_PROMPT")]),
        ):
            with self.subTest(request=request):
                response = DripResponse()
                self.gateway._opener = SimpleNamespace(open=lambda *args, **kwargs: response)
                clock = iter((0, 1, 10, 901))
                with patch("reference.local_model_gateway.time.monotonic",
                           side_effect=lambda: next(clock)):
                    with self.assertRaises(LocalModelError) as caught:
                        request()
                self.assertEqual(caught.exception.code, "runtime_timeout")
                self.assertNotIn("PRIVATE_TEST_PROMPT", str(caught.exception))
                self.assertTrue(response.closed)

    def test_nonstream_read_deadline_accepts_completed_bodies(self):
        class CompleteResponse:
            status = 200
            closed = False

            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.closed = True

            def read(self, count):
                result, self.data = self.data[:count], self.data[count:]
                return result

        for body, request, expected in (
            (b'{"models":[]}', self.gateway.list_models, ()),
            (b'{"done":true,"message":{"role":"assistant","content":"ok"}}',
             lambda: self.gateway.chat("tiny:1", [ChatMessage("user", "hello")]), "ok"),
        ):
            with self.subTest(body=body):
                response = CompleteResponse(body)
                self.gateway._opener = SimpleNamespace(open=lambda *args, **kwargs: response)
                with patch("reference.local_model_gateway.time.monotonic", return_value=1):
                    result = request()
                self.assertEqual(result.content if hasattr(result, "content") else result, expected)
                self.assertTrue(response.closed)

    def test_provider_errors_sanitized(self):
        self.reply(b'{"error":"sensitive prompt from backend"}', 500)
        with self.assertRaises(LocalModelError) as caught:
            self.gateway.chat("m", [ChatMessage("user", "private prompt")])
        self.assertEqual(caught.exception.code, "runtime_error")
        self.assertNotIn("private", str(caught.exception))
        self.assertNotIn("sensitive", str(caught.exception))

    def test_unavailable_service_has_actionable_error(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            unused_port = probe.getsockname()[1]
        missing = LocalOllamaGateway(f"http://127.0.0.1:{unused_port}", 1)
        self.assert_error("runtime_unavailable", missing.list_models)

    def test_timeout_bounds(self):
        for timeout in (0, -1, float("inf"), float("nan"), 121, True, "10"):
            self.assert_error("invalid_timeout", lambda: LocalOllamaGateway(self.endpoint, timeout))

    def test_cli_model_listing_and_local_chat_from_stdin(self):
        self.reply({"models": [{"name": "tiny:1"}]})
        args = [sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint", self.endpoint, "models"]
        listing = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(listing.stdout.strip(), "tiny:1")
        self.reply({"done": True, "message": {"role": "assistant", "content": "Local answer"}})
        args[-1:] = ["chat", "--model", "tiny:1"]
        chat = subprocess.run(args, input="Hi there", cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(chat.returncode, 0, chat.stderr)
        self.assertEqual(chat.stdout.strip(), "Local answer")
        self.assertEqual(self.server.requests[-1]["messages"], [{"role": "user", "content": "Hi there"}])

    def test_cli_rejects_oversized_input_without_network(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint", self.endpoint,
             "chat", "--model", "tiny"],
            input="a" * 17000, capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("request_too_large", proc.stderr)
        self.assertFalse(self.server.received)


if __name__ == "__main__":
    unittest.main()
