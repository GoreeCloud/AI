"""Synthetic local HTTP test for Qt SSE stream, cancellation and redirect denial.

Never connects to a real AI model, paid API or user device.
"""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from chat_stream import ChatStreamBridge
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer
from PySide6.QtNetwork import QNetworkProxy


class LocalSse(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        self.server.request_paths.append(self.path)
        size = int(self.headers.get("Content-Length", "0"))
        self.server.request_bodies.append(self.rfile.read(min(size, 256_001)))
        if self.server.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", "/redirect-target")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        payload = (
            'data: {"type":"delta","content":"Hello "}' + "\n\n"
            + 'data: {"type":"delta","content":"synthetic Qt"}' + "\n\n"
            + 'data: {"type":"done","provider":"ollama","model":"local-stub"}' + "\n\n"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def log_message(self, *_):
        pass


class QtStreamHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt = QCoreApplication.instance() or QCoreApplication([])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalSse)
        cls.server.daemon_threads = True
        cls.server.request_paths = []
        cls.server.request_bodies = []
        cls.server.mode = "success"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.server.mode = "success"
        self.server.request_paths.clear()
        self.server.request_bodies.clear()
        self.bridge = ChatStreamBridge()
        self.deltas = []
        self.completions = []
        self.errors = []
        self.stops = []
        self.bridge.delta.connect(self.deltas.append)
        self.bridge.completed.connect(lambda p, m: self.completions.append((p, m)))
        self.bridge.failed.connect(self.errors.append)
        self.bridge.stopped.connect(lambda: self.stops.append(True))

    def _call(self, address=None):
        payload = json.dumps({
            "messages": [{"role": "user", "content": "synthetic input only"}],
            "provider": "ollama",
            "allow_cloud_processing": False,
        })
        self.bridge.start(address or self.url, "synthetic-owner-token", payload)

    def _drain(self):
        loop = QEventLoop()
        self.bridge.completed.connect(lambda *_: loop.quit())
        self.bridge.failed.connect(lambda *_: loop.quit())
        QTimer.singleShot(3000, loop.quit)
        loop.exec()

    def test_no_implicit_desktop_proxy(self):
        self.assertEqual(self.bridge.manager.proxy().type(),
                         QNetworkProxy.ProxyType.NoProxy)

    def test_live_loopback_sse_delivers_delta_and_done(self):
        self._call()
        self._drain()
        self.assertEqual("".join(self.deltas), "Hello synthetic Qt")
        self.assertEqual(self.completions, [("ollama", "local-stub")])
        self.assertEqual(self.errors, [])
        self.assertEqual(self.server.request_paths, ["/api/v1/chat/stream"])
        self.assertIn(b"synthetic input", self.server.request_bodies[0])

    def test_external_redirect_is_not_followed(self):
        self.server.mode = "redirect"
        self._call()
        self._drain()
        self.assertEqual(self.completions, [])
        self.assertEqual(self.deltas, [])
        self.assertEqual(self.server.request_paths, ["/api/v1/chat/stream"])
        self.assertTrue(self.errors)

    def test_cancel_discards_late_reply(self):
        self._call()
        self.bridge.cancel()
        self.assertEqual(self.stops, [True])
        self.assertFalse(self.completions)
        self.assertFalse(self.deltas)
        self.assertFalse(self.errors)

    def test_invalid_endpoint_fails_before_network(self):
        self._call("http://example.invalid:8080")
        self.assertEqual(self.errors, ["Invalid chat stream configuration or input"])
        self.assertFalse(self.server.request_paths)


if __name__ == "__main__":
    unittest.main()
