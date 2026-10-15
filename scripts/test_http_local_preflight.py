"""Localhost HTTP integration coverage for the full non-executing preflight."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from reference.local_model_gateway import LocalOllamaGateway
from test_complete_local_preflight import CompletePreflightTests


class HttpPreflightTests(CompletePreflightTests):
    def test_loopback_ollama_protocol_to_sqlite_reservation(self):
        response = json.dumps(self.response)
        requests = []

        class OllamaStub(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                requests.append((self.path, payload))
                body = json.dumps({
                    "model": "sample:latest",
                    "done": True,
                    "message": {"role": "assistant", "content": response},
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), OllamaStub)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            self.runtime = LocalOllamaGateway(
                f"http://127.0.0.1:{server.server_port}")
            preview = self.run_flow().redacted()
        finally:
            server.shutdown()
            worker.join(timeout=3)
            server.server_close()

        self.assertEqual(preview["execution"], "disabled")
        self.assertEqual(preview["status"], "reserved_no_execution")
        self.assertEqual(self.count_reservations(), 1)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0][0], "/api/chat")
        self.assertEqual(requests[0][1]["stream"], False)
        self.assertNotIn("tools", requests[0][1])


if __name__ == "__main__":
    unittest.main()
