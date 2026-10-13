"""Offline retention cap regressions for private local chat."""
import unittest
from test_local_chat_controls import CatalogRuntime
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import ChatMessage, LocalModelError

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = CatalogRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_capped_retention_preserves_system_not_old_turns(self):
        self.session.set_system_instruction("Private system")
        for prompt in ("alpha", "beta", "gamma"):
            self.session.reply(prompt)
        self.session.set_turn_limit(2)
        self.assertEqual([pair[0].content for pair in self.session.turns], ["beta", "gamma"])
        self.session.reply("delta")
        self.assertEqual([pair[0].content for pair in self.session.turns], ["gamma", "delta"])
        sent = self.runtime.requests[-1][1]
        self.assertEqual(sent[0], ChatMessage("system", "Private system"))
        self.assertFalse(any(msg.content == "alpha" for msg in sent))

    def test_zero_retention_does_not_forward_old_prompts(self):
        self.session.reply("older")
        self.assertTrue(self.session.last_reply_retained)
        self.session.set_turn_limit(0)
        self.assertFalse(self.session.last_reply_retained)
        self.assertEqual(self.session.turns, ())
        self.session.reply("secret")
        self.assertEqual(self.session.turns, ())
        self.assertFalse(self.session.last_reply_retained)
        self.session.reply("another")
        self.assertEqual(self.runtime.requests[-1][1], (ChatMessage("user", "another"),))

    def test_invalid_limit_does_not_mutate_context(self):
        self.session.reply("retain")
        original = self.session.turns
        for value in (-1, 51, True, False, 1.0, "1", None):
            with self.subTest(value=repr(value)):
                with self.assertRaises(LocalModelError):
                    self.session.set_turn_limit(value)
                self.assertEqual(original, self.session.turns)

if __name__ == "__main__":
    unittest.main()

class RetentionCliTests(unittest.TestCase):
    def test_console_keep_limit_and_renumbered_turns(self):
        from test_local_chat_controls import ConsoleControlTests
        harness = ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            result = harness.run_console(
                "/keep 1\nprivate first\nprivate second\n/turns\n"
                "/keep 0\nprivate third\n/turns\n/exit\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Local turn retention cap set to 1", result.stdout)
            self.assertIn("Local turn retention cap set to 0", result.stdout)
            self.assertIn("Completed local turn numbers: 1", result.stdout)
            self.assertIn("Completed local turn numbers: (none)", result.stdout)
            self.assertEqual(
                [m["content"] for m in harness.server.requests[-1]["messages"]],
                ["private third"],
            )
            self.assertNotIn("private first", result.stdout)
        finally:
            harness.tearDown()

class RetentionStartupTests(unittest.TestCase):
    def test_stateless_launch_option_applies_before_first_prompt(self):
        import subprocess
        import sys
        from test_local_chat_controls import ConsoleControlTests, ROOT
        harness = ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            invocation = [
                sys.executable, str(ROOT / "scripts/ai_local.py"), "--endpoint",
                f"http://127.0.0.1:{harness.server.server_port}", "repl",
                "--model", "tiny:1", "--no-stream", "--keep", "0",
            ]
            result = subprocess.run(
                invocation, input="private one\nprivate two\n/turns\n/exit\n",
                text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Private stateless mode: completed turn not retained.", result.stdout)
            self.assertNotIn("Context reset: answer too large", result.stderr)
            self.assertIn("Completed local turn numbers: (none)", result.stdout)
            self.assertEqual(len(harness.server.requests), 2)
            self.assertEqual(
                [item["content"] for item in harness.server.requests[1]["messages"]],
                ["private two"],
            )
            invocation[-1] = "51"
            invalid = subprocess.run(
                invocation, input="", text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(len(harness.server.requests), 2)
        finally:
            harness.tearDown()

class HistoryClearTests(unittest.TestCase):
    def test_clear_keeps_ephemeral_instruction_and_retention_limit(self):
        runtime = CatalogRuntime()
        session = LocalChatSession(runtime, "tiny:1")
        session.set_system_instruction("Short responses only")
        session.set_turn_limit(1)
        session.reply("secret old prompt")
        self.assertEqual(session.clear_turns(), 1)
        self.assertEqual(session.clear_turns(), 0)
        self.assertEqual(session.turns, ())
        self.assertTrue(session.has_system_instruction)
        self.assertEqual(session.turn_limit, 1)
        session.reply("new prompt")
        self.assertEqual(
            runtime.requests[-1][1],
            (ChatMessage("system", "Short responses only"),
             ChatMessage("user", "new prompt")),
        )

    def test_clear_respects_stateless_mode(self):
        session = LocalChatSession(CatalogRuntime(), "tiny:1")
        session.set_turn_limit(0)
        self.assertEqual(session.clear_turns(), 0)
        self.assertFalse(session.last_reply_retained)

    def test_console_clear_preserves_settings_until_reset(self):
        from test_local_chat_controls import ConsoleControlTests
        harness = ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            result = harness.run_console(
                "/system Keep the wording short\n/keep 1\nsecret old prompt\n"
                "/clear\nnew prompt\n/status\n/reset\nafter reset\n/exit\n"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Cleared 1 local turn(s); system instruction and retention cap preserved.", result.stdout)
            self.assertIn("system instruction: on", result.stdout)
            self.assertEqual(
                [x["content"] for x in harness.server.requests[1]["messages"]],
                ["Keep the wording short", "new prompt"],
            )
            self.assertEqual(
                [x["content"] for x in harness.server.requests[2]["messages"]],
                ["after reset"],
            )
        finally:
            harness.tearDown()


class AutomaticRetentionRestoreTests(unittest.TestCase):
    def test_stateless_to_automatic_keeps_only_new_history(self):
        runtime = CatalogRuntime()
        session = LocalChatSession(runtime, "tiny:1")
        session.set_system_instruction("Be concise")
        session.set_turn_limit(0)
        session.reply("discard me")
        session.restore_automatic_retention()
        self.assertIsNone(session.turn_limit)
        self.assertEqual(session.turns, ())
        self.assertTrue(session.has_system_instruction)
        session.reply("retain this")
        session.reply("use this context")
        sent = runtime.requests[-1][1]
        self.assertEqual([m.content for m in sent if m.role == "user"],
                         ["retain this", "use this context"])
        self.assertEqual(len(session.turns), 2)

    def test_console_restore_retention_does_not_replay_old_turns(self):
        from test_local_chat_controls import ConsoleControlTests
        harness = ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            result = harness.run_console(
                "/system Be concise\n/keep 0\nsecret old message\n"
                "/keep auto\nretain one\nretain two\n/keep\n/exit\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Automatic retention restored", result.stdout)
            self.assertIn("Retained completed-turn cap: automatic", result.stdout)
            sent = harness.server.requests[2]["messages"]
            self.assertEqual([m["content"] for m in sent if m["role"] == "user"],
                             ["retain one", "retain two"])
            self.assertFalse(any(m["content"] == "secret old message" for m in sent))
        finally:
            harness.tearDown()


class RetentionModeStatusTests(unittest.TestCase):
    def test_status_reports_automatic_capped_and_stateless_modes_without_contents(self):
        from test_local_chat_controls import ConsoleControlTests
        harness = ConsoleControlTests("test_missing_model_does_not_discard_context")
        harness.setUp()
        try:
            result = harness.run_console(
                "/status\n/keep 2\n/status\n/keep 0\n/status\n/keep auto\n/status\n/exit\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count("Retention mode: automatic"), 2)
            self.assertIn("Retention mode: last 2 completed turn(s)", result.stdout)
            self.assertIn("Retention mode: stateless", result.stdout)
            self.assertEqual(len(harness.server.requests), 0)
        finally:
            harness.tearDown()
