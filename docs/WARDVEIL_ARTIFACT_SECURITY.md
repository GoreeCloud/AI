# GoreeCloud AI Wardveil Artifact Security

GoreeCloud AI treats every file-like artifact as untrusted input, regardless of whether it comes from a user, an import, a tool, a model source, or an AI-generated workflow.

## Current source-level flow

`untrusted artifact -> private AI staging -> SHA-256 binding -> Wardveil Scan -> evidence validation -> post-scan re-hash -> AI release boundary`

The initial executable reference implementation is `reference/ai_artifact_security.py`.

Supported artifact classes are:

- chat uploads;
- knowledge documents;
- imported assets;
- model artifacts;
- tool artifacts;
- generated files.

All use the normalized Wardveil resource type `ai_artifact` and a GoreeCloud AI internal resource identity of `ai:<context_id>:artifact:<artifact_id>`.

## Release behavior

A staged artifact is released only when Wardveil returns a current, unexpired, authoritative `clean` scan finding bound to the exact resource identity and SHA-256 digest and backed by evidence references. The staging file is hashed again after the clean decision and before release. If the bytes changed while verification was in progress, release fails closed. In the source-level reference, a regular staged file is atomically linked into a destination that must not already exist; a competing writer or a dangling destination symlink is not overwritten. A source symlink is rejected, and the linked bytes are checked once more before removing the staging name. Failed release attempts retain staging where possible and roll back a newly created destination link. If the staged artifact disappears between the initial check and hashing, or during scanning, the reference gate returns a blocked decision rather than propagating an unhandled file-open error. A symlink swapped into the staged path after scanning is rejected before the second hash. Private staging-directory ownership and operating-system protections remain required to mitigate filesystem races; source tests do not establish adversarial runtime acceptance.

For a clean result, evidence references must be a bounded list or tuple (at most 32 entries), with every reference a nonempty, unpadded string of at most 512 characters. The scan envelope itself and both SHA-256 digest bindings are type-checked before any string operations: malformed objects, non-string digests, non-hex characters, and non-64-character digests return explicit blocked decisions rather than escaping the gate as runtime exceptions. Uppercase hexadecimal digests remain accepted and compared case-insensitively. Strings, mappings, mixed-type collections, malformed producer identities, and non-string scan results do not establish clean evidence. Suspicious artifacts remain held for review. Malicious artifacts remain blocked and can produce a non-destructive handoff to Wardveil Quarantine. Unknown, unsupported, expired-clean, future-dated, malformed, mismatched, non-authoritative, or scanner-unavailable evidence never becomes clean.

An exact malicious digest remains blocking after the ordinary evidence-validity window expires. Expiry cannot turn known malicious content into an allowed artifact.

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
- a durable private staging implementation with concurrency-safe release;
- real upload/knowledge/model/tool/generated-artifact adapters using this gate;
- authorized Wardveil Quarantine execution and recovery where claimed;
- Glaze UI states for scanning, held, blocked, unavailable, quarantine, and recovery;
- Privacy Shield data-minimization acceptance;
- separate runtime-policy acceptance before model loading, tool execution, code execution, or other active use.

Passing source CI does not prove that a deployed GoreeCloud AI instance is protected from malware.
