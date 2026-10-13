#!/usr/bin/env python3
"""Local-only model discovery and single-prompt inference from stdin."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import (
    ChatMessage,
    LocalModelError,
    LocalOllamaGateway,
    MAX_MESSAGE_BYTES,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="GoreeCloud AI Development: local-only Ollama model discovery and chat."
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=30)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("models", help="List installed local models.")
    chat = commands.add_parser("chat", help="Read one user prompt from stdin and print the response.")
    chat.add_argument("--model", required=True)
    args = parser.parse_args(argv)
    try:
        runtime = LocalOllamaGateway(args.endpoint, args.timeout)
        if args.command == "models":
            models = runtime.list_models()
            if not models:
                print("No local models installed.", file=sys.stderr)
            for model in models:
                print(model.name)
            return 0
        if sys.stdin.isatty():
            print("Enter the prompt using standard input, not a command-line argument.", file=sys.stderr)
            return 2
        content_bytes = sys.stdin.buffer.read(MAX_MESSAGE_BYTES + 1)
        if len(content_bytes) > MAX_MESSAGE_BYTES:
            raise LocalModelError("request_too_large", "The input prompt is too large.")
        try:
            prompt = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise LocalModelError("invalid_messages", "Prompt must be UTF-8 text.") from None
        result = runtime.chat(args.model, [ChatMessage(role="user", content=prompt)])
        print(result.content)
        return 0
    except LocalModelError as exc:
        print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
