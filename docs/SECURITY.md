# GoreeCloud AI — Security

**Document version:** 0.1  
**Lifecycle:** Development  
**Security identity:** Wardveil Security

This document defines GoreeCloud AI security requirements and current Development boundaries. Source checks and trust-shaped records are supporting evidence only; they do not establish production protection or target-runtime acceptance by themselves.

## Core security principles

GoreeCloud AI must use least privilege, explicit authorization, bounded inputs, fail-closed trust decisions, authenticated evidence, private-by-default service exposure, and separation between untrusted model/retrieval content and consequential actions.

The AI application must never treat model output, retrieved web content, uploaded files, prompt text, or caller-supplied JSON as authority to perform privileged operations.

## Service boundary

The current backend binds to loopback by default. Direct public exposure of the Node.js backend or Ollama ports is not an accepted production architecture. Supported remote access must use approved GoreeCloud network, identity, TLS, authorization, and service-management boundaries.

`GOREECLOUD_AI_API_TOKEN` is a Development guard, not a replacement for authenticated GoreeCloud Identity and application authorization. A missing token must not be interpreted as production authentication approval merely because loopback development is allowed.

## Model-runtime boundary

Ollama access is backend-owned. Requests require bounded model/message input, timeouts, cancellation, error normalization, and no browser-side assumption that raw Ollama behavior is a stable GoreeCloud application contract.

Model output is untrusted application content. It must not directly become shell commands, privileged service actions, filesystem writes outside approved application scope, authorization decisions, or security/privacy claims.

## Artifact and attachment security

Attachment intake is private and staged until authoritative Wardveil evidence permits release. File storage must enforce size/count/total quotas, bounded identifiers, safe path construction, symlink/path-traversal resistance, controlled deletion, and digest binding.

Released content must match current clean evidence and the source SHA-256. A previous clean decision must not silently authorize changed bytes.

Passive extraction is limited to explicitly supported safe text formats. Complex/active formats such as PDF, HTML, Office, archives, executables/scripts, media, and models require separately designed parsers/sandboxes before support. Extraction does not authorize indexing, retrieval, model context, tool execution, or external processing.

## Identity and application authorization

GoreeCloud Identity establishes authenticated identity and approved claims. GoreeCloud AI remains responsible for resource, conversation, file, Workspace, tool, and application-operation authorization.

Authorization inputs must bind to the exact actor, resource, operation, request/evidence identity, observation time, expiry, and expected application context. Unknown or malformed fields, impossible time ordering, stale evidence, resource/operation mismatch, revocation, or replay must fail closed.

The Development-only durable evidence-use registry stores hashed evidence/request identifiers for replay/revocation state. It is not authenticated provenance and cannot make caller-supplied evidence production-trusted.

## Privacy Shield and Wardveil authority

Privacy Shield governs privacy authorization for data operations. Wardveil governs substantive security/trust boundaries. Structural compatibility with their contracts is insufficient for production acceptance. Real adapters require authenticated transport/provenance, capability/signature or equivalent authority validation where required, exact binding, freshness, revocation/replay controls, and target-runtime acceptance.

## Retrieval, research, and prompt-injection boundary

Local documents and external research are untrusted content even when their source identity is known. Retrieved instructions must not override system/application policy, authorize tools, alter security state, expose secrets, or expand data access.

Future RAG and GoreeCloud Search integrations must preserve source provenance, permission filtering, privacy constraints, citation integrity, and explicit separation between content evidence and action authority.

## Tool and agent security

Tools and agents are disabled as authority until separately implemented and accepted. Future tool execution must use an allowlisted contract, least-privilege service identity, explicit operation/resource scope, bounded arguments, confirmation for consequential actions where required, durable audit/evidence, and independently enforced authorization.

## Secrets and logging

Credentials, private keys, recovery material, raw authorization tokens, reusable capability material, and unrelated private content must not enter normal logs, analytics, model context, or error responses. Logs and evidence should prefer bounded identifiers, hashes, state codes, and minimal diagnostics.

## Supply-chain and release security

Dependencies, actions, runtime versions, source revisions, and release artifacts require governed provenance and vulnerability/update practices. Exact-head CI is necessary but not sufficient. Anchor or production claims additionally require applicable security, privacy, accessibility, recovery, supported-platform, deployment, and release acceptance.

## Current non-claims

GoreeCloud AI is in the Forge lifecycle. Live authenticated Wardveil, Privacy Shield, and Identity integration; broader platform-system acceptance; production RAG; supported deployment; release evidence; and Anchor security acceptance remain outstanding unless later authoritative evidence explicitly closes those gates.
