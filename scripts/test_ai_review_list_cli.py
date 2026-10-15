"""Local HTTP CLI regression for optional bounded list arguments."""
import json
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from test_ai_review_local import ReviewCliTests, ROOT, SCRIPT


class ReviewListCliTests(unittest.TestCase):
    def test_optional_list_can_be_present_or_absent(self):
        fixture = ReviewCliTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        answers = [
            {"count": 2, "tags": ["urgent", "client"]},
            {"count": 2},
        ]
        received = []

        class FakeOllama(BaseHTTPRequestHandler):
            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                received.append(json.loads(raw))
                data = answers.pop(0)
                proposal = json.dumps({
                    "schema": "goreecloud.ai.action-proposal.v1",
                    "service": "sample", "operation": "items.read",
                    "resource": "list:sample", "arguments": data,
                })
                body = json.dumps({
                    "model": "demo:latest", "done": True,
                    "message": {"role": "assistant", "content": proposal},
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = fixture.command(
                f"http://127.0.0.1:{server.server_port}", mode="json")
            command = base + ["--field", "tags:string_list:optional"]
            results = [
                subprocess.run(command, input="List items", text=True,
                               capture_output=True, cwd=ROOT, timeout=12)
                for _ in range(2)
            ]
        finally:
            server.shutdown()
            worker.join(timeout=3)
            server.server_close()
        self.assertEqual([x.returncode for x in results], [0, 0],
                         [x.stderr for x in results])
        first, second = [json.loads(x.stdout) for x in results]
        self.assertEqual(first["arguments"]["tags"], ["urgent", "client"])
        self.assertNotIn("tags", second["arguments"])
        self.assertEqual(first["execution"], "disabled")
        self.assertEqual(len(received), 2)
        self.assertTrue(all("tools" not in body for body in received))


if __name__ == "__main__":
    unittest.main()
