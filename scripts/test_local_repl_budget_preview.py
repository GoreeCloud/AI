#!/usr/bin/env python3
"""REPL budget and privacy-safe context preview; entirely synthetic."""
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
from reference.local_model_gateway import ChatMessage, ChatResult, ChatStreamEvent, LocalModelError, MAX_REQUEST_BYTES
from test_local_chat_session import FakeRuntime
from test_local_model_gateway import FakeOllama
from test_local_model_streaming import frame, ndjson

ROOT = Path(__file__).resolve().parents[1]


class BudgetRuntime:
    def __init__(self):
        self.calls = []
    def chat(self, model, messages, *, max_tokens=None):
        self.calls.append(("chat", max_tokens, tuple(messages)))
        return ChatResult("ollama", model, "local", "OK")
    def iter_chat(self, model, messages, *, max_tokens=None):
        self.calls.append(("stream", max_tokens, tuple(messages)))
        yield ChatStreamEvent("ollama", model, "local", "OK", False)
        yield ChatStreamEvent("ollama", model, "local", "", True)


class SessionBudgetPreviewTests(unittest.TestCase):
    def setUp(self):
        self.runtime = BudgetRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_generation_limit_validation_and_atomicity(self):
        self.session.set_generation_limit(24)
        for bad in (0, -1, 513, True, False, 1.2, "24", [], {}):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(LocalModelError) as caught:
                    self.session.set_generation_limit(bad)
                self.assertEqual(caught.exception.code, "invalid_generation_limit")
                self.assertEqual(self.session.generation_limit, 24)
        self.session.set_generation_limit(None)
        self.assertIsNone(self.session.generation_limit)

    def test_budget_reaches_all_chat_modes(self):
        self.session.set_generation_limit(32)
        self.session.reply("first")
        self.session.reply_once("ephemeral")
        self.session.regenerate_last()
        self.session.edit_last("corrected")
        self.assertEqual([call[1] for call in self.runtime.calls], [32] * 4)
        self.assertEqual(self.runtime.calls[1][2], (ChatMessage("user", "ephemeral"),))
        self.assertEqual(len(self.session.turns), 1)

    def test_budget_reaches_streaming_modes(self):
        self.session.set_generation_limit(18)
        list(self.session.iter_reply("first"))
        list(self.session.iter_reply_once("ephemeral"))
        list(self.session.iter_regenerate_last())
        list(self.session.iter_edit_last("changed"))
        self.assertEqual([call[1] for call in self.runtime.calls], [18] * 4)
        self.assertEqual(len(self.session.turns), 1)

    def test_unset_budget_preserves_legacy_provider_contract(self):
        legacy = FakeRuntime()
        local = LocalChatSession(legacy, "tiny:1")
        local.reply("first")
        list(local.iter_reply("second"))
        self.assertEqual([call[0] for call in legacy.requests], ["chat", "stream"])
        self.assertIsNone(local.generation_limit)

    def test_preview_is_redacted_and_read_only(self):
        self.session.reply("PRIVATE_COMPLETED_TURN")
        self.session.set_generation_limit(36)
        before = self.session.turns
        n = len(self.runtime.calls)
        preview = self.session.preview_next("PRIVATE_UNSENT_PROMPT", stream=True)
        self.assertEqual(preview["messages"], 3)
        self.assertEqual(preview["turns_sent"], 1)
        self.assertEqual(preview["turns_omitted"], 0)
        self.assertFalse(preview["network_attempted"])
        self.assertFalse(preview["system_instruction"])
        expected = {"model": "tiny:1", "stream": True,
                    "messages": [{"role":"user","content":"PRIVATE_COMPLETED_TURN"},
                                 {"role":"assistant","content":"OK"},
                                 {"role":"user","content":"PRIVATE_UNSENT_PROMPT"}],
                    "options":{"num_predict":36}}
        self.assertEqual(preview["request_bytes"],
                         len(json.dumps(expected, ensure_ascii=False, separators=(",", ":")).encode()))
        self.assertNotIn("PRIVATE", str(preview))
        self.assertEqual(self.session.turns, before)
        self.assertEqual(len(self.runtime.calls), n)

    def test_preview_eviction_is_not_applied_to_history(self):
        for i in range(19):
            self.session.reply(f"private {i}")
        saved = self.session.turns
        n = len(self.runtime.calls)
        preview = self.session.preview_next("next")
        self.assertGreater(preview["turns_omitted"], 0)
        self.assertLessEqual(preview["messages"], 32)
        self.assertLessEqual(preview["request_bytes"], MAX_REQUEST_BYTES)
        self.assertEqual(self.session.turns, saved)
        self.assertEqual(len(self.runtime.calls), n)

    def test_preview_invalid_prompt_rejected_without_mutation(self):
        self.session.reply("first")
        snapshot = self.session.turns
        for bad in ("", "  ", "text\x00private", "x" * 20000, "\ud800"):
            with self.subTest(bad=repr(bad)[:22]):
                with self.assertRaises(LocalModelError):
                    self.session.preview_next(bad)
        self.assertEqual(self.session.turns, snapshot)
        self.assertEqual(len(self.runtime.calls), 1)

    def test_limits_survive_reset_and_clear_without_restoring_history(self):
        self.session.set_generation_limit(22)
        self.session.reply("private")
        self.session.clear_turns()
        self.session.reset()
        self.assertEqual(self.session.turns, ())
        self.assertEqual(self.session.generation_limit, 22)


class ReplCommandTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        self.server.received = []
        self.server.requests = []
        self.server.reply = (200, ndjson(frame("OK"), frame(done=True)), {})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_repl(self, input_text, *, nonstream=False, flags=()):
        if nonstream:
            self.server.reply = (200, b'{"done":true,"model":"tiny:1","message":{"role":"assistant","content":"OK"}}', {})
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint", self.endpoint,
             "repl", "--model", "tiny:1", *flags] + (["--no-stream"] if nonstream else []),
            input=input_text, text=True, capture_output=True, cwd=ROOT, timeout=10,
        )

    def test_repl_budget_roundtrip_and_offline_preview(self):
        out = self.run_repl("/budget 24\n/preview PRIVATE_UNSENT_PROMPT\nfirst\n/budget 32\nnext\n/budget auto\nthird\n/exit\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual([p.get("options") for p in self.server.requests],
                         [{"num_predict":24}, {"num_predict":32}, None])
        self.assertEqual(len(self.server.requests), 3)
        self.assertIn("Preview (no network)", out.stdout)
        self.assertNotIn("PRIVATE_UNSENT_PROMPT", out.stdout + out.stderr)

    def test_repl_nonstream_budget_from_cli_and_rejected_edits(self):
        out = self.run_repl("/budget\n/budget 0\n/budget 513\n/preview PRIVATE_UNSENT_PROMPT\nhello\n/exit\n",
                            nonstream=True, flags=("--max-tokens", "12"))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(len(self.server.requests), 1)
        self.assertEqual(self.server.requests[0]["options"], {"num_predict":12})
        self.assertIn("12", out.stdout)
        self.assertNotIn("PRIVATE_UNSENT_PROMPT", out.stdout + out.stderr)

    def test_preview_with_invalid_input_never_sends(self):
        out = self.run_repl("/preview\n/preview   \n/budget 0\n/exit\n")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(self.server.received)
        self.assertIn("invalid_messages", out.stderr)


if __name__ == "__main__":
    unittest.main()
