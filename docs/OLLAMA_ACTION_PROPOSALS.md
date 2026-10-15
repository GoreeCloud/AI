# GoreeCloud AI — Ollama Action Proposal Contract

**Development-only, non-executing.** The local Ollama runtime may suggest a JSON action, but is never an authorization or execution authority.

## Implemented flow

1. An operator-provisioned, connected capability catalog and trusted-scoped service and operation grants determine which operations are shown to the model. The inference prompt lists at most 48 service/operation identifiers with backend-declared risk, never connection IDs, credentials, endpoint URLs or actual grants.
2. `reference/local_action_planner.py` uses the existing loopback-only `LocalOllamaGateway.chat` for one bounded response. Tool calls are already rejected at the Ollama adapter boundary.
3. `reference/model_action_proposal.py` accepts **only one bare JSON object** with exactly `schema`, `service`, `operation`, `resource` and `arguments`. The schema must equal `goreecloud.ai.action-proposal.v1`. Markdown fences, commentary, duplicate JSON keys, unknown properties (such as an `approved` claim), NaN, oversized responses, malformed targets, or unsupported argument types fail closed.
4. An independent backend request identifier is attached to the typed `CapabilityIntent`. The actual arguments are canonicalized and hashed by the backend; model text cannot supply the request ID, digest, policy outcome, credentials, tenant or approval. The proposed operation must resolve against the live development registry **and** be one that was explicitly exposed in the model prompt.
5. A redacted preview shows service, operation, minimum risk, argument count and digest, labeled `proposed_not_authorized`. It deliberately omits raw arguments, resource contents and connector binding IDs. This is **not yet a sufficient permission-consent UI**, since users will need to review exact target and data disclosures in a trusted Glaze approval flow.

The new modules do not call `authorize`, reserve or execute an effect, connect services, store user prompts, create OAuth grants or expose Ollama's own tool-calling protocol. Synthetic tests exercise malformed JSON and model-forged authority. Real target-host Ollama inference remains unverified until an installed runtime and suitable model are available.

## Remaining implementation work

Versioned operation-specific JSON Schema validation; a trusted proposal-to-validated-arguments boundary; independent Identity, Policy, Privacy Shield, Wardveil and resource authorization; Glaze target/payload consent and accessibility; cancellation and error UX; durable, auditable approval and idempotency; connector execution sandbox with network egress controls; results sanitization; representative installed-model and service end-to-end tests; security review and release approval.

**Non-execution invariant:** A model-generated string, model tool call, or displayed capability never conveys permission to execute an external action.

## Optional local CLI demonstration

After an operator independently reviews and pins a service manifest and installs a local Ollama model, the preview-only command is:

```sh
printf 'List two items' | python3 scripts/ai_propose_local.py \
  --manifest /path/to/reviewed.json \
  --sha256 YOUR_INDEPENDENTLY_VERIFIED_PIN \
  --model YOUR_INSTALLED_LOCAL_MODEL \
  --transport mcp --permit items.read
```

All `--permit` options are **simulation-only preview scope**, not authenticated user grants. The CLI uses a synthetic `preview-only` connector binding, never real service credentials. It only calls local Ollama on an HTTP loopback address through the existing local-only gateway; the named external service is not contacted. It prints a redacted JSON status of `proposed_not_authorized` and `execution: disabled`, or a sanitized error. This is not an interactive approval experience and must not be exposed as a public or multi-tenant authorization endpoint. Prompts are read from standard input; terminal capture, pipes and Ollama's own process are outside the CLI's privacy guarantees.

The test suite exercises the CLI against a **synthetic loopback HTTP server** and does not prove actual installed model inference, domain authorization, or real connector access.
