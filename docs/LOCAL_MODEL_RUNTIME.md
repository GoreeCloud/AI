# GoreeCloud AI — Local Model Runtime (Development)

This first-party Development adapter connects to a local Ollama runtime without making Ollama the product identity or a permanent application dependency. It adds real model discovery and single-turn or multi-message, non-streaming chat through a normalized ChatResult carrying provider, model, processing location and text.

## Usage

Ollama must already be installed and serving the selected local model on a trusted loopback socket. This adapter does not install models or configure runtime authentication.

    python3 scripts/ai_local.py models
    printf 'Explain photosynthesis in one paragraph.\n' | python3 scripts/ai_local.py chat --model llama3.2
    python3 scripts/test_local_model_gateway.py

An alternate local-only tunnel can be configured using --endpoint http://127.0.0.1:PORT. The tunnel must terminate on a trusted environment managed by the operator; this adapter cannot authenticate the other end. Plain HTTP is permitted only on literal loopback IP addresses. DNS names, remote IPs, HTTPS, credentials in URLs, URL paths/queries/fragments, redirects and proxy environment settings are refused. Do not expose the CLI as a remotely reachable endpoint.

Prompts are read from standard input rather than CLI arguments to avoid putting them in process argument lists. No prompt, model output, history, tokens, credentials, or conversation metadata are intentionally persisted or logged by the adapter. Shell history, terminal capture, pipes, runtime diagnostics and OS telemetry are outside these guarantees.

## Current capability and limits

- Models: retrieve, normalize and sort at most 200 locally installed Ollama model identifiers.
- Chat: up to 32 text-only messages, 16 KiB per message, 64 KiB serialized overall, and up to 1 MiB JSON response.
- Roles: system only in the first message; user and assistant allowed; final message must come from the user.
- Error behavior: bounded timeouts, sanitized errors, fail-closed invalid responses and prohibited redirects.
- Provider identity: a normalized result explicitly identifies Ollama and local processing.
- No external provider, automatic fallback, tool execution, streaming, attachments, retrieval, image input, persistence or UI integration is implemented.

The adapter confines outbound transport to a loopback address but does not enforce GoreeCloud Identity, Privacy Shield, Wardveil, Policy or sandbox authorization. Those remain responsibilities of the actual application and platform integration. Model output is untrusted and confers no permission for file operations or tool execution.

## Validation and acceptance

The deterministic regression suite uses a synthetic HTTP service bound to loopback, covering catalog, chat, malformed data, input limits, redirects, provider errors, offline behavior, and actual CLI subprocess calls. It does not establish live Ollama model inference, deployed authorization, mobile compatibility, Glaze interface accessibility, independent security review or production acceptance.

Further provider integration should follow [Model Provider Architecture](MODEL_PROVIDER_ARCHITECTURE.md), and any exposed application surface must retain provider-neutral contracts and explicit local/external processing disclosure.
