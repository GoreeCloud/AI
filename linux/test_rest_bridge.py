"""Synthetic localhost Qt REST security tests: no provider calls or real secrets."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import rest_bridge
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from rest_bridge import SafeRestBridge, checked_route


class TestApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._reply("GET")

    def do_POST(self):
        self._reply("POST")

    def _reply(self, method):
        self.server.calls.append((method, self.path, self.headers.get("Authorization", "")))
        if self.server.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/forbidden-relay")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.server.mode == "invalid":
            data = b'{"private-but-not-returned":'
        elif self.server.mode == "oversized":
            data = b'{"very_long":"' + b"x" * 512 + b'"}'
        else:
            data = json.dumps({"ok": True, "kind": method}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


class QtRestBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QCoreApplication.instance() or QCoreApplication([])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), TestApiHandler)
        cls.server.daemon_threads = True
        cls.server.calls = []
        cls.server.mode = "success"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def setUp(self):
        self.server.mode = "success"
        self.server.calls.clear()
        self.bridge = SafeRestBridge()
        self.results = []
        self.errors = []
        self.bridge.succeeded.connect(lambda rid, json_text: self.results.append((rid, json.loads(json_text))))
        self.bridge.failed.connect(lambda rid, error: self.errors.append((rid, error)))

    def request(self, method="GET", path="/api/v1/documents", body="", token="local-fixture-token",
                endpoint=None):
        self.bridge.start(17, endpoint or self.url, token, method, path, body)

    def drain(self):
        if self.results or self.errors:
            return
        loop = QEventLoop()
        self.bridge.succeeded.connect(lambda *_: loop.quit())
        self.bridge.failed.connect(lambda *_: loop.quit())
        QTimer.singleShot(3000, loop.quit)
        loop.exec()

    def test_read_only_get_returns_structured_object(self):
        self.request()
        self.drain()
        self.assertEqual(self.results, [(17, {"ok": True, "kind": "GET"})])
        self.assertEqual(self.errors, [])
        self.assertEqual(self.server.calls, [
            ("GET", "/api/v1/documents", "Bearer local-fixture-token")
        ])

    def test_synthetic_post_retains_json_contract(self):
        self.request(method="POST", path="/api/v1/agents/plan", body='{"synthetic":"only"}')
        self.drain()
        self.assertEqual(self.results, [(17, {"ok": True, "kind": "POST"})])
        self.assertEqual(self.server.calls[0][1], "/api/v1/agents/plan")

    def test_refuses_external_redirect_without_following_it(self):
        self.server.mode = "redirect"
        self.request()
        self.drain()
        self.assertEqual(self.results, [])
        self.assertEqual(len(self.server.calls), 1)
        self.assertEqual(self.server.calls[0][1], "/api/v1/documents")
        self.assertTrue(self.errors)
        self.assertNotIn("Bearer", str(self.errors))

    def test_rejects_oversized_untrusted_reply(self):
        self.server.mode = "oversized"
        with patch.object(rest_bridge, "_MAX_RESPONSE", 64):
            self.request()
            self.drain()
        self.assertEqual(self.results, [])
        self.assertTrue(self.errors)
        self.assertIn("size limit", str(self.errors))

    def test_invalid_json_produces_generic_error(self):
        self.server.mode = "invalid"
        self.request()
        self.drain()
        self.assertEqual(self.results, [])
        self.assertTrue(self.errors)
        self.assertNotIn("private-but-not-returned", str(self.errors))

    def test_bad_route_and_credentials_deny_before_network(self):
        for path in ("/not-api", "/api/v1/../secrets", "/api/v1/chat?token=secret",
                     "/api/v1//admin", "/api/v1/a%2fb"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                checked_route(path)
        self.request(path="/api/v1/../admin")
        self.assertEqual(self.results, [])
        self.assertTrue(self.errors)
        self.assertFalse(self.server.calls)
        self.errors.clear()
        self.request(token="bad\r\nCredential: injected")
        self.assertTrue(self.errors)
        self.assertFalse(self.server.calls)

    def test_nonloopback_http_denied(self):
        self.request(endpoint="http://example.invalid:80")
        self.assertTrue(self.errors)
        self.assertFalse(self.server.calls)

    def test_qml_does_not_use_redirectable_xmlhttp_requests(self):
        scene = (Path(__file__).resolve().parent / "Main.qml").read_text(encoding="utf-8")
        self.assertNotIn("XMLHttpRequest", scene)
        self.assertIn("restBridge.start", scene)
        self.assertIn("streamBridge.start", scene)
