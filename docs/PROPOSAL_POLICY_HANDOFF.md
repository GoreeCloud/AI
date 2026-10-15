# GoreeCloud AI — Model Proposal to Policy Handoff

**Development-only, non-executing reference.** This does not authenticate evidence, grant service access, or dispatch a connector action.

The `reference/proposal_policy_handoff.py` module checks a parsed model proposal against a trusted backend-supplied resource, a limited argument input contract, and a pinned service connection/manifest revision. Arguments are checked for exact permitted names and scalar types (bounded string, safe integer, boolean). Missing required keys, extra keys, wrong types, or changes to the original canonical argument digest are denied. The actual `authorize()` gate then checks Identity/Policy evidence, request scope, and write/sensitive approval receipts. The result is an internal planning receipt, not an execution permit.

The caller MUST obtain the resource entitlement, allowed argument rules, expected transport/connection/revision, identity, policy decision and approval from independent trusted authorities. They must not come from Ollama text, service descriptions, tool visibility, user-controlled UI state, or connector payloads. This reference cannot verify that evidence's origin.

## Missing production gates

Implement full operation-specific JSON Schema (the current scalar contract is deliberately restricted), trusted issuer attestation, time-of-use revalidation, transaction-safe connection pinning, Glaze review of actual target and data, atomic replay/idempotency protection, isolated connector execution and output sanitation, auditable denial and approval trails, and representative Ollama/provider end-to-end security testing. Do not expose this reference as a production authorization endpoint or mark GoreeCloud AI ready to execute real services.
