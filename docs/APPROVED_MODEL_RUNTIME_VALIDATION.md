# Approved Local Model Runtime Validation

**Status:** Development-only, operator initiated. This validation executes exactly one streamed local model request through the existing GoreeCloud AI backend. It does not change the backend, load a model, enable a route, create product authorization, establish authenticated administrator provenance, or qualify the application for production or Stable.

## Purpose

`npm run validate:approved-model-runtime` closes part of the gap between source-only model selection checks and representative target-host runtime evidence. It binds an exact requested model and GoreeCloud functional role to the existing protected Development policy, discovers installed models through the first-party GoreeCloud AI backend, and then exercises one streamed request through the existing `/api/ollama/chat` application path.

The validator is evidence collection for a Development environment. It is not a production authorization mechanism and is not imported by `server/index.mjs`.

## Safety boundary

The command requires all of the following before any request is made:

- Explicit opt-in: `VALIDATE_APPROVED_MODEL_RUNTIME=local-development-only`.
- An absolute protected local policy path in `VALIDATE_MODEL_POLICY_PATH`.
- A supported functional role in `VALIDATE_MODEL_ROLE`.
- An exact requested installed model in `VALIDATE_MODEL_PREFERRED`.
- A literal loopback GoreeCloud AI URL. DNS names, private-network addresses, public addresses, credentials in URLs, redirects, paths, query strings, and fragments are rejected.

The policy file is read through the same restrictive local loader used by the other Development model-routing diagnostics. The selected model must be both present in application-backed discovery and explicitly approved for the requested role. A manual preference cannot bypass those conditions.

The command uses a fixed non-sensitive validation prompt. It never prints generated model text, the configured bearer token, the policy path, policy file contents, application URLs, arbitrary upstream bodies, or exception details. JSON and streamed responses have bounded sizes and timeouts. Invalid, malformed, oversized, incomplete, or error-bearing streams fail closed.

## Run on the intended Development host

```bash
VALIDATE_APPROVED_MODEL_RUNTIME=local-development-only \
VALIDATE_MODEL_POLICY_PATH=/absolute/private/model-policy.json \
VALIDATE_MODEL_ROLE=coding \
VALIDATE_MODEL_PREFERRED=qwen3-coder:latest \
GOREECLOUD_AI_URL=http://127.0.0.1:8787 \
npm run validate:approved-model-runtime
```

If the Development API requires its bearer token, supply `GOREECLOUD_AI_API_TOKEN` through protected runtime configuration. Do not place reusable credentials in source control, shell history intended for sharing, screenshots, or retained validation output.

`VALIDATE_APPROVED_MODEL_RUNTIME_TIMEOUT_MS` may be set from 1 through 120000 milliseconds; the default is 30000 milliseconds. The policy/discovery preflight remains capped at 30000 milliseconds.

## Evidence output

A successful run emits one sanitized JSON object. It identifies the exact role/model, policy revision, model family and selection mode, application service identity, Wardveil scanner configuration state, bounded stream counters, and elapsed time. It also states:

- `runtimeValidated: true`
- `validationScope: one-approved-streamed-request-only`
- `executionAuthority: operator-initiated-development-validation-only`
- `productionInferenceAuthorized: false`
- `productionAccepted: false`
- `stableQualified: false`

`runtimeValidated: true` means only that the one exact operator-initiated Development request passed the validation conditions. It does not prove sustained throughput, GPU/VRAM capacity, model quality, all supported roles, authenticated GoreeCloud Identity/application authorization, Privacy Shield or GoreeCloud Policy enforcement, Wardveil production transport, Everkeep recovery, Mesh, Observability, Glaze UI conformance, deployment, or Stable acceptance.

## Tests

`server/approved-model-runtime-diagnostic.test.mjs` uses an isolated literal-loopback mock application and a temporary mode-0600 policy file. It verifies explicit opt-in, local-only destination enforcement, exact role/model approval, successful health/discovery/chat sequencing, bearer handling without leakage, no generated-content leakage, refusal before chat for an unapproved model, malformed private-policy handling, and fail-closed incomplete or error-bearing streams.

The normal repository `npm run test:server` suite includes these tests. No CI job performs real model inference; real target-host evidence remains an operator-run validation step.

## Remaining acceptance

This validator is one Development evidence source only. Representative hardware characterization, real GPU/VRAM and concurrency measurements, authenticated administrative policy provenance, Identity-backed application authorization, Privacy Shield and GoreeCloud Policy decisions, Wardveil acceptance, nine-system platform acceptance, recovery, rollback, release, deployment, and Stable qualification remain separate gates.
