#!/usr/bin/env python3
"""Atomic latest-question editing: synthetic local-only session and console tests."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import ChatMessage, LocalModelError, ChatStreamEvent
from test_local_chat_session import FakeRuntime, FakeOllama
from test_local_model_streaming import frame, ndjson

ROOT = Path(__file__).resolve().parents[1]


class EditSessionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")
        self.session.reply("first")
        self.session.reply("superseded secret")
        self.before = self.session.turns

    def test_edit_replaces_only_last_completed_pair(self):
        self.runtime.response = "new answer"
        result = self.session.edit_last("revised question")
        self.assertEqual(result.content, "new answer")
        self.assertEqual(self.session.turns[0], self.before[0])
        self.assertEqual(self.session.turns[-1][0].content, "revised question")
        self.assertEqual(self.session.turns[-1][1].content, "new answer")
        self.assertEqual(self.runtime.requests[-1][1], (
            ChatMessage("user", "first"), ChatMessage("assistant", "OK"),
            ChatMessage("user", "revised question")
        ))

    def test_rejected_or_failed_edit_preserves_private_turn(self):
        for value in ("", " ", "bad\x00prompt", "\ud800", "x" * 17000):
            with self.subTest(prompt=repr(value[:10])):
                with self.assertRaises(LocalModelError):
                    self.session.edit_last(value)
                self.assertEqual(self.session.turns, self.before)
        self.runtime.raise_error = True
        with self.assertRaises(LocalModelError):
            self.session.edit_last("replacement")
        self.assertEqual(self.session.turns, self.before)

    def test_invalid_replacement_preserves_last_turn(self):
        for reply in ("", "x" * 17000, "\ud800"):
            with self.subTest(reply=repr(reply[:10])):
                self.runtime.response = reply
                with self.assertRaises(LocalModelError):
                    self.session.edit_last("new prompt")
                self.assertEqual(self.session.turns, self.before)

    def test_stream_edit_commits_only_on_done(self):
        self.runtime.stream_events = [
            ChatStreamEvent("ollama", "tiny:1", "local", "new", False),
            ChatStreamEvent("ollama", "tiny:1", "local", "", True),
        ]
        result = list(self.session.iter_edit_last("streamed edit"))
        self.assertEqual([e.done for e in result], [False, True])
        self.assertEqual(self.session.turns[-1][0].content, "streamed edit")
        self.assertEqual(self.runtime.requests[-1][1][-1],
                         ChatMessage("user", "streamed edit"))
        self.assertTrue(self.runtime.stream_closed)

    def test_stream_cancel_and_incomplete_edit_keep_original(self):
        iterator = self.session.iter_edit_last("cancel")
        self.assertEqual(next(iterator).delta, "OK")
        iterator.close()
        self.assertEqual(self.session.turns, self.before)
        self.runtime.stream_events = [ChatStreamEvent("ollama", "tiny:1", "local", "partial", False)]
        with self.assertRaises(LocalModelError):
            list(self.session.iter_edit_last("incomplete"))
        self.assertEqual(self.session.turns, self.before)

    def test_no_retained_turn_cannot_be_edited(self):
        self.session.clear_turns()
        with self.assertRaises(LocalModelError) as e:
            self.session.edit_last("x")
        self.assertEqual(e.exception.code, "no_turns")
        with self.assertRaises(LocalModelError):
            list(self.session.iter_edit_last("x"))
        self.assertEqual(self.session.turns, ())


class EditConsoleTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, ndjson(frame("answer"), frame(done=True)), {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_cli(self, commands, nonstream=False):
        if nonstream:
            self.server.reply = (200, json.dumps({
                "done": True, "message": {"role": "assistant", "content": "answer"}
            }).encode(), {})
        return subprocess.run([
            sys.executable, str(ROOT / "scripts/ai_local.py"),
            "--endpoint", f"http://127.0.0.1:{self.server.server_port}",
            "repl", "--model", "tiny:1", *(["--no-stream"] if nonstream else []),
        ], input=commands, text=True, capture_output=True, timeout=10)

    def test_console_edits_latest_and_excludes_old_question(self):
        for nonstream in (False, True):
            with self.subTest(nonstream=nonstream):
                self.server.requests.clear()
                p = self.run_cli("first\nprivate old question\n/edit corrected\nnext\n/exit\n", nonstream)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(len(self.server.requests), 4)
                self.assertEqual([m["content"] for m in self.server.requests[2]["messages"]],
                                 ["first", "answer", "corrected"])
                self.assertEqual([m["content"] for m in self.server.requests[3]["messages"]],
                                 ["first", "answer", "corrected", "answer", "next"])

    def test_edit_without_retained_turn_is_not_sent(self):
        p = self.run_cli("/edit something\n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("no_turns", p.stderr)
        self.assertFalse(self.server.requests)


if __name__ == "__main__":
    unittest.main()
