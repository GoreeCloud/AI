#!/usr/bin/env python3
"""Explicit, synthetic, loopback-only inference smoke check for GoreeCloud AI Development.

Never uses personal prompts, external providers, tools, file writes or retries.
An installed model is NOT proof of successful inference; this command requests
one intentionally synthetic inference from a model the owner already installed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import (
    ChatMessage, LocalModelError, LocalOllamaGateway, _model_name,
)

_SYNTHETIC_PROMPT = "Reply with the single word READY."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicit synthetic local Ollama inference smoke check (Development)."
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--model", required=True, help="An already-installed local model.")
    parser.add_argument("--json", action="store_true", help="Redacted machine-readable status.")
    parser.add_argument("--max-tokens", type=int, default=16)
    parser.add_argument("--strict-ready", action="store_true")
    args = parser.parse_args(argv)
    attempted = False

    def report(ok: bool, code: str) -> int:
        if args.json:
            print(json.dumps({
                "status": "passed" if ok else "failed",
                "code": code,
                "inference_attempted": attempted,
                "inference_verified": ok,
                "processing": "local",
            }, sort_keys=True))
        elif ok:
            print("GoreeCloud AI: synthetic local inference completed; output kept private.")
        else:
            print(f"GoreeCloud AI smoke check failed ({code}).", file=sys.stderr)
        return 0 if ok else 1

    try:
        model = _model_name(args.model)
        if not 1 <= args.max_tokens <= 128:
            return report(False, "invalid_generation_limit")
        gateway = LocalOllamaGateway(args.endpoint, args.timeout)
        catalog = gateway.list_models()
        if model not in (entry.name for entry in catalog):
            return report(False, "model_not_installed")
        # Intentionally no personal content, no retries, no nonlocal fallback.
        attempted = True
        answer = gateway.chat(model, [ChatMessage("user", _SYNTHETIC_PROMPT)],
                              max_tokens=args.max_tokens)
        if (answer.provider != "ollama" or answer.model != model
                or answer.processing != "local" or not isinstance(answer.content, str)
                or not answer.content.strip()):
            return report(False, "invalid_inference")
        return report(True, "ok")
    except LocalModelError as exc:
        return report(False, exc.code)


if __name__ == "__main__":
    raise SystemExit(main())
