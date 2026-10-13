"""Offline tests for precise, ephemeral local-chat turn deletion."""
import unittest

from test_local_chat_controls import CatalogRuntime
from reference.local_chat_session import LocalChatSession
from reference.local_model_gateway import ChatMessage


class ChatTurnEditTests(unittest.TestCase):
    def setUp(self):
        self.runtime = CatalogRuntime()
        self.session = LocalChatSession(self.runtime, "tiny:1")

    def test_delete_middle_turn_preserves_surrounding_turns(self):
        self.session.set_system_instruction("Private local instructions")
        for question in ("first", "private second", "third"):
            self.session.reply(question)
        self.assertTrue(self.session.delete_turn(1))
        self.assertEqual(
            [pair[0].content for pair in self.session.turns],
            ["first", "third"],
        )
        self.session.reply("fourth")
        sent = self.runtime.requests[-1][1]
        self.assertEqual(sent[0], ChatMessage("system", "Private local instructions"))
        self.assertFalse(any(msg.content == "private second" for msg in sent))
        self.assertEqual(len(self.session.turns), 3)

    def test_invalid_indices_do_not_modify_private_history(self):
        self.session.reply("first")
        before = self.session.turns
        for value in (-1, 1, None, False, True, 0.0, "0"):
            with self.subTest(value=repr(value)):
                self.assertFalse(self.session.delete_turn(value))
                self.assertEqual(self.session.turns, before)
        self.assertTrue(self.session.delete_turn(0))
        self.assertFalse(self.session.delete_turn(0))
        self.assertEqual(self.session.turns, ())


if __name__ == "__main__":
    unittest.main()
