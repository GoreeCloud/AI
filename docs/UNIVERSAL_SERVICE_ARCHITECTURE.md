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

## Development hardening: trusted operation baselines

The new `reference/capability_requirements.py` adds an **operator-configured, versioned** requirements catalog. A capability must be defined in both the service directory and the requirements catalog before the non-executing broker returns a route. Its pinned transport must be explicitly allowed, and every operation has a backend-owned minimum risk classification.

**Risk cannot be downgraded:** If an operation is classified `write` or `sensitive` in the trusted catalog, a Policy response labeling it `read` is rejected. Policy can elevate risk (for example, classify an otherwise read-only request as sensitive), triggering an approval requirement. Any missing/malformed requirement or transport mismatch fails closed. Approval receipts now include the exact session, service, operation, and resource, in addition to subject, tenant, request ID, and arguments digest.

The requirements catalog only models **trusted configuration supplied by a future backend**. It does not verify signatures, manifest provenance, protocol schemas, or domain ownership. Adding a requirement in Python source is not a live connector enrollment or permission. No default permission manifests are enabled for the illustrative third-party service examples.

Unit tests exercise downgrade attempts, policy escalation, transport drift, missing requirements, invalid manifests, approval context confusion, and malformed risk values. These tests provide **offline reference-contract evidence**, not authenticated end-to-end enforcement.

## Development increment: scalable discovery and replay reservation

The development-only \`reference/capability_discovery.py\` uses the existing backend-controlled integration directory and risk/transport requirements catalog to return **only operations that are (1) connected, (2) explicitly permitted, and (3) backed by a compatible registered operation requirement**. Descriptors include display title, service/operation, pinned transport, minimum risk, and requirement revision; they intentionally omit internal connection IDs, credentials, and endpoint URLs. Keyset pagination supports bounded pages of up to 100 descriptors; synthetic tests exercise **1,200 distinct capabilities** without one hard-coded adapter per service. The cursor is pagination metadata, *not* an authentication or authorization token. Permission grants must come from real trusted Identity/Policy inputs, not a request or model-supplied list. Discovery currently scans the in-memory catalog and is not a provider discovery service, distributed snapshot, or deployed API.

The development-only \`reference/capability_replay_ledger.py\` uses a trusted backend-supplied SQLite connection and atomic \`BEGIN IMMEDIATE\` reservations with a unique tenant/request identity digest. Reservation fingerprints bind the authorized route's subject, tenant, session, request, service, operation, resource, canonical argument digest, policy version, requirement revision, pinned transport, and connection ID. Database rows store **hashes and lifecycle state only**, avoiding raw user content, resource paths, and credentials. Duplicate request IDs within a tenant are rejected even if later arguments, session, target, or policy revision differ. Final \`succeeded\`, \`failed\`, and \`unknown\` outcomes remain reserved and non-retryable under the same ID. Tests exercise reopening the SQLite file, cross-tenant separation, ambiguous effects, digest mismatch, and database failure. Adding a new request ID is **not** authorization to repeat an irreversible operation: the future runtime must enforce idempotency or user consent at the action level.

**This ledger does not provide exactly-once effects or production replay guarantees.** The database's true durability depends on deployment configuration, WAL/fsync/storage semantics, process coordination, backup, and disaster recovery. No real service action is currently dispatched; there is no authenticated evidence issuance, cross-process distributed transaction coordinator, effect verification, automatic replay cleanup, production recovery workflow, or protected model-facing API. A crash between external side effects and marking final state must remain \`reserved\` until operator reconciliation; no automatic resend. Failed/unknown outcomes require a new, independently authorized request with the appropriate idempotency and approval safeguards. Production must durably reserve *after fresh authorization and immediately before dispatch*, and re-evaluate policy, resource scope, and connector binding at the actual effect boundary.

## Development increment: declarative, pinned service manifests

\`reference/capability_manifest.py\` defines a strict JSON-v1 manifest contract that creates the existing \`Integration\` and \`OperationRequirement\` records without hard-coding each service in Python. Each manifest contains one service identifier, display title, revision, supported transports, and up to 64 bounded operation definitions with explicit minimum risk and allowed transport subsets. A manifest may not declare endpoint URLs or other arbitrary fields. The parser rejects duplicate JSON keys, malformed records, invalid operation risk, undeclared transports, control characters in display titles, and oversized documents.

Before parsing, the module requires an **exact SHA-256 match against a separately supplied, operator-pinned expected digest**. This verifies byte-for-byte integrity **only if the expected pin itself comes from a separately authenticated, approved governance channel**. A model, service response, or API caller presenting its own document and matching digest is *not* trusted. SHA-256 pinning is not a digital signature, certificate validation, publisher identity, manifest security review, revocation infrastructure, provenance guarantee, or permission. The parser performs no network requests and does not automatically register or connect services.

A trusted control plane must stage and review manifests, authenticate the source of pins, validate ownership and version compatibility, atomically commit directory + operation-requirement records, and handle rollback on conflict. Application security and domain authorities still evaluate every action. The existing example third-party entries remain disconnected until a trusted backend configuration explicitly enrolls them; no broad connection privileges are conferred by a manifest.

## Development increment: canonical arguments and all-or-nothing catalog staging

`reference/capability_arguments.py` now provides bounded, deterministic Python JSON encoding of backend-validated tool arguments. `reference/capability_authorization.py` **requires the concrete `validated_arguments` object** and compares its newly computed digest with the model-requested `CapabilityIntent.arguments_sha256` and the independently trusted Policy evidence. A copied or forged digest cannot authorize a different argument object. The encoder caps payload size (64 KiB), depth (16), and node count; rejects cycles, non-JSON values, NaN/Infinity, unsafe integers beyond the exact JavaScript integer range, and invalid Unicode. It does **not** perform per-tool JSON Schema validation or standardize JSON across runtimes: the production backend must validate the operation's input schema, preserve the exact canonical bytes through policy/approval/dispatch, and define portable rules before cross-language deployment. Sensitive argument bytes must not enter logs.

`reference/capability_catalog_loader.py` constructs an entirely **new, disconnected** `IntegrationDirectory` and `RequirementCatalog` from a bounded set of operator-pinned manifests. It validates all source manifests before registering anything, rejects duplicate services and conflicting definitions, and returns a sorted digest of manifest revisions. If any source fails, **no candidate registry is returned and no existing catalog is modified**. The owning backend must authenticate manifest pins, maintain a versioned trusted snapshot, and perform an atomic activation/rollback with safe connection and policy re-evaluation. A `StagedCatalog` is not a thread-safe immutable map or live authorization grant; administrators must explicitly and separately establish approved connection bindings. Regression tests cover malformed inputs, manifest conflicts, digest binding, disconnected defaults, and error paths.

## Remaining acceptance gates

Authenticated Identity, Policy, and approval adapters; signed or pinned manifest source verification; delegated connection/OAuth management; least-privilege credentials; resource-level permission enforcement; schema/protocol negotiation; sandboxed and network-restricted execution (including SSRF protections for HTTP/webhooks); atomic replay prevention; audit evidence; consent UI and accessibility; cancellation, rollback, data recovery; real tenant-isolation and adversarial tests; target-host end-to-end qualification; and explicit release authorization.

No service credentials, live external calls, provider account changes, deployment, or production tool access are introduced by this development increment.
