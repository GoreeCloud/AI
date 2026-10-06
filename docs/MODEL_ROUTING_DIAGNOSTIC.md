# Operator-Initiated Local Model-Routing Diagnostic

**Status:** Development only. The command is deliberately disconnected from live chat, user-facing HTTP routes, model inference, and platform authorization.

The opt-in `npm run validate:model-routing` command composes the private local model-policy reader, loopback-only runtime discovery, and bounded preflight introduced earlier. It checks whether the selected functional role has an explicitly approved, currently installed local model. It never sends chat messages, invokes embeddings, executes tools, loads a model, or grants execution authority.

## Operator setup

Create an approved **private local Development policy file** outside the source tree, Workspace, uploaded-file tree, and web root. The file must be owned by the application process UID, be a single-link regular file, have mode 0600 or stricter, and reside behind a canonical (non-symlinked) parent directory. It must contain the exact preflight policy envelope documented in `docs/MODEL_ROUTING_PREFLIGHT.md` with an appropriate fresh observation and expiry. Do not include credentials. There is no bundled, auto-enabled approval policy.

On the same local host as the model runtime, an authorized developer may explicitly invoke:

```bash
VALIDATE_MODEL_ROUTING=local-development-only \
VALIDATE_MODEL_POLICY_PATH=/absolute/protected/path/model-policy.json \
VALIDATE_MODEL_ROLE=coding \
npm run validate:model-routing
```

Optionally set `VALIDATE_MODEL_PREFERRED` to one exact approved model, `VALIDATE_MODEL_RUNTIME_URL` to a literal loopback URL (default `http://127.0.0.1:11434`), and `VALIDATE_MODEL_TIMEOUT_MS` to an integer from 1 through 30000 (default 5000). The command takes no CLI positional arguments, refuses to operate without the exact opt-in marker, and returns a short JSON result and nonzero exit code on unavailability. It never prints the configured file path, policy bytes, upstream body, or raw exception message.

A successful result contains the chosen model identity, policy revision, `policyTrust: development-unverified`, `processingZone: local-only-intended`, and **`inferenceAuthorized: false`**. It only demonstrates local discovery and selection under the supplied **Development** policy. It does not prove administrator authenticity, model generation/streaming, accepted policy enforcement, platform-system integration, runtime deployment, or production readiness.

## Source and tests

- CLI: `scripts/validate-model-routing.mjs`.
- Existing adapters: `server/model-local-adapters.mjs`.
- Existing preflight: `server/model-route-preflight.mjs`.
- CLI integration tests: `server/model-route-diagnostic.test.mjs`, included by `npm run test:server`.

Tests launch the real CLI subprocess against a private temporary policy file and a loopback test server. They validate exact role selection, denial of mismatched manual models, mandatory operator opt-in, malformed policy, unsafe timeout, rejection of remote runtime destinations, no secret output, and discovery-only `GET /api/tags` traffic.

## Pending governance gates

Keep the existing manual chat endpoint unchanged. Before any live model routing or production claim, obtain authenticated administrator-policy provenance, application-owned access controls, relevant Identity/Privacy Shield/Policy/Wardveil authorization and evidence, model capability/resource checks, actual target-host model discovery and streamed-generation evidence, current Stable Glaze UI consumer acceptance, and applicable platform-system review. The CLI does not bypass any of those blockers.
