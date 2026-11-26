"""Native Linux SSE decoding and endpoint-denial tests; synthetic and offline."""
import json
import unittest

from chat_stream import checked_endpoint
from stream_frames import StreamFrameError, StreamFrames


class LinuxSseTests(unittest.TestCase):
    def test_fragmented_unicode_and_completion(self):
        parser = StreamFrames()
        payload = 'data: ' + json.dumps({"type": "delta", "content": "café"}, ensure_ascii=False) + "\r\n\n"
        encoded = payload.encode("utf-8")
        cut = encoded.index("é".encode()) + 1
        self.assertEqual(parser.feed(encoded[:cut]), [])
        self.assertEqual(parser.feed(encoded[cut:]), [{"type": "delta", "content": "café"}])
        self.assertEqual(parser.feed(b'data: {"type":"done","model":"test","provider":"ollama"}\n'),
                         [{"type": "done", "provider": "ollama", "model": "test"}])
        self.assertTrue(parser.done)
        self.assertEqual(parser.feed(b"data: invalid\n"), [])

    def test_multiple_events(self):
        parser = StreamFrames()
        result = parser.feed(
            b": keepalive\n"
            b'data: {"type":"delta","content":"a"}\n'
            b'data: {"type":"delta","content":"b"}\n'
        )
        self.assertEqual([e["content"] for e in result], ["a", "b"])

    def test_invalid_json_or_utf8_and_invalid_event_types(self):
        for data in (
            b"data: {bad}\n",
            b"data: \xff\n",
            b'data: {"type":"unknown"}\n',
            b'data: {"type":"delta","content":17}\n',
        ):
            with self.subTest(data=data):
                with self.assertRaises(StreamFrameError):
                    StreamFrames().feed(data)

    def test_error_keeps_preceding_delta_and_ends_stream(self):
        parser = StreamFrames()
        self.assertEqual(parser.feed(
            b'data: {"type":"delta","content":"partial"}\n\n'
            b'data: {"type":"error","message":"SECRET_PROVIDER_REASON"}\n\n'
            b'data: {"type":"done"}\n\n'
        ), [
            {"type": "delta", "content": "partial"},
            {"type": "error"},
        ])
        self.assertTrue(parser.done)
        self.assertEqual(parser.feed(b'data: {"type":"done"}\n\n'), [])

    def test_rejects_oversized_lines_and_total_response(self):
        with self.assertRaises(StreamFrameError):
            StreamFrames().feed(b"x" * 100_001)
        with self.assertRaises(StreamFrameError):
            StreamFrames().feed(b"data: " + b"x" * 100_001 + b"\n")
        with self.assertRaises(StreamFrameError):
            StreamFrames().feed(b":x\n" * 200_001)

    def test_rejects_excessive_text_and_event_count(self):
        parser = StreamFrames()
        sample = b'data: {"type":"delta","content":"' + b"a" * 80_000 + b'"}\n'
        self.assertEqual(len(parser.feed(sample)), 1)
        with self.assertRaises(StreamFrameError):
            parser.feed(sample)
        parser = StreamFrames()
        for _ in range(10_000):
            parser.feed(b'data: {"type":"delta","content":""}\n')
        with self.assertRaises(StreamFrameError):
            parser.feed(b'data: {"type":"delta","content":""}\n')

    def test_requires_https_except_localhost(self):
        for value in ("https://ai.example.test/api", "http://localhost:8000",
                      "http://127.0.0.1:8000", "http://[::1]:8000"):
            self.assertEqual(checked_endpoint(value), value)
        for bad in ("http://example.test", "file:///tmp", "https://name:pass@ai.example.test",
                    "https://ai.example.test:99999", "https://ai.example.test/#foo",
                    "https://ai.example.test/?foo=1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                checked_endpoint(bad)


if __name__ == "__main__":
    unittest.main()
