#!/usr/bin/env python3
"""Local Ollama action review output only; no service or approval execution."""
from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reference.capability_catalog_loader import (
    CatalogError, PinnedManifest, build_staged_catalog,
)
from reference.capability_authorization import VerifiedIdentity
from reference.integration_directory import IntegrationError
from reference.local_model_gateway import LocalModelError, LocalOllamaGateway
from reference.local_review_lifecycle import ReviewError, draft_local_review
from reference.local_review_html import render_review_html
from reference.proposal_policy_handoff import HandoffError, InputRule

_FIELD = re.compile(r"^[a-z][a-z0-9_.-]{0,95}:(string|integer|boolean)$")
_MAX_PROMPT = 16384


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect one local AI action draft without granting consent.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--transport", required=True,
                        choices=("mcp", "api", "native", "webhook", "plugin"))
    parser.add_argument("--target-file", required=True,
                        help="Private local target text; avoid exposing it in process arguments")
    parser.add_argument("--field", action="append", default=[], metavar="NAME:TYPE",
                        help="Required argument (string, integer, boolean); repeat as needed")
    parser.add_argument("--format", choices=("html", "json"), default="html")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    opts = parser.parse_args(argv)
    try:
        if len(opts.field) > 32 or any(_FIELD.fullmatch(x) is None for x in opts.field):
            raise ValueError("invalid argument contract")
        rules = tuple(InputRule(*entry.split(":", 1)) for entry in opts.field)
        if len({rule.key for rule in rules}) != len(rules):
            raise ValueError("duplicate field")
        with open(opts.manifest, "rb") as handle:
            raw = handle.read(65537)
        staged = build_staged_catalog((PinnedManifest(raw, opts.sha256),))
        service = staged.revisions[0].service
        requirement = staged.requirements.resolve(service, opts.operation, opts.transport)
        with open(opts.target_file, "rb") as handle:
            target = handle.read(2049)
        if not 1 <= len(target) <= 2048:
            raise ValueError("invalid target length")
        resource = target.decode("utf-8", errors="strict").removesuffix("\n")
        staged.directory.bind(service, connection_id="local-preview",
                              transport=opts.transport)
        prompt = sys.stdin.buffer.read(_MAX_PROMPT + 1)
        if not prompt or len(prompt) > _MAX_PROMPT:
            raise ValueError("invalid prompt")
        user_text = prompt.decode("utf-8", errors="strict")
        now = int(time.time())
        identity = VerifiedIdentity("local-demo", "local-demo", "local-demo", now + 300)
        draft = draft_local_review(
            LocalOllamaGateway(opts.endpoint), opts.model, user_text,
            request_id="req-" + secrets.token_hex(12),
            directory=staged.directory, requirements=staged.requirements,
            permitted_services=frozenset({service}),
            permitted_operations=frozenset({f"{service}:{opts.operation}"}),
            rules=rules, target_resource=resource,
            expected_revision=requirement.revision,
            expected_connection="local-preview", expected_transport=opts.transport,
            identity=identity, now=now,
        )
        if opts.format == "html":
            sys.stdout.write(render_review_html(draft))
        else:
            print(json.dumps(draft.display(), ensure_ascii=True, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, CatalogError, IntegrationError,
            LocalModelError, ReviewError, HandoffError) as exc:
        code = getattr(exc, "code", "review_unavailable")
        print(f"GoreeCloud AI local review unavailable: {code}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
