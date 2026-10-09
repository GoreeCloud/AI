# Model-Routing Backend Preflight — Development Foundation

**Status:** Development-only module and unit tests. This does not change the HTTP API, activate model routing, run inference, or establish platform acceptance.

`server/model-route-preflight.mjs` composes the existing deterministic role selector with two **backend-owned, injectable** adapters: `loadPolicy({ signal })` and `discoverModels({ signal })`. The preflight request accepts only `role`, an optional exact `preferredModel`, and an optional cancellation signal. A caller cannot supply or override the model approvals. Server-side approvals remain a prerequisite, and model discovery never by itself grants an approved role.

## Expected server policy snapshot

The preflight expects a snapshot with these exact properties:

```json
{
  "source": "server-local-config",
  "revision": "development-1",
  "observedAt": "2026-09-23T09:00:00Z",
  "expiresAt": "2026-09-23T10:00:00Z",
  "approvedModels": [
    { "name": "gemma3:12b", "family": "gemma", "roles": ["general", "reasoning", "writing"] },
    { "name": "qwen3-coder:latest", "family": "qwen", "roles": ["coding", "reasoning", "agent"] }
  ]
}
```

The dates above are an example only and are not usable as a current runtime policy. A future backend adapter must retrieve policy from an approved, authenticated administrator-controlled authority, not from a request body, workspace file, model response, or a public endpoint. The `source` string and policy revision are **structural metadata, not cryptographic proof of trust**. This module makes no production authorization claim.

## Safeguards in the development seam

- Reject unknown request fields, unsupported roles, malformed model identifiers, and invalid signal types before accessing the adapters.
- Reject policy snapshots with unknown envelope keys, missing local source declaration, malformed timestamps/revision, future observation, expired state, excessive validity window, or more than 128 approval records.
- Execute policy retrieval before discovery. If the policy is invalid or unavailable, no discovery is attempted.
- Bound policy retrieval and model discovery independently to a configurable maximum of 30 seconds, propagate cancellation, and fail closed if an adapter ignores abort.
- Reject invalid, overlarge (more than 512 entries), duplicate, or malformed discovered inventories; require exact name and role approval for a selected installed model.
- Return stable, non-secret error codes and mark all selection results `policyTrust: development-unverified` and `inferenceAuthorized: false`.

## Local validation

```bash
node --check server/model-route-preflight.mjs
node --test server/model-router.test.mjs server/model-route-preflight.test.mjs
```

The existing `npm run test:server` command automatically discovers this test file. A passing unit suite validates these source-level invariants; it does not prove live runtime interoperability.

## Explicitly deferred

This module is intentionally **not imported into** `server/index.mjs`. The existing manual `/api/ollama/chat` path remains unchanged. Before routing any live request, separately verify authenticated administrator-policy provenance, local runtime model capabilities and resource limits, backend request authorization, Privacy Shield and GoreeCloud Policy decisions, exact processing-zone controls, Wardveil boundaries where applicable, failure isolation, runtime behavior, rollback, and current platform-system conformance. Production privilege or knowledge-access gates must not be derived from this development preflight result.
