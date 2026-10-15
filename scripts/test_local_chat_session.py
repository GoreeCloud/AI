#!/usr/bin/env python3
"""In-memory local chat sessions: deterministic security, transcript and CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import (
    ChatMessage, ChatResult, ChatStreamEvent, LocalModelError,
    MAX_MESSAGES, MAX_REQUEST_BYTES,
)
from test_local_model_gateway import FakeOllama
from test_local_model_streaming import frame, ndjson

ROOT = Path(__file__).resolve().parents[1]


class FakeRuntime:
    def __init__(self, *, response="OK"):
        self.requests = []
        self.response = response
        self.raise_error = False
        self.stream_events = None
        self.stream_closed = False

    def chat(self, model, messages):
        self.requests.append(("chat", tuple(messages)))
        if self.raise_error:
            raise LocalModelError("runtime_unavailable", "Local runtime unavailable.")
        return ChatResult("ollama", model, "local", self.response)

    def iter_chat(self, model, messages):
        self.requests.append(("stream", tuple(messages)))
        try:
            if self.raise_error:
                raise LocalModelError("runtime_unavailable", "Local runtime unavailable.")
            if self.stream_events is not None:
                for event in self.stream_events:
                    yield event
            else:
                yield ChatStreamEvent("ollama", model, "local", self.response, False)
                yield ChatStreamEvent("ollama", model, "local", "", True)
        finally:
            self.stream_closed = True


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_multiple_turns_are_in_context(self):
        self.session.reply("first")
        self.session.reply("second")
        self.assertEqual(self.runtime.requests[0][1], (ChatMessage("user", "first"),))
        self.assertEqual(self.runtime.requests[1][1], (
            ChatMessage("user", "first"), ChatMessage("assistant", "OK"),
            ChatMessage("user", "second"),
        ))
        self.assertEqual(len(self.session.turns), 2)

    def test_turns_are_immutable_snapshots(self):
        self.session.reply("first")
        snapshot = self.session.turns
        self.session.reset()
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(self.session.turns, ())

    def test_reset_does_not_include_prior_prompts(self):
        self.session.reply("private original")
        self.session.reset()
        self.session.reply("second")
        self.assertEqual(self.runtime.requests[-1][1], (ChatMessage("user", "second"),))

    def test_history_eviction_always_retains_complete_pairs(self):
        for i in range(20):
            self.session.reply(f"question {i}")
        messages = self.runtime.requests[-1][1]
        self.assertLessEqual(len(messages), MAX_MESSAGES)
        self.assertEqual(messages[-1], ChatMessage("user", "question 19"))
        self.assertEqual(messages[0].role, "user")
        self.assertEqual([m.role for m in messages], ["user", "assistant"] * ((len(messages)-1)//2) + ["user"])
        self.assertNotIn(ChatMessage("user", "question 0"), messages)

    def test_request_byte_budget_evicts_old_pairs(self):
        large = "x" * 10000
        self.runtime.response = "a" * 10000
        for i in range(7):
            self.session.reply(f"{i}:{large}")
        messages = self.runtime.requests[-1][1]
        self.assertLess(len(messages), MAX_MESSAGES)
        self.assertEqual(messages[-1].content, f"6:{large}")
        self.assertNotIn(ChatMessage("user", f"0:{large}"), messages)
        request_bytes = len(json.dumps({
            "model": "tiny:1",
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        self.assertLessEqual(request_bytes, MAX_REQUEST_BYTES)

    def test_runtime_failure_preserves_old_history(self):
        self.session.reply("first")
        before = self.session.turns
        self.runtime.raise_error = True
        with self.assertRaises(LocalModelError):
            self.session.reply("do not save")
        self.assertEqual(self.session.turns, before)

    def test_invalid_input_never_reaches_provider(self):
        for prompt in ("", "   ", "\0", "x" * 17000, "\ud800"):
            with self.subTest(repr=repr(prompt)):
                with self.assertRaises(LocalModelError):
                    self.session.reply(prompt)
        self.assertFalse(self.runtime.requests)

    def test_large_and_empty_reply_preserve_completed_history(self):
        self.session.reply("one")
        for response in ("A" * 17000, "", "NUL\0in answer"):
            with self.subTest(response_length=len(response)):
                before = self.session.turns
                self.runtime.response = response
                self.session.reply("second")
                self.assertFalse(self.session.last_reply_retained)
                self.assertEqual(self.session.turns, before)
                self.runtime.response = "OK"
                self.session.reply("again")
                self.assertEqual(self.runtime.requests[-1][1][-1], ChatMessage("user", "again"))
                self.assertNotIn(ChatMessage("user", "second"), self.runtime.requests[-1][1])
        self.assertTrue(self.session.last_reply_retained)

    def test_empty_stream_preserves_previous_completed_turn(self):
        self.session.reply("previous")
        snapshot = self.session.turns
        self.runtime.stream_events = [ChatStreamEvent("ollama", "tiny:1", "local", "", True)]
        self.assertTrue(list(self.session.iter_reply("new"))[-1].done)
        self.assertEqual(self.session.turns, snapshot)
        self.assertFalse(self.session.last_reply_retained)

    def test_invalid_response_identity_does_not_modify_history(self):
        class BadRuntime(FakeRuntime):
            def chat(self, model, messages):
                return ChatResult("external", model, "remote", "bad")
        s = LocalChatSession(BadRuntime(), "tiny:1")
        with self.assertRaises(LocalModelError) as got:
            s.reply("hi")
        self.assertEqual(got.exception.code, "invalid_response")
        self.assertEqual(s.turns, ())

    def test_stream_commits_only_after_explicit_done(self):
        self.session.reply("previous")
        events = list(self.session.iter_reply("new"))
        self.assertEqual([e.done for e in events], [False, True])
        self.assertEqual(len(self.session.turns), 2)
        self.assertEqual(self.runtime.requests[-1][1][-1], ChatMessage("user", "new"))
        self.assertTrue(self.runtime.stream_closed)

    def test_incomplete_stream_keeps_history_unchanged(self):
        self.session.reply("previous")
        before = self.session.turns
        self.runtime.stream_events = [ChatStreamEvent("ollama", "tiny:1", "local", "partial", False)]
        with self.assertRaises(LocalModelError) as got:
            list(self.session.iter_reply("unfinished"))
        self.assertEqual(got.exception.code, "incomplete_stream")
        self.assertEqual(self.session.turns, before)

    def test_closing_partial_iterator_prevents_history_commit(self):
        self.session.reply("old")
        iterator = self.session.iter_reply("new")
        self.assertEqual(next(iterator).delta, "OK")
        self.assertFalse(self.runtime.stream_closed)
        iterator.close()
        self.assertTrue(self.runtime.stream_closed)
        self.assertEqual(len(self.session.turns), 1)

    def test_stream_bad_identity_and_done_delta_fail_closed(self):
        for events in (
            [ChatStreamEvent("remote", "tiny:1", "remote", "x", False)],
            [ChatStreamEvent("ollama", "other", "local", "", True)],
            [ChatStreamEvent("ollama", "tiny:1", "local", "payload", True)],
        ):
            with self.subTest(events=events):
                self.runtime.stream_events = events
                with self.assertRaises(LocalModelError):
                    list(self.session.iter_reply("bad"))
                self.assertEqual(self.session.turns, ())

    def test_stream_failure_rolls_back_and_closes(self):
        self.runtime.raise_error = True
        with self.assertRaises(LocalModelError):
            list(self.session.iter_reply("new"))
        self.assertEqual(self.session.turns, ())
        self.assertTrue(self.runtime.stream_closed)

    def test_oversized_stream_reply_preserves_prior_context(self):
        self.session.reply("previous")
        before = self.session.turns
        self.runtime.response = "x" * 17000
        events = list(self.session.iter_reply("large"))
        self.assertTrue(events[-1].done)
        self.assertFalse(self.session.last_reply_retained)
        self.assertEqual(self.session.turns, before)
        self.runtime.response = "OK"
        self.session.reply("next")
        self.assertNotIn(ChatMessage("user", "large"), self.runtime.requests[-1][1])

    def test_invalid_unicode_stream_is_rejected(self):
        self.runtime.stream_events = [
            ChatStreamEvent("ollama", "tiny:1", "local", "\ud800", False),
            ChatStreamEvent("ollama", "tiny:1", "local", "", True),
        ]
        with self.assertRaises(LocalModelError) as got:
            list(self.session.iter_reply("test"))
        self.assertEqual(got.exception.code, "invalid_response")
        self.assertEqual(self.session.turns, ())


class CliSessionTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, ndjson(frame("answer"), frame(done=True)), {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_repl(self, input_text, *, nonstream=False, preserve_reply=False):
        if nonstream and not preserve_reply:
            self.server.reply = (200, json.dumps({
                "done": True, "message": {"role": "assistant", "content": "answer"},
            }).encode(), {})
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint", self.endpoint,
             "repl", "--model", "tiny:1"] + (["--no-stream"] if nonstream else []),
            input=input_text, text=True, capture_output=True, timeout=9,
        )

    def test_cli_stream_multi_turn_reset_status(self):
        proc = self.run_repl("hello\n/status\nnext\n/reset\n/status\nfinal\n/exit\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([len(p["messages"]) for p in self.server.requests], [1, 3, 1])
        self.assertIn("Retained conversation turns: 1", proc.stdout)
        self.assertIn("Retained conversation turns: 0", proc.stdout)
        self.assertIn("Conversation cleared", proc.stdout)

    def test_cli_nonstream_multi_turn(self):
        proc = self.run_repl("hello\nnext\n/exit\n", nonstream=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([len(p["messages"]) for p in self.server.requests], [1, 3])
        self.assertEqual(proc.stdout.count("AI> answer"), 2)

    def test_cli_unknown_command_never_sent_to_model(self):
        proc = self.run_repl("/fake\n//slash\n/exit\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0]["messages"][0]["content"], "/slash")
        self.assertIn("Unknown command", proc.stdout)

    def test_cli_failed_partial_stream_does_not_enter_history(self):
        self.server.reply = (200, ndjson(frame("partial")), {})
        proc = self.run_repl("first\nsecond\n/exit\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual([len(p["messages"]) for p in self.server.requests], [1, 1])
        self.assertIn("Partial response discarded", proc.stderr)
        self.assertIn("incomplete_stream", proc.stderr)

    def test_invalid_surrogate_from_service_is_sanitized_failure(self):
        # JSON escapes the lone surrogate; decoded assistant text must be rejected.
        self.server.reply = (200, b"".join(
            json.dumps(item, ensure_ascii=True).encode("utf-8") + b"\n"
            for item in (frame("\ud800"), frame(done=True))
        ), {})
        proc = self.run_repl("first\n/exit\n")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("invalid_response", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_invalid_nonstream_unicode_from_service_is_sanitized_failure(self):
        self.server.reply = (200, json.dumps({
            "done": True, "message": {"role": "assistant", "content": "\ud800"},
        }, ensure_ascii=True).encode("utf-8"), {})
        proc = self.run_repl("first\n/exit\n", nonstream=True, preserve_reply=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("invalid_response", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_exit_does_not_send_request(self):
        proc = self.run_repl("/exit\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.server.requests, [])


if __name__ == "__main__":
    unittest.main()
