#!/usr/bin/env python3
"""Bounded, opt-in, synthetic inference checks for 1-4 installed local models.

No user prompts, downloads, persistence, external providers or retries.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import ChatMessage, LocalModelError, LocalOllamaGateway, _model_name

PROMPT = "Reply with the single word READY."
MAX_MODELS = 4


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded local model group smoke check (Development)")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--models", required=True, nargs="+", help="One to four installed local models")
    parser.add_argument("--max-tokens", type=int, default=16, help="1–128 generated tokens per model")
    parser.add_argument("--strict-ready", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    attempted = 0
    passed = 0

    def report(ok: bool, code: str) -> int:
        if args.json:
            print(json.dumps({
                "status": "passed" if ok else "failed",
                "code": code,
                "models_requested": len(args.models),
                "inference_attempted": attempted,
                "inference_verified": passed,
                "processing": "local",
            }, sort_keys=True))
        elif ok:
            print(f"GoreeCloud AI: {passed} synthetic local model check(s) completed.")
        else:
            print(f"GoreeCloud AI group smoke failed ({code}); {passed} verified.", file=sys.stderr)
        return 0 if ok else 1

    try:
        if not 1 <= len(args.models) <= MAX_MODELS:
            return report(False, "invalid_model_count")
        if not 1 <= args.max_tokens <= 128:
            return report(False, "invalid_generation_limit")
        names = [_model_name(name) for name in args.models]
        if len(names) != len(set(names)):
            return report(False, "duplicate_model")
        runtime = LocalOllamaGateway(args.endpoint, args.timeout)
        installed = {entry.name for entry in runtime.list_models()}
        if any(name not in installed for name in names):
            return report(False, "model_not_installed")
        for name in names:
            attempted += 1
            result = runtime.chat(name, [ChatMessage("user", PROMPT)], max_tokens=args.max_tokens)
            if (result.provider != "ollama" or result.processing != "local" or
                    result.model != name or not isinstance(result.content, str) or
                    not result.content.strip()):
                return report(False, "invalid_inference")
            if args.strict_ready and result.content.strip() != "READY":
                return report(False, "unexpected_output")
            passed += 1
        return report(True, "ok")
    except LocalModelError as exc:
        return report(False, exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
