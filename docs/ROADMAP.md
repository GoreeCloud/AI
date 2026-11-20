# GoreeCloud AI implementation roadmap

Not verified or delivered merely because they appear below.

## P0: qualify the source
- Verify Python API tests and React TypeScript build on CI.
- Compile and run Linux Qt Quick and Android Kotlin Compose on real devices.
- Pin lockfiles and add dependency provenance, SCA/SBOM checks.
- Validate OpenRouter Auto, image generation/edits and configured Ollama runtime
  with privacy-safe test data and owner-controlled provider costs.
- Validate MCP Python SDK transport with a trusted test server.
- Adopt native GoreeCloud UI Compose Expressive source adapter, then verify
  Android accessibility and desktop visual parity.

## P1: harden product
- GoreeCloud Identity OIDC/scoped tokens and network TLS/ingress gates.
- GoreeShield per-workflow privacy consent, redaction, retention and deletion.
- Wardveil scans, per-tool sandbox, prompt-injection evaluations and audit.
- Hard per-user budgets, provider privacy filters, cost previews, token accounting.
- Encrypted conversations/documents, search, citations, RAG and secure backups.
- Real human-in-the-loop multi-step agents with state machines and approvals.
- Resource-aware Ollama model selection and streaming/cancel support.

## P2: ecosystem adoption
- GoreeCloud Mesh SDK and consumer app integrations with version negotiation.
- Native voice and speech, document layouts and rich editing, image histories.
- Model marketplace with verified manifests, multimodal workflows and routing.
- Automated CI, supported-browser matrix, accessibility/device acceptance.
- Stable release, rollout, observability and rollback only with verified evidence.
