# GoreeCloud AI Knowledge Authorization Boundary

GoreeCloud AI treats attachment security release, safe extraction, authenticated identity, application authorization, Privacy Shield data-use authorization, indexing, retrieval, and model-context execution as separate gates.

## Current source slice

The current development API exposes:

- `GET /api/files/:id/knowledge-eligibility` — read-only current gate observation with no supplied authorization input.
- `POST /api/files/:id/knowledge-authorization-assessment` — bounded assessment of explicitly supplied Identity/application-authorization and Privacy Shield decision inputs against the current attachment and extraction state.

Neither endpoint creates persistent authorization, chunks, embeddings, indexes, retrieval state, model context, research work, or external transfers.

## GoreeCloud Identity boundary

Current GoreeCloud Identity architecture establishes authenticated identity and approved identity claims, while each participating application remains responsible for its own authorization and data-access decisions.

Accordingly, this source slice does **not** invent GoreeCloud-wide Identity permission scopes. The following identifiers are GoreeCloud AI application-local operation names:

- `goreecloud-ai.knowledge.index`
- `goreecloud-ai.knowledge.retrieve`
- `goreecloud-ai.knowledge.model-context`

An assessment input includes an authenticated actor observation plus GoreeCloud AI application authorization bound to the attachment resource ID and one of those operations. Temporal ordering, expiration, resource binding, and operation permission are checked fail-closed.

This is still not production Identity integration. The current application has no authenticated GoreeCloud Identity adapter that establishes the supplied input at runtime.

## Privacy Shield boundary

The assessment consumes fields aligned to the current `privacy-shield.decision.schema.json` request/response contract, including requester, resource, operation, purpose, processing zone, destination, retention, decision outcome, permitted operations/destinations, obligations, and expiration where present. If request `retention.expires_at` is present and non-null, it must be a valid date-time; malformed values fail closed.

The current Privacy Shield request contract is closed at the request, requester, and request-retention object boundaries, and the response contract is closed at the decision object boundary. The assessor therefore rejects unknown properties at those same boundaries rather than silently accepting schema drift. Known optional fields such as `external_disclosure`, `context`, `delegation_chain`, consent/manifest/Wardveil references, `consent_required`, policy references, and capability/evidence references are type-checked when supplied. The resource object remains extensible as allowed by the authoritative schema, and decision retention remains an object because the current response schema does not further constrain its internal properties.

Current Privacy Shield outcomes are preserved:

- `DENY` — blocked;
- `REQUIRE_USER_DECISION` — pending, never treated as approval;
- `ALLOW` — structurally satisfied only when all checked bindings/constraints agree;
- `ALLOW_WITH_CONSTRAINTS` — structurally satisfied only when bindings agree, with obligations preserved in the assessment.

The request resource must match the GoreeCloud AI attachment resource ID. The request operation must match the application-local operation being assessed. The Privacy Shield decision must bind to the same request ID and permit the operation, processing zone, and destination. Expired decisions fail closed.

Requester/actor binding is also fail-closed. An application requester acting for a user must carry that exact user as `acting_user`. An application actor can bind only to the same application requester. Services/agents cannot be silently wrapped as an application requester without an explicit supported binding.

These operation names are not additions to the canonical Privacy Shield capability registry. Privacy Shield authorization travels with the operation; registry capability adoption remains a separate centrally governed contract.

## Deliberately non-authorizing source trust

Even when the supplied Identity/application and Privacy Shield inputs are structurally satisfied, the assessment returns:

- `sourceTrust.productionTrustedInput: false`;
- `persistentAuthorizationCreated: false`;
- `executionAuthorized: false`.

Reason: authenticated Identity and Privacy Shield runtime adapters, capability/signature verification, durable decision/evidence handling, and production acceptance are not connected here. A client-supplied JSON object cannot manufacture production authority.

## Knowledge eligibility result

A structurally satisfied authorization assessment can move the *displayed assessment state* to `pending_stage_implementation`, but it still keeps:

- `eligibleForIndexing: false`;
- `eligibleForRetrieval: false`;
- `eligibleForModelContext: false`.

Privacy Shield `REQUIRE_USER_DECISION` maps to `pending_privacy_user_decision`. Identity or Privacy failures remain blocked. Wardveil and extraction gates retain precedence.

## Required future work before execution

Before any knowledge operation can become executable, GoreeCloud AI still requires at minimum:

1. authenticated GoreeCloud Identity session/service integration and application-owned resource/Workspace authorization;
2. authenticated Privacy Shield enforcement/decision integration with operation-bound capability/evidence verification;
3. production Wardveil Scan transport and accepted attachment trust evidence;
4. safe provenance/chunking/embedding/indexing implementation;
5. Workspace/owner permission filtering for retrieval;
6. model-context execution controls and Privacy Shield destination/retention enforcement;
7. durable authorization/evidence/revocation behavior appropriate to the operation;
8. Everkeep lifecycle/recovery treatment for derived knowledge state;
9. GoreeCloud Mesh integration where required without manufacturing authority; and
10. current Glaze UI and broader product-specific runtime/deployment acceptance.

No source-level authorization assessment is a Stable or production-ready claim.
