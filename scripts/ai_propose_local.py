#!/usr/bin/env python3
"""Opt-in local Ollama proposal preview. NO real service binding or execution."""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.capability_catalog_loader import CatalogError, PinnedManifest, build_staged_catalog
from reference.integration_directory import IntegrationError
from reference.local_action_planner import LocalProposalError, propose_with_local_ollama
from reference.local_model_gateway import LocalModelError, LocalOllamaGateway

_MAX_MANIFEST = 65536
_MAX_PROMPT = 16384


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Development-only local proposal PREVIEW; no real service is connected."
    )
    parser.add_argument("--manifest", required=True, help="Path to reviewed local JSON service manifest")
    parser.add_argument("--sha256", required=True, help="Independently verified manifest SHA-256 pin")
    parser.add_argument("--model", required=True, help="Installed Ollama local model")
    parser.add_argument("--transport", required=True, choices=("mcp", "api", "native", "webhook", "plugin"))
    parser.add_argument("--permit", action="append", required=True, metavar="OPERATION",
                        help="Explicit operation in this PREVIEW, not a real account permission")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    args = parser.parse_args(argv)
    try:
        with open(args.manifest, "rb") as file:
            manifest_bytes = file.read(_MAX_MANIFEST + 1)
        staged = build_staged_catalog((PinnedManifest(manifest_bytes, args.sha256),))
        definition = staged.revisions[0]
        # This binding is synthetic and never contains a provider account or token.
        staged.directory.bind(definition.service, connection_id="preview-only",
                              transport=args.transport)
        requested = frozenset(args.permit)
        # Explicitly verify every requested operation is in this manifest and route.
        if len(requested) != len(args.permit):
            raise ValueError("duplicate preview operations")
        for operation in requested:
            staged.requirements.resolve(definition.service, operation, args.transport)
        prompt = sys.stdin.buffer.read(_MAX_PROMPT + 1)
        if not prompt or len(prompt) > _MAX_PROMPT:
            raise ValueError("empty or oversized prompt")
        user_text = prompt.decode("utf-8", errors="strict")
        runtime = LocalOllamaGateway(args.endpoint)
        result = propose_with_local_ollama(
            runtime, args.model, user_text,
            request_id="req-" + secrets.token_hex(12),
            directory=staged.directory,
            requirements=staged.requirements,
            permitted_services=frozenset({definition.service}),
            permitted_operations=frozenset(
                f"{definition.service}:{operation}" for operation in requested
            ),
        )
        preview = result.redacted_preview()
        preview["connection"] = "synthetic_preview_only"
        preview["execution"] = "disabled"
        print(json.dumps(preview, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, CatalogError, IntegrationError,
            LocalProposalError, LocalModelError) as exc:
        # Errors deliberately omit user/model content and connection details.
        code = getattr(exc, "code", "preview_unavailable")
        print(f"GoreeCloud AI proposal preview unavailable: {code}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
