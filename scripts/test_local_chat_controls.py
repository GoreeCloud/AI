#!/usr/bin/env python3
"""Synthetic, offline regressions for local chat controls and console commands."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import ChatMessage, LocalModel, LocalModelError
from test_local_chat_session import FakeRuntime

ROOT = Path(__file__).resolve().parents[1]


class CatalogRuntime(FakeRuntime):
    def __init__(self):
        super().__init__()
        self.installed = ("tiny:1", "alt:1")
        self.catalog_error = False

    def list_models(self):
        if self.catalog_error:
            raise LocalModelError("runtime_unavailable", "Local runtime unavailable.")
        return tuple(LocalModel(name, None) for name in self.installed)


class SessionControlTests(unittest.TestCase):
    def setUp(self):
        self.runtime = CatalogRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_undo_removes_only_last_completed_pair(self):
        self.session.reply("first")
        self.session.reply("second")
        requests_before = len(self.runtime.requests)
        self.assertTrue(self.session.undo_last_turn())
        self.assertEqual(len(self.runtime.requests), requests_before)
        self.session.reply("third")
        self.assertEqual(self.runtime.requests[-1][1], (
            ChatMessage("user", "first"), ChatMessage("assistant", "OK"),
            ChatMessage("user", "third"),
        ))
        self.assertFalse(any(message.content == "second" for message in self.runtime.requests[-1][1]))

    def test_empty_undo_is_safe(self):
        self.assertFalse(self.session.undo_last_turn())
        self.assertEqual(self.runtime.requests, [])

    def test_system_instruction_first_for_both_modes(self):
        self.session.set_system_instruction("Be concise.")
        self.assertTrue(self.session.has_system_instruction)
        self.session.reply("Hello")
        self.assertEqual(self.runtime.requests[-1][1], (
            ChatMessage("system", "Be concise."), ChatMessage("user", "Hello"),
        ))
        events = list(self.session.iter_reply("Again"))
        self.assertTrue(events[-1].done)
        self.assertEqual(self.runtime.requests[-1][1][0], ChatMessage("system", "Be concise."))

    def test_replacing_system_instruction_clears_old_turns(self):
        self.session.reply("private old prompt")
        self.session.set_system_instruction("Use bullet points.")
        self.assertEqual(self.session.turns, ())
        self.session.reply("new")
        self.assertEqual(self.runtime.requests[-1][1], (
            ChatMessage("system", "Use bullet points."), ChatMessage("user", "new"),
        ))

    def test_invalid_system_does_not_change_existing_state(self):
        self.session.set_system_instruction("Valid instruction")
        self.session.reply("keep me")
        old = self.session.turns
        for value in ("", "   ", "\0", "\ud800", "x" * 17000):
            with self.subTest(value=repr(value[:10])):
                with self.assertRaises(LocalModelError):
                    self.session.set_system_instruction(value)
                self.assertEqual(self.session.turns, old)
                self.assertTrue(self.session.has_system_instruction)

    def test_system_instruction_counts_against_request_budget(self):
        self.session.set_system_instruction("S" * 15000)
        self.runtime.response = "A" * 10000
        for i in range(6):
            self.session.reply("prompt " + str(i) + " " + "x" * 10000)
        sent = self.runtime.requests[-1][1]
        self.assertEqual(sent[0].role, "system")
        self.assertEqual(sent[-1].content[:8], "prompt 5")
        self.assertNotIn(ChatMessage("user", "prompt 0 " + "x" * 10000), sent)

    def test_clear_resets_system_and_transcript(self):
        self.session.set_system_instruction("Current")
        self.session.reply("Private")
        self.session.reset()
        self.assertFalse(self.session.has_system_instruction)
        self.assertEqual(self.session.turns, ())
        self.session.reply("new")
        self.assertEqual(self.runtime.requests[-1][1], (ChatMessage("user", "new"),))

    def test_model_switch_checks_installed_and_isolates_context(self):
        self.session.set_system_instruction("For old model")
        self.session.reply("Only for tiny")
        self.assertTrue(self.session.switch_model("alt:1"))
        self.assertEqual(self.session.model, "alt:1")
        self.assertEqual(self.session.turns, ())
        self.assertFalse(self.session.has_system_instruction)
        self.session.reply("Only for alt")
        self.assertEqual(self.runtime.requests[-1][1], (ChatMessage("user", "Only for alt"),))

    def test_unchanged_model_does_not_clear_context(self):
        self.session.reply("Preserve")
        self.runtime.catalog_error = True
        self.assertFalse(self.session.switch_model("tiny:1"))
        self.assertEqual(len(self.session.turns), 1)

    def test_bad_or_unavailable_model_does_not_change_context(self):
        self.session.reply("Preserve")
        for invalid in ("missing:1", "other host", "invalid\nname"):
            with self.subTest(model=invalid):
                with self.assertRaises(LocalModelError):
                    self.session.switch_model(invalid)
                self.assertEqual(self.session.model, "tiny:1")
                self.assertEqual(len(self.session.turns), 1)
        self.runtime.catalog_error = True
        with self.assertRaises(LocalModelError) as error:
            self.session.switch_model("alt:1")
        self.assertEqual(error.exception.code, "runtime_unavailable")
        self.assertEqual(len(self.session.turns), 1)


class LocalHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self.server.calls.append(("GET", self.path))
        self.send_json({"models": [{"name": "tiny:1"}, {"name": "alt:1"}]})

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(size))
        self.server.calls.append(("POST", self.path))
        self.server.requests.append(request)
        self.send_json({"done": True, "message": {"role": "assistant", "content": "OK"}})


class ConsoleControlTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
        self.server.calls = []
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def run_console(self, commands):
        return subprocess.run([
            sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint",
            f"http://127.0.0.1:{self.server.server_port}", "repl", "--model", "tiny:1",
            "--no-stream",
        ], input=commands, capture_output=True, text=True, timeout=10)

    def test_model_discovery_switch_and_reset(self):
        p = self.run_console("first\n/models\n/model alt:1\n/status\nsecond\n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Installed local models: alt:1, tiny:1", p.stdout)
        self.assertIn("Local model: alt:1", p.stdout)
        self.assertEqual([r["model"] for r in self.server.requests], ["tiny:1", "alt:1"])
        self.assertEqual([len(r["messages"]) for r in self.server.requests], [1, 1])

    def test_missing_model_does_not_discard_context(self):
        p = self.run_console("first\n/model missing:1\nsecond\n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("model_not_installed", p.stderr)
        self.assertEqual([r["model"] for r in self.server.requests], ["tiny:1", "tiny:1"])
        self.assertEqual(len(self.server.requests[-1]["messages"]), 3)

    def test_system_instruction_and_undo_commands(self):
        p = self.run_console(
            "/system Be concise.\nfirst\nsecond\n/undo\nthird\n"
            "/system off\nfinal\n/exit\n"
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        requests = self.server.requests
        self.assertEqual([m["role"] for m in requests[0]["messages"]], ["system", "user"])
        self.assertEqual([m["content"] for m in requests[2]["messages"]],
                         ["Be concise.", "first", "OK", "third"])
        self.assertEqual(requests[3]["messages"], [{"role": "user", "content": "final"}])
        self.assertIn("Last completed turn removed", p.stdout)

    def test_invalid_system_stays_out_of_model(self):
        p = self.run_console("/system \nhello\n/exit\n")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("invalid_messages", p.stderr)
        self.assertEqual(self.server.requests[0]["messages"], [{"role": "user", "content": "hello"}])


if __name__ == "__main__":
    unittest.main()
