#!/usr/bin/env python3
"""Local-only model discovery and single-prompt inference from stdin."""

from __future__ import annotations

import argparse
import json
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
    _model_name,
    _validated_messages,
)


def _terminal_safe(value: str) -> str:
    """Make untrusted model output printable without terminal escape/control effects."""
    return "".join(
        char if char in ("\n", "\t") or unicodedata.category(char) not in ("Cc", "Cf", "Cs")
        else ascii(char)[1:-1]
        for char in value
    )


def _run_repl(runtime: LocalOllamaGateway, model: str, *, stream: bool, keep: int | None = None) -> int:
    from reference.local_chat_session import LocalChatSession

    session = LocalChatSession(runtime, model)
    if keep is not None:
        session.set_turn_limit(keep)
    print("GoreeCloud AI — local-only in-memory chat. /help for commands.")
    while True:
        try:
            prompt = input("You> ")
        except EOFError:
            print()
            session.reset()
            return 0
        except KeyboardInterrupt:
            print("\nUse /exit to leave or /reset to clear the conversation.")
            continue

        regenerate = False
        ephemeral = False
        edit_requested = False
        if prompt.startswith("//"):
            prompt = prompt[1:]  # Literal user message starting with '/'.
        elif prompt.startswith("/"):
            command = prompt.strip()
            if command in ("/exit", "/quit"):
                session.reset()
                return 0
            if command == "/reset":
                session.reset()
                print("Conversation cleared from this process.")
                continue
            if command == "/clear":
                removed = session.clear_turns()
                print(f"Cleared {removed} local turn(s); system instruction and retention cap preserved.")
                continue
            if command == "/status":
                print(f"Retained conversation turns: {len(session.turns)} (memory only)")
                retention = ("automatic" if session.turn_limit is None else
                             "stateless" if session.turn_limit == 0 else
                             f"last {session.turn_limit} completed turn(s)")
                print(f"Retention mode: {retention} (process memory only)")
                print(f"Local model: {_terminal_safe(session.model)}; "
                      f"system instruction: {'on' if session.has_system_instruction else 'off'}")
                continue
            if command == "/turns":
                numbers = ", ".join(str(i) for i in range(1, len(session.turns) + 1))
                print("Completed local turn numbers: " + (numbers or "(none)"))
                print("Use /delete N to remove one numbered turn; contents stay private.")
                continue
            if command == "/keep":
                current = session.turn_limit
                print("Retained completed-turn cap: " + ("automatic" if current is None else str(current)))
                continue
            if command == "/keep auto":
                session.restore_automatic_retention()
                print("Automatic retention restored; previously deleted turns stay deleted.")
                continue
            if command.startswith("/keep "):
                number = command[6:].strip()
                if number.isascii() and number.isdecimal() and len(number) <= 2:
                    try:
                        session.set_turn_limit(int(number))
                        print(f"Local turn retention cap set to {session.turn_limit}; excess prior turns cleared.")
                    except LocalModelError as exc:
                        print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
                else:
                    print("Enter an integer turn limit from 0 to 50; history unchanged.")
                continue
            if command == "/undo":
                if session.undo_last_turn():
                    print("Last completed turn removed from in-memory context.")
                else:
                    print("No completed turn to undo.")
                continue
            if command.startswith("/delete "):
                number = command[8:].strip()
                if (number.isascii() and number.isdecimal() and len(number) <= 6
                        and int(number) > 0 and session.delete_turn(int(number) - 1)):
                    print("Selected completed turn removed from local in-memory context.")
                else:
                    print("Invalid or missing completed turn number; history unchanged.")
                continue
            if command in ("/rewind", "/forget") or command.startswith(("/rewind ", "/forget ")):
                action, _, value = command.partition(" ")
                number = value.strip()
                if not number.isascii() or not number.isdecimal() or len(number) > 6:
                    print("Specify a valid completed-turn count; history unchanged.")
                else:
                    try:
                        count = int(number)
                        removed = (session.rewind_to(count) if action == "/rewind"
                                   else session.forget_oldest(count))
                        print(f"Discarded {removed} completed turn(s) from process memory.")
                    except LocalModelError as exc:
                        print(f"GoreeCloud AI ({exc.code}): {exc}; history unchanged.", file=sys.stderr)
                continue
            if command == "/models":
                try:
                    models = runtime.list_models()
                    print("Installed local models: " +
                          (", ".join(_terminal_safe(m.name) for m in models) if models else "(none)"))
                except LocalModelError as exc:
                    print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
                continue
            if command == "/model":
                print("Active local model: " + _terminal_safe(session.model))
                continue
            if command.startswith("/model "):
                try:
                    changed = session.switch_model(command[len("/model "):])
                    print("Local model selected: " + _terminal_safe(session.model) +
                          ("; prior context cleared." if changed else "; unchanged."))
                except LocalModelError as exc:
                    print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
                continue
            if command == "/system":
                print("System instruction: " + ("on" if session.has_system_instruction else "off") +
                      " (content is never shown).")
                continue
            if command == "/system off":
                session.set_system_instruction(None)
                print("System instruction and prior context cleared.")
                continue
            if command.startswith("/system "):
                try:
                    session.set_system_instruction(prompt[len("/system "):])
                    print("Session-only system instruction set; prior context cleared.")
                except LocalModelError as exc:
                    print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
                continue
            if command == "/help":
                print("/models lists local models; /model NAME switches models and clears context; "
                      "/system TEXT sets ephemeral system instruction; /system off clears it; "
                      "/turns lists redacted turn numbers; /keep N caps retained turns; /keep auto restores automatic retention; /delete N removes one; /undo removes the last turn; /rewind N keeps the first N turns; /forget N drops the oldest N turns; /again regenerates the last answer; /edit TEXT revises the last completed question; /once TEXT answers without prior chat history or retention; /clear forgets turns but preserves system instruction; /reset clears all context; "
                      "/status reports configuration and count; /exit quits; "
                      "// sends a message starting with /.")
                continue
            if command == "/once":
                print("Use /once TEXT for a response without prior turns or retention.")
                continue
            if command.startswith("/once "):
                prompt = prompt[len("/once "):]
                ephemeral = True
            elif command == "/again":
                regenerate = True
            elif command.startswith("/edit "):
                prompt = prompt[6:]
                edit_requested = True
            else:
                print("Unknown command. Use /help. Nothing sent to the model.")
                continue

        if not prompt.strip():
            continue
        try:
            if stream:
                emitted = False
                print("AI> ", end="", flush=True)
                try:
                    with closing(session.iter_edit_last(prompt) if edit_requested else
                                 session.iter_reply_once(prompt) if ephemeral else
                                 session.iter_regenerate_last() if regenerate else
                                 session.iter_reply(prompt)) as events:
                        for event in events:
                            if event.done:
                                print(flush=True)
                                break
                            print(_terminal_safe(event.delta), end="", flush=True)
                            emitted = True
                except (LocalModelError, KeyboardInterrupt):
                    if emitted:
                        print("\nPartial response discarded from conversation history.", file=sys.stderr)
                    else:
                        print()
                    raise
            else:
                answer = (session.edit_last(prompt) if edit_requested else
                          session.reply_once(prompt) if ephemeral else
                          session.regenerate_last() if regenerate else session.reply(prompt))
                print("AI> " + _terminal_safe(answer.content))
            if ephemeral:
                print("One-time reply: not added to conversation memory.")
            elif not session.last_reply_retained:
                if session.turn_limit == 0:
                    print("Private stateless mode: completed turn not retained.")
                else:
                    print("New answer not retained; earlier completed turns remain in memory.", file=sys.stderr)
        except KeyboardInterrupt:
            print("Generation interrupted; the incomplete turn was not retained.", file=sys.stderr)
        except LocalModelError as exc:
            print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)


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
    chat.add_argument("--validate-only", action="store_true",
                      help="Validate the local request offline without contacting a model.")
    chat.add_argument("--max-tokens", type=int, choices=range(1, 513), metavar="1..512")
    chat.add_argument("--stream", action="store_true",
                      help="Print local model tokens as they arrive; output is provisional until completion.")
    repl = commands.add_parser("repl", help="Start private multi-turn local chat in memory.")
    repl.add_argument("--model", required=True)
    repl.add_argument("--keep", type=int, choices=range(51), metavar="0..50",
                      help="Maximum completed turns held in memory (0: stateless).")
    repl.add_argument("--no-stream", action="store_true", help="Wait for complete responses before displaying.")
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
        if args.command == "repl":
            return _run_repl(runtime, args.model, stream=not args.no_stream, keep=args.keep)
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
        if args.validate_only:
            _model_name(args.model)
            _validated_messages(messages)
            print(json.dumps({
                "status": "valid",
                "network_attempted": False,
                "inference_attempted": False,
                "model_installed_verified": False,
                "processing": "local",
            }, sort_keys=True))
            return 0
        if args.stream:
            emitted = False
            try:
                with closing(runtime.iter_chat(args.model, messages, max_tokens=args.max_tokens)) as events:
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
        result = runtime.chat(args.model, messages, max_tokens=args.max_tokens)
        print(_terminal_safe(result.content))
        return 0
    except LocalModelError as exc:
        print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
