#!/usr/bin/env python3
"""In-process ephemeral one-time chat privacy and CLI contract tests."""

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
from reference.local_model_gateway import ChatMessage, ChatStreamEvent, LocalModelError
from test_local_chat_session import FakeRuntime, FakeOllama
from test_local_model_streaming import ndjson, frame

ROOT = Path(__file__).resolve().parents[1]


class OneTimeSessionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")
        self.session.reply("retained secret")
        self.before = self.session.turns

    def test_nonstream_omits_history_and_keeps_state_unchanged(self):
        result = self.session.reply_once("independent question")
        self.assertEqual(result.content, "OK")
        self.assertEqual(self.session.turns, self.before)
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "independent question"),))
        self.session.reply("continuation")
        self.assertEqual(self.runtime.requests[-1][1][0].content, "retained secret")
        self.assertNotIn(ChatMessage("user", "independent question"),
                         self.runtime.requests[-1][1])

    def test_stream_omits_history_and_keeps_state_unchanged(self):
        received = list(self.session.iter_reply_once("one time streamed"))
        self.assertEqual([event.done for event in received], [False, True])
        self.assertEqual(self.session.turns, self.before)
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "one time streamed"),))
        self.assertTrue(self.runtime.stream_closed)

    def test_system_instruction_is_only_preserved_context(self):
        self.session.set_system_instruction("Temporary system instruction")
        self.session.reply("stored question")
        old = self.session.turns
        self.session.reply_once("isolated ask")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("system", "Temporary system instruction"),
                          ChatMessage("user", "isolated ask")))
        self.assertEqual(self.session.turns, old)

    def test_failure_and_invalid_input_never_modify_history(self):
        for prompt in ("", "  ", "\x00", "\ud800", "x" * 17000):
            with self.subTest(prompt=repr(prompt[:10])):
                with self.assertRaises(LocalModelError):
                    self.session.reply_once(prompt)
                self.assertEqual(self.session.turns, self.before)
        self.runtime.raise_error = True
        with self.assertRaises(LocalModelError):
            self.session.reply_once("failed")
        with self.assertRaises(LocalModelError):
            list(self.session.iter_reply_once("failed stream"))
        self.assertEqual(self.session.turns, self.before)

    def test_cancel_or_incomplete_stream_never_retains(self):
        iterator = self.session.iter_reply_once("cancel me")
        self.assertEqual(next(iterator).delta, "OK")
        iterator.close()
        self.assertEqual(self.session.turns, self.before)
        self.runtime.stream_events = [
            ChatStreamEvent("ollama", "tiny:1", "local", "partial", False)
        ]
        with self.assertRaises(LocalModelError):
            list(self.session.iter_reply_once("truncate"))
        self.assertEqual(self.session.turns, self.before)

    def test_stateless_retention_and_original_history_independent(self):
        self.session.set_turn_limit(0)
        self.session.reply_once("ephemeral question")
        self.assertEqual(self.session.turns, ())
        self.assertEqual(self.session.turn_limit, 0)


class OneTimeCliTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, ndjson(frame("done"), frame(done=True)), {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_repl(self, commands, *, nonstream=False):
        if nonstream:
            self.server.reply = (200, json.dumps({
                "done": True, "message": {"role": "assistant", "content": "done"}
            }).encode(), {})
        return subprocess.run([
            sys.executable, str(ROOT / "scripts/ai_local.py"),
            "--endpoint", f"http://127.0.0.1:{self.server.server_port}",
            "repl", "--model", "tiny:1", *(["--no-stream"] if nonstream else [])
        ], input=commands, capture_output=True, text=True, timeout=10)

    def test_cli_once_is_not_in_followup_history_both_modes(self):
        for nonstream in (False, True):
            with self.subTest(nonstream=nonstream):
                self.server.received.clear()
                self.server.requests.clear()
                p = self.run_repl("remember me\n/once private one-off\nfollowup\n/exit\n",
                                  nonstream=nonstream)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual([len(q["messages"]) for q in self.server.requests],
                                 [1, 1, 3])
                self.assertEqual(self.server.requests[1]["messages"],
                                 [{"role": "user", "content": "private one-off"}])
                self.assertNotIn("private one-off",
                                 str(self.server.requests[-1]["messages"]))
                self.assertIn("not added to conversation memory", p.stdout)

    def test_cli_missing_once_text_never_calls_runtime(self):
        p = self.run_repl("/once\n/once   \n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(self.server.requests)
        self.assertIn("Use /once TEXT", p.stdout)

    def test_help_discloses_one_time_mode(self):
        p = self.run_repl("/help\n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("/once TEXT", p.stdout)


if __name__ == "__main__":
    unittest.main()
