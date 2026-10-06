# GoreeCloud AI

GoreeCloud AI is GoreeCloud's first-party AI application and local-model experience. It is designed around Glaze UI, integrates with Ollama as an initial replaceable model-runtime foundation, and uses GoreeCloud platform services rather than exposing infrastructure as the product identity.

## Current source milestone

This repository now includes the first executable **Wardveil Security artifact-intake boundary** for GoreeCloud AI.

`reference/ai_artifact_security.py` provides a fail-closed staging-release gate for:

- chat uploads;
- knowledge documents;
- imported assets;
- model artifacts;
- tool artifacts; and
- generated files.

Artifacts remain in private application staging until Wardveil Scan returns current authoritative clean evidence bound to the exact GoreeCloud AI resource identity and SHA-256 digest. The staged file is hashed again after verification and before release so changed bytes cannot inherit an earlier clean finding.

Suspicious content is held. Malicious content is blocked and can request an explicitly authorized Wardveil Quarantine handoff. Unknown, unsupported, stale, expired-clean, mismatched, non-authoritative, malformed, or scanner-unavailable evidence fails closed.

GoreeCloud AI **does not connect directly to ClamAV**. ClamAV remains replaceable malware-scanning infrastructure behind Wardveil Security.

A clean malware scan is also **not permission to execute or load active artifacts**. Model loading, tool execution, generated code execution, deserialization, and other active operations retain separate runtime-policy and sandbox requirements.

See [`docs/WARDVEIL_ARTIFACT_SECURITY.md`](docs/WARDVEIL_ARTIFACT_SECURITY.md) and [`contracts/wardveil.ai-artifact-scan.json`](contracts/wardveil.ai-artifact-scan.json).

## GoreeCloud Code repository context

The repository also includes an executable first-party consumer boundary for GoreeCloud Code repository context. `reference/code_repository_context.py` accepts only fresh, scope-bound, provider-healthy `repository_context` envelopes from the GoreeCloud Code API contract, rejects credential-bearing or provider-specific fields, and caps repository activity collections at 20 items.

Accepted repository content remains untrusted data. Structural acceptance is not an execution authorization, tool authorization, repository-write authorization, or permission to follow instructions embedded in commit messages, issues, pull requests, descriptions, branches, or other repository-controlled text.

GoreeCloud AI does not connect directly to Forgejo and does not receive Forgejo credentials. The current transport contract is Development-level and is designed to move to GoreeCloud Identity and GoreeCloud Mesh without changing the provider-neutral AI consumer boundary.

See [`docs/CODE_REPOSITORY_CONTEXT.md`](docs/CODE_REPOSITORY_CONTEXT.md) and [`contracts/code.repository-context.schema.json`](contracts/code.repository-context.schema.json).

## Validation

```bash
python3 scripts/test_ai_artifact_security.py
python3 scripts/test_code_repository_context.py
python3 scripts/validate_wardveil_ai_integration.py
python3 scripts/validate_code_ai_integration.py
```

These source integrations are not production security, repository-authority, or AI-execution claims. The Wardveil integration is not a production malware-protection claim. Deployed authenticated AI-to-Wardveil transport, live scanner/signature health, real application adapters, quarantine execution, Glaze UI states, Privacy Shield acceptance, and active-artifact runtime policy still require target-environment evidence before production acceptance.
