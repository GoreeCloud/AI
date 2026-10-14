#!/usr/bin/env python3
"""Read-only, local-only GoreeCloud AI model readiness probe (Development)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.local_model_gateway import LocalModelError, LocalOllamaGateway, _model_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the already-running loopback Ollama runtime without inference."
    )
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--model", help="Require a particular installed local model.")
    args = parser.parse_args(argv)
    try:
        # Reject malformed model IDs and endpoints before sending a network request.
        model = _model_name(args.model) if args.model is not None else None
        runtime = LocalOllamaGateway(args.endpoint, args.timeout)
        models = runtime.list_models()  # Only GET /api/tags; no chat, prompt or download.
        if not models:
            print("GoreeCloud AI: local runtime reachable, no installed models.", file=sys.stderr)
            return 1
        if model is not None and model not in (item.name for item in models):
            print("GoreeCloud AI: requested local model is not installed.", file=sys.stderr)
            return 1
        if model is not None:
            print("GoreeCloud AI: requested local model is installed (inference not tested).")
        else:
            print(f"GoreeCloud AI: local runtime reachable; {len(models)} installed model(s) "
                  "(inference not tested).")
        return 0
    except LocalModelError as exc:
        print(f"GoreeCloud AI ({exc.code}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
