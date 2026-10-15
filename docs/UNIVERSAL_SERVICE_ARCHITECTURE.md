# GoreeCloud AI — Universal Service Capability Architecture

**Status:** Development design and offline reference gate only. **Not live service access or production authorization.**

## Goal

GoreeCloud AI is an Ollama-powered, local-first AI platform that can work with thousands of services through reusable protocols and governed capability manifests, without hard-coding an integration for every service. GoreeCloud AI retains a model-provider-independent product contract. Ollama performs inference and suggests actions; GoreeCloud authorizes and executes them.

## Stable boundaries

1. **User interface / model:** Conversations, agents, workspaces, Glaze UI, and model runtimes never confer tool permissions. Model output is untrusted intent, not authorization.
2. **Capability registry:** Trusted, versioned manifests identify a service, operations, input/output schemas, resource scopes, side effects, risk, credential class, transport, origin, version, and health. A disconnected entry grants no access. Tool descriptions cannot expand permissions.
3. **Identity / Policy:** GoreeCloud Identity verifies the user, tenant, session, and trust. GoreeCloud Policy evaluates applicable rules using Privacy Shield data-use constraints, Wardveil Security protections, and other domain-owned authority. Absent, stale, conflicting, or unknown decisions fail closed.
4. **AI Capability Broker:** Checks exact identity, permitted service, operation and target resource, policy freshness, risk classification, explicit purpose, and any action approval. Bind evidence to a unique request ID and SHA-256 digest of canonical backend-validated arguments; do not trust model-supplied risk or grants.
5. **Connector adapters:** Route only through backend-pinned, reviewed handlers for MCP, REST/OpenAPI, native GoreeCloud Mesh, approved plugin SDKs, or constrained webhooks. Never let a model choose arbitrary destinations, transports, credentials, or callback URLs. Enforce protocol and schema version checks, output sanitization, retries, limits, timeouts, and cancellations.
6. **Execution / evidence:** Before effects, recheck permissions, resource scope, connection state, approved arguments, expiry, and replay/idempotency status in an authoritative store. Use redacted audit records and verify actual outcomes, including partial failures, uncertainty, and recovery.
7. **Platform contracts:** Mesh for discovery and coordination; Manager for operational inventory; Glaze for permission UI; Observability for redacted evidence; Everkeep for recovery; Sync only when separately applicable.

## Request flow

    User -> GoreeCloud AI -> Ollama model
                                |
                                v
                       Untrusted typed intent
                                |
                                v
                  GoreeCloud AI Capability Broker
                    Identity + tenant + session
                    Policy + scope + resource
                    Privacy Shield + Wardveil
                    Explicit action approval
                    Exact arguments digest
                                |
                                v
                    Pinned connector transport
                         MCP/API/native/etc.
                                |
                                v
                    Execute -> Verify -> Audit

## Example intent (not executable)

    {
      "request_id": "req-1",
      "service": "github",
      "operation": "issues.write",
      "resource": "repo:sample/demo",
      "arguments_sha256": "<sha256 of validated canonical arguments>"
    }

Only the trusted backend can determine whether the action is read-only, write, or sensitive. Writes and sensitive actions require exact-request, explicitly approved evidence. Grants must not be inferred from tool visibility or an OAuth connection alone.

## Current development work

The existing draft reference/integration_directory.py offers a **non-executing** catalog and pinned route selection across native, MCP, API, webhook and plugin transports. This follow-up introduces reference/capability_authorization.py, a **pure, non-executing** evidence-matching reference, and scripts/test_capability_authorization.py, synthetic tests for denied and stale policy, tenant mismatch, scope mismatch, disconnected integrations, invalid intent, and write approvals.

The reference data types are not cryptographically authenticated, and this example has no trusted adapter issuance, durable replay store, credential isolation, audited execution, or network access. It must not be exposed as a public authorization endpoint or considered production protection.

## Remaining acceptance gates

Authenticated Identity, Policy, and approval adapters; signed or pinned manifest source verification; delegated connection/OAuth management; least-privilege credentials; resource-level permission enforcement; schema/protocol negotiation; sandboxed and network-restricted execution (including SSRF protections for HTTP/webhooks); atomic replay prevention; audit evidence; consent UI and accessibility; cancellation, rollback, data recovery; real tenant-isolation and adversarial tests; target-host end-to-end qualification; and explicit release authorization.

No service credentials, live external calls, provider account changes, deployment, or production tool access are introduced by this development increment.
