# GoreeCloud AI — Local Capability Preflight

**Development-only, non-executing.** The local model can propose an action, but cannot authorize or execute one.

## Implemented sequence

Local Ollama response -> strict JSON proposal -> service/operation scope -> input and resource checks -> Identity/Policy/approval planning -> SQLite replay reservation -> redacted `reserved_no_execution` receipt.

`reference/local_preflight_pipeline.py` coordinates the existing pure development modules. It rejects denied/stale identity or Policy evidence before inference, validates the proposed resource, argument digest, contract and pinned connector, then reserves the request only after passing the Policy gate. No external connector is contacted and no effects are dispatched. The preview omits resource data, input arguments and connection IDs.

The offline suite covers read-only success, duplicate request rejection, denied policy before inference, write approval, changed arguments, target mismatch, and connector drift. One test exercises the actual local HTTP adapter against a synthetic Ollama server and an SQLite reference store. That is **not** evidence that Ollama is installed or a real provider is reachable.

## Remaining production gates

Authenticated issuer provenance for Identity, Policy and approval; independently reviewed resource/input contracts; Glaze consent; secure durable replay and idempotency; independent execution-time authorization; isolated connector transport and output handling; observability; target-host Ollama and service E2E; independent security review and protected rollout/rollback.

The reference may use in-memory SQLite only for synthetic tests. Its status `reserved_no_execution` is not a bearer permission, service success, or production acceptance.

## Early deny and replay optimization

Before invoking Ollama, the reference preflight checks the trusted Policy's
service, operation, requested resource, and service/operation grants against
the preview scope. It resolves the current backend connector transport and
manifest revision and rejects binding drift. For write/sensitive operations,
a fresh, request/session/resource/argument-bound approval must already be
present. If the tenant/request identity has been reserved, the reference
denies another generation call before sending the prompt to Ollama.

`ReplayLedger.was_reserved` is an **advisory, backend-internal read**; never
expose it to users or models as a request-existence oracle. A negative lookup
cannot prove the request is available because of concurrency. The later
atomic `ReplayLedger.reserve` operation is still required for every accepted
plan, even when the early lookup finds no row. A database error fails closed,
and neither check confers permission to execute any service.

The source remains development-only: a Python dataclass is not proof of
authenticated Identity, Policy or approval provenance. Production must
authenticate trust inputs and freshly reevaluate policy immediately before
any external side effect. These tests use synthetic models and SQLite, not
installed model inference or live connector execution.
