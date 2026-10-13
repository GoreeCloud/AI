#!/usr/bin/env python3
"""Local-only deterministic streaming inference tests using synthetic HTTP responses."""

from __future__ import annotations

from contextlib import closing
import json
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import ChatMessage, LocalModelError, LocalOllamaGateway
from test_local_model_gateway import FakeOllama

ROOT = Path(__file__).resolve().parents[1]


def ndjson(*frames: dict) -> bytes:
    return b"".join(json.dumps(frame, ensure_ascii=False).encode("utf-8") + b"\n" for frame in frames)


def frame(content: str = "", *, done: bool = False, model: str = "tiny:1") -> dict:
    return {"model": model, "message": {"role": "assistant", "content": content}, "done": done}


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, ndjson(frame("Hello "), frame("world!"), frame(done=True)), {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"
        self.gateway = LocalOllamaGateway(self.endpoint, 2)
        self.messages = [ChatMessage("user", "Greetings")]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def set_stream(self, data: bytes, *, status: int = 200, headers=None):
        self.server.reply = (status, data, headers or {})

    def assert_stream_error(self, code: str):
        with self.assertRaises(LocalModelError) as caught:
            with closing(self.gateway.iter_chat("tiny:1", self.messages)) as events:
                list(events)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("Greetings", str(caught.exception))

    def test_stream_yields_ordered_deltas_and_done(self):
        with closing(self.gateway.iter_chat("tiny:1", self.messages)) as events:
            received = list(events)
        self.assertEqual([e.delta for e in received], ["Hello ", "world!", ""])
        self.assertEqual([e.done for e in received], [False, False, True])
        self.assertEqual(
            [(e.provider, e.model, e.processing) for e in received],
            [("ollama", "tiny:1", "local")] * 3,
        )
        self.assertEqual(self.server.requests, [{
            "model": "tiny:1", "messages": [{"role": "user", "content": "Greetings"}], "stream": True
        }])
        self.assertEqual(self.server.received, [("POST", "/api/chat")])

    def test_stream_cli_flushes_complete_answer(self):
        command = [
            sys.executable, str(ROOT / "scripts/ai_local.py"),
            "--endpoint", self.endpoint, "chat", "--model", "tiny:1", "--stream",
        ]
        proc = subprocess.run(command, input="Greetings", text=True, capture_output=True, timeout=8)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "Hello world!\n")
        self.assertFalse(proc.stderr)

    def test_truncated_stream_never_claims_completion(self):
        self.set_stream(ndjson(frame("partial")))
        with closing(self.gateway.iter_chat("tiny:1", self.messages)) as events:
            first = next(events)
            self.assertEqual(first.delta, "partial")
            with self.assertRaises(LocalModelError) as caught:
                list(events)
        self.assertEqual(caught.exception.code, "incomplete_stream")

    def test_cli_partial_failure_is_nonzero_and_identified(self):
        self.set_stream(ndjson(frame("partial")))
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/ai_local.py"),
             "--endpoint", self.endpoint, "chat", "--model", "tiny:1", "--stream"],
            input="Greetings", text=True, capture_output=True, timeout=8,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "partial")
        self.assertIn("NOT a completed answer", proc.stderr)
        self.assertIn("incomplete_stream", proc.stderr)

    def test_cli_sanitizes_terminal_control_and_bidi_in_both_modes(self):
        dangerous = "\x1b[31mRED\x1b[0m\u202e"
        expected = r"\x1b[31mRED\x1b[0m\u202e" + "\n"
        for streamed in (True, False):
            with self.subTest(streamed=streamed):
                if streamed:
                    self.set_stream(ndjson(frame(dangerous), frame(done=True)))
                else:
                    self.set_stream(json.dumps({
                        "done": True,
                        "message": {"role": "assistant", "content": dangerous},
                    }).encode("utf-8"))
                args = [
                    sys.executable, str(ROOT / "scripts/ai_local.py"),
                    "--endpoint", self.endpoint, "chat", "--model", "tiny:1",
                ]
                if streamed:
                    args.append("--stream")
                result = subprocess.run(args, input="Greetings", capture_output=True,
                                        text=True, timeout=8)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, expected)
                self.assertFalse(result.stderr)

    def test_stream_wire_bound_is_independent_of_answer_size(self):
        # Enough metadata-only frames to exceed 2 MiB wire cap, below frame-count cap.
        padded = {**frame(), "metadata": "z" * 1000}
        self.set_stream(ndjson(*(padded for _ in range(2200))))
        self.assert_stream_error("response_too_large")

    def test_final_frame_may_contain_last_delta(self):
        self.set_stream(ndjson(frame("A"), frame("B", done=True)))
        with closing(self.gateway.iter_chat("tiny:1", self.messages)) as events:
            received = list(events)
        self.assertEqual([(e.delta, e.done) for e in received],
                         [("A", False), ("B", False), ("", True)])

    def test_final_frame_can_omit_message(self):
        self.set_stream(ndjson(frame("ok"), {"model": "tiny:1", "done": True}))
        with closing(self.gateway.iter_chat("tiny:1", self.messages)) as events:
            received = list(events)
        self.assertEqual([(e.delta, e.done) for e in received], [("ok", False), ("", True)])

    def test_reject_model_swap_and_unsupported_tool_outputs(self):
        for unexpected in (
            frame("intruder", model="other"),
            {"model": "tiny:1", "message": {"role": "tool", "content": "execute"}, "done": True},
            {"model": "tiny:1", "message": {"role": "assistant", "content": "", "tool_calls": []}, "done": True},
            {"model": "tiny:1", "message": {"role": "assistant", "content": "", "images": []}, "done": True},
            {"model": "tiny:1", "message": {"role": "assistant", "content": 17}, "done": True},
            {"model": "tiny:1", "done": False},
            {"model": "tiny:1", "message": {}, "done": True},
            {"model": "tiny:1", "message": {"role": "assistant", "content": "x"}, "done": "yes"},
            {"model": "tiny:1", "error": "sensitive private response", "done": True},
        ):
            with self.subTest(frame=unexpected):
                self.set_stream(ndjson(unexpected))
                self.assert_stream_error("invalid_response")

    def test_malformed_utf8_json_and_long_frame(self):
        for wire in (b"\xff\n", b"not-json\n", b"\n"):
            with self.subTest(wire=wire):
                self.set_stream(wire)
                self.assert_stream_error("invalid_response")
        self.set_stream(b"x" * (64 * 1024 + 1))
        self.assert_stream_error("response_too_large")

    def test_frame_count_and_answer_size_limits(self):
        self.set_stream(ndjson(*(frame() for _ in range(4097))))
        self.assert_stream_error("response_too_large")
        self.set_stream(ndjson(*(frame("a" * 16000) for _ in range(67))))
        self.assert_stream_error("response_too_large")

    def test_prohibited_redirect_not_followed(self):
        self.set_stream(b"", status=302, headers={"Location": "https://example.invalid/collect"})
        self.assert_stream_error("redirect_blocked")
        self.assertEqual(self.server.received, [("POST", "/api/chat")])

    def test_runtime_error_is_sanitized(self):
        self.set_stream(b'{"error":"Greetings and secrets"}', status=500)
        self.assert_stream_error("runtime_error")

    def test_invalid_input_fails_before_network(self):
        cases = [
            ("tiny:1", [ChatMessage("tool", "exec")]),
            ("bad model", self.messages),
            ("tiny:1", [ChatMessage("user", "A" * (16 * 1024 + 1))]),
        ]
        for name, messages in cases:
            with self.subTest(name=name):
                with self.assertRaises(LocalModelError):
                    list(self.gateway.iter_chat(name, messages))
        self.assertEqual(self.server.received, [])

    def test_close_iterator_releases_stream(self):
        class TrackingResponse:
            status = 200
            closed = False

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                self.closed = True

            def readline(self, maximum):
                return ndjson(frame("first"))

        response = TrackingResponse()
        self.gateway._opener = SimpleNamespace(open=lambda *a, **kw: response)
        iterator = self.gateway.iter_chat("tiny:1", self.messages)
        self.assertEqual(next(iterator).delta, "first")
        self.assertFalse(response.closed)
        iterator.close()
        self.assertTrue(response.closed)
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_nonstream_rejects_tool_calls_too(self):
        self.set_stream(json.dumps({
            "done": True, "message": {"role": "assistant", "content": "", "tool_calls": []}
        }).encode("utf-8"))
        with self.assertRaises(LocalModelError) as caught:
            self.gateway.chat("tiny:1", self.messages)
        self.assertEqual(caught.exception.code, "invalid_response")


if __name__ == "__main__":
    unittest.main()
