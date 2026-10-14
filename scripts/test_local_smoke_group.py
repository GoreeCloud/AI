"""Synthetic group smoke regression tests. No live model required."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ai_smoke_group as smoke

class FakeGateway:
    last = None
    unavailable = False
    fail_on = None
    def __init__(self, endpoint, timeout):
        self.calls = []
        FakeGateway.last = self
    def list_models(self):
        self.calls.append("catalog")
        return [type("Model", (), {"name": f"tiny:{i}"})() for i in range(1,5)]
    def chat(self, name, messages, *, max_tokens=None):
        self.calls.append((name, messages[0].content, max_tokens))
        if name == FakeGateway.fail_on:
            raise smoke.LocalModelError("runtime_error", "SECRET")
        return type("Result", (), {
            "provider": "ollama", "processing": "local", "model": name,
            "content": "READY" if name != "tiny:3" else "other answer"})()

class GroupTests(unittest.TestCase):
    def setUp(self):
        FakeGateway.last = None
        FakeGateway.fail_on = None
        self.patcher = patch.object(smoke, "LocalOllamaGateway", FakeGateway)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
    def probe(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = smoke.main(["--models", *args, "--json"])
        return rc, json.loads(out.getvalue())
    def test_sequential_and_budget(self):
        rc, data = self.probe("tiny:1", "tiny:2")
        self.assertEqual(rc, 0)
        self.assertEqual(data["inference_verified"], 2)
        self.assertEqual(FakeGateway.last.calls, [
            "catalog", ("tiny:1", smoke.PROMPT, 16), ("tiny:2", smoke.PROMPT, 16)])
    def test_four_models(self):
        rc, data = self.probe("tiny:1", "tiny:2", "tiny:3", "tiny:4")
        self.assertEqual(rc, 0)
        self.assertEqual(data["inference_verified"], 4)
    def test_absent_preflights_without_chat(self):
        rc, data = self.probe("tiny:1", "missing:1")
        self.assertEqual((rc, data["code"]), (1, "model_not_installed"))
        self.assertEqual(FakeGateway.last.calls, ["catalog"])
    def test_invalid_count_and_duplicate(self):
        for names, code in ((("tiny:1",)*5, "invalid_model_count"),
                            (("tiny:1","tiny:1"), "duplicate_model")):
            FakeGateway.last = None
            rc, data = self.probe(*names)
            self.assertEqual((rc, data["code"]), (1, code))
            self.assertIsNone(FakeGateway.last)
    def test_invalid_model_and_budget(self):
        for flags in (("bad model",), ("tiny:1", "--max-tokens", "0"),
                      ("tiny:1", "--max-tokens", "129")):
            FakeGateway.last = None
            rc, data = self.probe(*flags)
            self.assertEqual(rc, 1)
            self.assertEqual(data["inference_attempted"], 0)
            self.assertIsNone(FakeGateway.last)
    def test_strict_fails_fast_and_redacts(self):
        rc, data = self.probe("tiny:1", "tiny:3", "tiny:4", "--strict-ready")
        self.assertEqual((rc, data["code"]), (1, "unexpected_output"))
        self.assertEqual((data["inference_attempted"], data["inference_verified"]), (2,1))
        self.assertNotIn("tiny:", json.dumps(data))
    def test_strict_exact_and_custom_tokens(self):
        rc, data = self.probe("tiny:1", "--strict-ready", "--max-tokens", "128")
        self.assertEqual(rc, 0)
        self.assertEqual(FakeGateway.last.calls[-1][-1], 128)
    def test_failure_stops_and_redacts(self):
        FakeGateway.fail_on = "tiny:2"
        rc, data = self.probe("tiny:1", "tiny:2", "tiny:4")
        self.assertEqual((rc, data["code"]), (1, "runtime_error"))
        self.assertEqual((data["inference_attempted"], data["inference_verified"]), (2,1))
        self.assertEqual(len(FakeGateway.last.calls), 3)

if __name__ == "__main__":
    unittest.main()
