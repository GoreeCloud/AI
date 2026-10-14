#!/usr/bin/env python3
"""In-memory conversation navigation and explicit answer-regeneration tests."""

from __future__ import annotations

from contextlib import closing
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import ChatMessage, ChatResult, ChatStreamEvent, LocalModelError
from test_local_chat_session import FakeRuntime, FakeOllama
from test_local_model_streaming import frame, ndjson


ROOT = Path(__file__).resolve().parents[1]


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")
        for prompt in ("first private", "second private", "third private"):
            self.session.reply(prompt)

    def test_rewind_removes_future_context_without_network(self):
        before = len(self.runtime.requests)
        self.assertEqual(self.session.rewind_to(1), 2)
        self.assertEqual(len(self.runtime.requests), before)
        self.session.reply("after rewind")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "first private"),
                          ChatMessage("assistant", "OK"),
                          ChatMessage("user", "after rewind")))

    def test_forget_oldest_removes_past_context_without_network(self):
        before = len(self.runtime.requests)
        self.assertEqual(self.session.forget_oldest(2), 2)
        self.assertEqual(len(self.runtime.requests), before)
        self.session.reply("after forget")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "third private"),
                          ChatMessage("assistant", "OK"),
                          ChatMessage("user", "after forget")))

    def test_invalid_navigation_is_atomic_and_offline(self):
        before = self.session.turns
        requests = len(self.runtime.requests)
        for invalid in (-1, 4, 3.0, True, "1", None):
            for action in (self.session.rewind_to, self.session.forget_oldest):
                with self.subTest(invalid=invalid, action=action.__name__):
                    with self.assertRaises(LocalModelError) as error:
                        action(invalid)
                    self.assertEqual(error.exception.code, "invalid_turn_index")
                    self.assertEqual(self.session.turns, before)
        self.assertEqual(len(self.runtime.requests), requests)

    def test_zero_and_full_count_boundaries(self):
        self.assertEqual(self.session.rewind_to(3), 0)
        self.assertEqual(self.session.forget_oldest(0), 0)
        self.assertEqual(self.session.rewind_to(0), 3)
        self.assertEqual(self.session.turns, ())
        self.assertEqual(self.session.forget_oldest(0), 0)

    def test_compatible_with_system_instruction_and_retention(self):
        self.session.set_system_instruction("Private instruction")
        self.session.reply("one")
        self.session.reply("two")
        self.session.set_turn_limit(1)
        self.assertEqual(self.session.turns[0][0].content, "two")
        self.assertEqual(self.session.rewind_to(0), 1)
        self.assertTrue(self.session.has_system_instruction)
        self.session.reply("three")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("system", "Private instruction"),
                          ChatMessage("user", "three")))


class RegenerationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_requires_completed_retained_turn(self):
        for action in (self.session.regenerate_last,
                       lambda: list(self.session.iter_regenerate_last())):
            with self.assertRaises(LocalModelError) as caught:
                action()
            self.assertEqual(caught.exception.code, "no_turns")
        self.assertFalse(self.runtime.requests)

    def test_nonstream_replaces_answer_without_replaying_previous_reply(self):
        self.session.reply("first")
        self.session.reply("latest private")
        self.runtime.response = "new answer"
        result = self.session.regenerate_last()
        self.assertEqual(result.content, "new answer")
        self.assertEqual(len(self.session.turns), 2)
        self.assertEqual(self.session.turns[-1][1].content, "new answer")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "first"),
                          ChatMessage("assistant", "OK"),
                          ChatMessage("user", "latest private")))
        self.session.reply("followup")
        self.assertEqual(self.runtime.requests[-1][1][-2],
                         ChatMessage("assistant", "new answer"))

    def test_failed_or_invalid_replacement_preserves_existing_turn(self):
        self.session.reply("keep this user")
        snapshot = self.session.turns
        self.runtime.raise_error = True
        with self.assertRaises(LocalModelError):
            self.session.regenerate_last()
        self.runtime.raise_error = False
        self.assertEqual(self.session.turns, snapshot)
        for value in ("", "bad\\x00answer".replace("\\x00", "\x00"),
                      "x" * 17000, "\ud800"):
            with self.subTest(value=repr(value[:8])):
                self.runtime.response = value
                with self.assertRaises(LocalModelError):
                    self.session.regenerate_last()
                self.assertEqual(self.session.turns, snapshot)
        self.assertTrue(self.session.last_reply_retained)

    def test_stream_replaces_only_after_done(self):
        self.session.reply("first")
        self.runtime.stream_events = [
            ChatStreamEvent("ollama", "tiny:1", "local", "new ", False),
            ChatStreamEvent("ollama", "tiny:1", "local", "answer", False),
            ChatStreamEvent("ollama", "tiny:1", "local", "", True),
        ]
        events = list(self.session.iter_regenerate_last())
        self.assertEqual([event.done for event in events], [False, False, True])
        self.assertEqual(self.session.turns[0][1].content, "new answer")
        self.assertEqual(self.runtime.requests[-1][1],
                         (ChatMessage("user", "first"),))
        self.assertTrue(self.runtime.stream_closed)

    def test_stream_cancel_and_incomplete_do_not_replace_old_answer(self):
        self.session.reply("stay private")
        old = self.session.turns
        iterator = self.session.iter_regenerate_last()
        self.assertEqual(next(iterator).delta, "OK")
        self.assertEqual(self.session.turns, old)
        iterator.close()
        self.assertTrue(self.runtime.stream_closed)
        self.assertEqual(self.session.turns, old)
        self.runtime.stream_events = [
            ChatStreamEvent("ollama", "tiny:1", "local", "partial", False)
        ]
        with self.assertRaises(LocalModelError):
            list(self.session.iter_regenerate_last())
        self.assertEqual(self.session.turns, old)

    def test_stream_empty_or_oversized_answer_does_not_discard_old(self):
        self.session.reply("private")
        old = self.session.turns
        for value in ("", "x" * 17000):
            self.runtime.stream_events = [
                ChatStreamEvent("ollama", "tiny:1", "local", value, False),
                ChatStreamEvent("ollama", "tiny:1", "local", "", True),
            ]
            with self.subTest(len=len(value)):
                with self.assertRaises(LocalModelError):
                    list(self.session.iter_regenerate_last())
                self.assertEqual(self.session.turns, old)

    def test_retention_cap_remains_active_during_regeneration(self):
        self.session.reply("first")
        self.session.reply("latest")
        self.session.set_turn_limit(1)
        self.runtime.response = "replacement"
        self.session.regenerate_last()
        self.assertEqual(len(self.session.turns), 1)
        self.assertEqual(self.session.turns[0][1].content, "replacement")
        self.session.set_turn_limit(0)
        with self.assertRaises(LocalModelError):
            self.session.regenerate_last()


class CliFeatureTests(unittest.TestCase):
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

    def run_repl(self, commands: str):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint",
             f"http://127.0.0.1:{self.server.server_port}",
             "repl", "--model", "tiny:1"],
            input=commands, text=True, capture_output=True, timeout=10,
        )

    def test_console_navigation_and_regeneration(self):
        p = self.run_repl("first\\nsecond\\nthird\\n/rewind 2\\n/again\\n/forget 1\\nnext\\n/exit\\n".replace("\\n", "\n"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(len(self.server.requests), 5)
        self.assertEqual([m["content"] for m in self.server.requests[3]["messages"]],
                         ["first", "answer", "second"])
        self.assertEqual([m["content"] for m in self.server.requests[-1]["messages"]],
                         ["second", "answer", "next"])
        self.assertIn("Discarded 1 completed turn", p.stdout)
        self.assertNotIn("Unknown command", p.stdout)

    def test_invalid_console_navigation_and_missing_retry_never_call_model(self):
        p = self.run_repl("/again\\n/rewind 99\\n/forget -1\\n/rewind 1junk\\n/exit\\n".replace("\\n", "\n"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.server.requests, [])
        self.assertIn("no_turns", p.stderr)
        self.assertIn("invalid_turn_index", p.stderr)
        self.assertIn("history unchanged", p.stdout)


if __name__ == "__main__":
    unittest.main()
