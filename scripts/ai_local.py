#!/usr/bin/env python3
"""Local-only model discovery and single-prompt inference from stdin."""

from __future__ import annotations

import argparse
from contextlib import closing
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import (
    ChatMessage,
    LocalModelError,
    LocalOllamaGateway,
    MAX_MESSAGE_BYTES,
)


def _terminal_safe(value: str) -> str:
    """Make untrusted model output printable without terminal escape/control effects."""
    return "".join(
        char if char in ("\n", "\t") or unicodedata.category(char) not in ("Cc", "Cf", "Cs")
        else ascii(char)[1:-1]
        for char in value
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
    chat.add_argument("--stream", action="store_true",
                      help="Print local model tokens as they arrive; output is provisional until completion.")
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
        messages = [ChatMessage(role="user", content=prompt)]
        if args.stream:
            emitted = False
            try:
                with closing(runtime.iter_chat(args.model, messages)) as events:
                    for event in events:
                        if event.done:
                            print(flush=True)
                            return 0
                        print(_terminal_safe(event.delta), end="", flush=True)
                        emitted = True
            except (KeyboardInterrupt, LocalModelError) as exc:
                if emitted:
                    print("\nGoreeCloud AI: partial stream is NOT a completed answer.", file=sys.stderr)
                if isinstance(exc, KeyboardInterrupt):
                    print("GoreeCloud AI: local generation interrupted.", file=sys.stderr)
                    return 130
                raise
            print("GoreeCloud AI: stream lacked completion.", file=sys.stderr)
            return 1
        result = runtime.chat(args.model, messages)
        print(_terminal_safe(result.content))
        return 0
    except LocalModelError as exc:
        print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
