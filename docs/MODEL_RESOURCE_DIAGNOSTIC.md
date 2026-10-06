# Operator-Initiated Local Model Resource Diagnostic

**Status:** Development-only opt-in. This diagnostic does not enable inference, execute tools, add an HTTP endpoint, change deployed configuration, measure GPU memory, establish authenticated policy provenance, or authorize production use.

This CLI composes the existing private local model-policy loader, loopback-only read-only model discovery, fail-closed model-role preflight, and pure development resource assessor. It adds a separate operator-provided private **model capability/resource profile**, samples free **system RAM** on the local host with Node's `os.freemem()`, and accepts operator-declared concurrency and safety reserve. It makes no claim that free system RAM represents available GPU VRAM, that model memory estimates are correct, or that operator-declared active requests reflect actual runtime scheduling.

## Operator setup

The private policy and model profile JSON files must both be absolute paths outside the repository, web root, Workspace, and upload tree. They must be owned by the process UID, mode `0600` or stricter, regular, single-link files with canonical nonsymlinked immediate parents. The policy schema appears in `docs/MODEL_ROUTING_PREFLIGHT.md`; the resource profile schema is defined and tested by `server/model-resource-readiness.mjs`. Do not store secrets in either file. The `source` field in the profile must be `operator-reviewed-development`, and freshness must be bounded; this text field is not evidence of authenticated administrator approval.

Run only on the local Development host with explicit opt-in:

```bash
VALIDATE_MODEL_RESOURCE=local-development-only \
VALIDATE_MODEL_POLICY_PATH=/absolute/private/model-policy.json \
VALIDATE_MODEL_PROFILE_PATH=/absolute/private/model-profile.json \
VALIDATE_MODEL_ROLE=coding \
npm run validate:model-resource
```

Optional configuration: `VALIDATE_MODEL_RUNTIME_URL` may be a literal HTTP loopback host (`127.0.0.1` or `[::1]`) with port; `VALIDATE_MODEL_PREFERRED` must be exactly installed and role-approved; `VALIDATE_RESOURCE_TIMEOUT_MS` is 1–30000 (default 5000); `VALIDATE_RESOURCE_INPUT_TOKENS` is 1–131072 (default 2048); `VALIDATE_RESOURCE_OUTPUT_TOKENS` is 1–65536 (default 1024); `VALIDATE_RESOURCE_SAFETY_RESERVE_MIB` is 0–1048576 (default 1024); `VALIDATE_RESOURCE_ACTIVE_REQUESTS` is 0–1024 (default 0); `VALIDATE_RESOURCE_MAX_PARALLEL` is 1–1024 (default 1). The command currently checks **text input only** and **no tool calling**. No CLI positional arguments are accepted.

On success it prints a short JSON `candidate` result with a selected model, role, Development profile revision and explicitly negative authority/validation fields: `profileTrust: development-unverified`, `capacityTrust: development-unverified`, `runtimeValidated: false`, `inferenceAuthorized: false`, and `toolExecutionAuthorized: false`. This is an *estimated local fit* to help plan **separate** target-host runtime testing, never permission to run the model. On failure it returns a nonzero status and a stable reason without private file contents, file paths, arbitrary upstream bodies or exception text.

The CLI only calls read-only Ollama `GET /api/tags` through the literal-loopback adapter. No chat, embedding, tool, remote runtime or model-loading call occurs. Its native subprocess tests use a temporary private policy/profile and an isolated loopback mock server, and test manual approval refusal, profile mismatch, budget exhaustion, malformed input, secret-output suppression, and non-loopback rejection.

Next required acceptance: security review of operator policy/profile provenance; verified model capabilities and target hardware measurements including GPU/VRAM where applicable; authenticated Identity, Privacy Shield and Policy execution decisions; actual first-party application-to-Ollama streamed inference tests; deployment and rollback evidence; nine Integral Platform System acceptance. Keep Draft PR #1 unmerged and the existing manual chat path unchanged until those conditions are separately accepted.
