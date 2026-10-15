"""Regression tests for blank local model completions with fake loopback HTTP."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_local_model_gateway import GatewayTests
from test_local_model_streaming import StreamingTests, frame, ndjson
from reference.local_model_gateway import ChatMessage, LocalModelError

class BlankChatTests(GatewayTests):
    def test_blank_nonstream_responses_fail_closed(self):
        for content in ("", " ", "\n\t"):
            with self.subTest(content=repr(content)):
                self.reply({"done": True, "message": {"role": "assistant", "content": content}})
                with self.assertRaises(LocalModelError) as caught:
                    self.gateway.chat("tiny:1", [ChatMessage("user", "test")])
                self.assertEqual(caught.exception.code, "invalid_response")

class BlankStreamTests(StreamingTests):
    def test_blank_stream_responses_fail_closed(self):
        for chunks in ((frame(done=True),), (frame(" "), frame(done=True)), (frame("\n\t"), frame(done=True))):
            with self.subTest(chunks=chunks):
                self.set_stream(ndjson(*chunks))
                self.assert_stream_error("invalid_response")

if __name__ == "__main__":
    unittest.main()
