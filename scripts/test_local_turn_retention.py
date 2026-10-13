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
