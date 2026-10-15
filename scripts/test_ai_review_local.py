"""End-to-end local proposal review CLI tests with a synthetic Ollama server."""
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
SCRIPT = ROOT / "scripts" / "ai_review_local.py"


class ReviewCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        folder = Path(self.directory.name)
        self.manifest = folder / "manifest.json"
        self.target = folder / "target.txt"
        self.target.write_text("list:sample", encoding="utf-8")
        self.manifest.write_text(json.dumps({
            "schema": "goreecloud.ai.capability-manifest.v1",
            "service": "sample", "title": "Sample", "revision": "v1",
            "transports": ["mcp"],
            "operations": [{"id": "items.read", "minimum_risk": "read",
                            "transports": ["mcp"]}],
        }), encoding="utf-8")
        self.pin = hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def command(self, endpoint, *, mode="html", pin=None, field="count:integer"):
        return [
            sys.executable, str(SCRIPT),
            "--manifest", str(self.manifest),
            "--sha256", self.pin if pin is None else pin,
            "--target-file", str(self.target),
            "--model", "demo:latest", "--operation", "items.read",
            "--transport", "mcp", "--field", field,
            "--endpoint", endpoint, "--format", mode,
        ]

    def execute(self, endpoint, **options):
        return subprocess.run(
            self.command(endpoint, **options), input="List two items",
            capture_output=True, text=True, cwd=ROOT, timeout=12)

    def test_bad_pin_rejected_without_model_request(self):
        result = self.execute("http://127.0.0.1:11434", pin="0" * 64)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("manifest_rejected", result.stderr)

    def test_bad_contract_rejected_without_model_request(self):
        result = self.execute("http://127.0.0.1:11434", field="count:unsafe")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_loopback_response_generates_review_without_approval(self):
        payloads = []
        content = json.dumps({
            "schema": "goreecloud.ai.action-proposal.v1",
            "service": "sample", "operation": "items.read",
            "resource": "list:sample", "arguments": {"count": 2},
        })

        class FakeOllama(BaseHTTPRequestHandler):
            def do_POST(self):
                size = int(self.headers.get("Content-Length", "0"))
                payloads.append((self.path, json.loads(self.rfile.read(size))))
                response = json.dumps({
                    "model": "demo:latest", "done": True,
                    "message": {"role": "assistant", "content": content},
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}"
            page = self.execute(endpoint)
            data = self.execute(endpoint, mode="json")
            self.target.write_text("list:other", encoding="utf-8")
            rejected = self.execute(endpoint)
        finally:
            server.shutdown()
            worker.join(timeout=3)
            server.server_close()

        self.assertEqual(page.returncode, 0, page.stderr)
        self.assertIn("Review proposed action", page.stdout)
        self.assertIn("list:sample", page.stdout)
        self.assertIn("count", page.stdout)
        self.assertIn("Content-Security-Policy", page.stdout)
        self.assertIn("color-scheme:light dark", page.stdout)
        self.assertNotIn("<form", page.stdout)
        self.assertNotIn("<script", page.stdout)
        self.assertEqual(data.returncode, 0, data.stderr)
        self.assertEqual(json.loads(data.stdout)["status"], "awaiting_user_review")
        self.assertEqual(json.loads(data.stdout)["execution"], "disabled")
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual(rejected.stdout, "")
        self.assertIn("target_denied", rejected.stderr)
        self.assertEqual(len(payloads), 3)
        self.assertTrue(all(path == "/api/chat" for path, _ in payloads))
        self.assertTrue(all("tools" not in body for _, body in payloads))


if __name__ == "__main__":
    unittest.main()
