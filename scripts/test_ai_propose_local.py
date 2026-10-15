"""CLI-to-loopback protocol regression tests with a synthetic Ollama server."""
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ai_propose_local.py"


class PreviewCliTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.manifest = Path(self.folder.name) / "manifest.json"
        self.manifest.write_text(json.dumps({
            "schema": "goreecloud.ai.capability-manifest.v1",
            "service": "sample", "title": "Sample", "revision": "v1",
            "transports": ["mcp"], "operations": [
                {"id": "items.read", "minimum_risk": "read", "transports": ["mcp"]},
                {"id": "items.write", "minimum_risk": "write", "transports": ["mcp"]},
            ],
        }), encoding="utf-8")
        self.pin = hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def run_cli(self, endpoint, pin=None):
        command = [sys.executable, str(SCRIPT),
                   "--manifest", str(self.manifest),
                   "--sha256", self.pin if pin is None else pin,
                   "--transport", "mcp", "--permit", "items.read",
                   "--model", "sample:latest", "--endpoint", endpoint]
        return subprocess.run(command, input="List two items", text=True,
                              capture_output=True, cwd=ROOT, timeout=12)

    def test_bad_manifest_pin_denied_without_model(self):
        result = self.run_cli("http://127.0.0.1:11434", pin="0" * 64)
        self.assertEqual(result.returncode, 2)
        self.assertIn("manifest_rejected", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_preview_over_local_http_is_not_execution(self):
        response = json.dumps({
            "schema": "goreecloud.ai.action-proposal.v1",
            "service": "sample", "operation": "items.read",
            "resource": "list:sample", "arguments": {"count": 2},
        })
        requests = []

        class StubOllama(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length))
                requests.append((self.path, payload))
                output = json.dumps({
                    "model": "sample:latest", "done": True,
                    "message": {"role": "assistant", "content": response},
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(output)))
                self.end_headers()
                self.wfile.write(output)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), StubOllama)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            completed = self.run_cli(f"http://127.0.0.1:{server.server_port}")
        finally:
            server.shutdown()
            worker.join(timeout=3)
            server.server_close()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        shown = json.loads(completed.stdout)
        self.assertEqual(shown["execution"], "disabled")
        self.assertEqual(shown["status"], "proposed_not_authorized")
        self.assertEqual(shown["connection"], "synthetic_preview_only")
        self.assertNotIn("list:sample", completed.stdout)
        self.assertEqual(requests[0][0], "/api/chat")
        self.assertNotIn("tools", requests[0][1])
        self.assertEqual(requests[0][1]["options"]["num_predict"], 512)


if __name__ == "__main__":
    unittest.main()
