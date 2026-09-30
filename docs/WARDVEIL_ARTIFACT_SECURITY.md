# GoreeCloud AI Wardveil Artifact Security

GoreeCloud AI treats every file-like artifact as untrusted input, regardless of whether it comes from a user, an import, a tool, a model source, or an AI-generated workflow.

## Current source-level flow

`untrusted artifact -> private AI staging -> SHA-256 binding -> Wardveil Scan -> evidence validation -> post-scan re-hash -> AI release boundary`

The executable contract is represented twice on purpose:

- `reference/ai_artifact_security.py` is the platform/reference implementation used to validate the Wardveil contract independently of the application runtime.
- `server/artifact-security.mjs` is the GoreeCloud AI Node.js runtime gate used by `server/files.mjs` for native attachment intake.

The native upload path now writes bytes into restrictive private staging first. It releases a staged file only after the runtime gate accepts the same digest-bound evidence rules as the reference contract. If no Wardveil scanner transport is configured, the file remains staged and `unverified`; the application does not silently downgrade the requirement.

Supported artifact classes are:

- chat uploads;
- knowledge documents;
- imported assets;
- model artifacts;
- tool artifacts;
- generated files.

All use the normalized Wardveil resource type `ai_artifact` and a GoreeCloud AI internal resource identity of `ai:<context_id>:artifact:<artifact_id>`.

## Release behavior

A staged artifact is released only when Wardveil returns a current, unexpired, authoritative `clean` scan finding bound to the exact resource identity and SHA-256 digest and backed by evidence references. The staging file is hashed again after the clean decision and before release. If the bytes changed while verification was in progress, release fails closed.

Suspicious artifacts remain held for review. Malicious artifacts remain blocked and can produce a non-destructive handoff to Wardveil Quarantine. Unknown, unsupported, expired-clean, future-dated, malformed, mismatched, non-authoritative, or scanner-unavailable evidence never becomes clean.

An exact malicious digest remains blocking after the ordinary evidence-validity window expires. Expiry cannot turn known malicious content into an allowed artifact.

The current development server intentionally has no fabricated Wardveil transport adapter. Its scanner is therefore unconfigured by default, so uploaded bytes return HTTP `202`, remain in private staging, and are recorded as `unverified` rather than being released into the available-file store. A future authenticated Wardveil transport may satisfy the gate; it must not bypass it.

## Glaze UI trust state

The current file model exposes `available`, `unverified`, `held`, and `blocked` trust states. Glaze UI presents these states beside attachment names and explains that only Wardveil-clean attachments may become available to AI context. Upload progress is described as staging for Wardveil verification rather than ordinary storage.

This presentation is a source-level trust-state foundation. It does not claim that a live scanner, quarantine executor, recovery flow, or production security telemetry is present.

## Execution boundary

A clean malware scan is not an execution authorization. It does not by itself permit:

- loading a model into an inference runtime;
- executing a tool or plugin artifact;
- executing generated code;
- unsafe deserialization;
- publishing an artifact outside the application;
- bypassing separate GoreeCloud AI, Wardveil Policy, sandbox, permission, provenance, or trust controls.

Those active operations require their own runtime policy and evidence.

## ClamAV boundary

GoreeCloud AI does not connect directly to `clamd`. It consumes Wardveil Scan. ClamAV remains a replaceable malware-signature engine behind Wardveil Security, so AI does not acquire scanner-specific configuration or policy semantics.

## Quarantine boundary

A blocked AI staging file is not automatically canonical Wardveil Quarantine. GoreeCloud AI owns its staging lifecycle. Wardveil Quarantine requires explicit executor authority and is not deletion.

## Privacy Shield boundary

Shared security evidence should use minimized internal artifact identity, digest, record IDs, and evidence references. Raw file bytes may be supplied to the authorized scanning operation when necessary, but shared security records do not require raw content, source URLs, user-facing filenames, credentials, cookies, or session tokens.

## Production acceptance

This repository currently establishes source integration only. `production_runtime_status` remains `unaccepted`.

Production acceptance still requires evidence for at least:

- deployed authenticated GoreeCloud AI-to-Wardveil transport;
- deployed ClamAV daemon and current signature-health evidence behind Wardveil;
- controlled clean and EICAR/malicious runtime tests;
- timeout and scanner-unavailable runtime tests;
- concurrency-safe and crash-safe private staging/release behavior under target deployment conditions;
- deployment evidence that upload, knowledge, model, tool, and generated-artifact adapters use this gate where applicable;
- authorized Wardveil Quarantine execution and recovery where claimed;
- complete Glaze UI states for scanning, held, blocked, unavailable, quarantine, and recovery;
- Privacy Shield data-minimization acceptance;
- separate runtime-policy acceptance before model loading, tool execution, code execution, or other active use.

Passing source CI does not prove that a deployed GoreeCloud AI instance is protected from malware.
