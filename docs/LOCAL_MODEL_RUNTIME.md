# GoreeCloud AI — Local Model Runtime (Development)

This first-party Development adapter connects to a local Ollama runtime without making Ollama the product identity or a permanent application dependency. It adds real model discovery and single-turn or multi-message, non-streaming chat through a normalized ChatResult carrying provider, model, processing location and text.

## Usage

Ollama must already be installed and serving the selected local model on a trusted loopback socket. This adapter does not install models or configure runtime authentication.

    python3 scripts/ai_local.py models
    printf 'Explain photosynthesis in one paragraph.\n' | python3 scripts/ai_local.py chat --model llama3.2
    python3 scripts/test_local_model_gateway.py

For **offline request-shape validation** without Ollama or a loaded model, use `printf '%s' 'Synthetic example' | python3 scripts/ai_local.py chat --model example:latest --validate-only`. This validates input and prints redacted JSON without network or inference; it does not prove the model is installed or runnable. See [Offline Request Validation](LOCAL_OFFLINE_REQUEST_VALIDATION.md). No dedicated AI Services VM is required.

An alternate local-only tunnel can be configured using --endpoint http://127.0.0.1:PORT. The tunnel must terminate on a trusted environment managed by the operator; this adapter cannot authenticate the other end. Plain HTTP is permitted only on literal loopback IP addresses. DNS names, remote IPs, HTTPS, credentials in URLs, URL paths/queries/fragments, redirects and proxy environment settings are refused. Do not expose the CLI as a remotely reachable endpoint.

Prompts are read from standard input rather than CLI arguments to avoid putting them in process argument lists. No prompt, model output, history, tokens, credentials, or conversation metadata are intentionally persisted or logged by the adapter. Shell history, terminal capture, pipes, runtime diagnostics and OS telemetry are outside these guarantees.

## Streaming local responses (Development)

Streamed output is opt-in and **never falls back to an external model**:

    printf 'Summarize photosynthesis.\n' | python3 scripts/ai_local.py chat --model llama3.2 --stream

Application clients can call LocalOllamaGateway.iter_chat(model, messages) with contextlib.closing, consuming ChatStreamEvent values. Every text event identifies local processing and carries one token/text delta with done=False; only a final event with done=True confirms that a complete answer was received. An interrupted, malformed, timed-out or truncated stream **must not** be saved or presented as a completed assistant answer. A partial CLI answer is accompanied by a failure status and a clear stderr warning.

The terminal CLI prints untrusted model text with control and bidirectional-format characters rendered as visible escapes. Newlines and tabs remain readable; this display sanitization does not authorize model output as instructions.

Calling close() on an active iterator closes the underlying local HTTP response; this is local request cancellation, **not evidence that the Ollama server stopped its underlying GPU job**. There is no automatic retry, alternate-provider routing, or tool execution after an interruption.

Only the exact literal endpoints `127.0.0.1` and `[::1]` are accepted; other 127/8 addresses are rejected to avoid unexpected local-service routing.

Non-streaming model discovery and chat also enforce a 15-minute total elapsed response deadline, including incomplete slow-trickle JSON bodies. The socket timeout still bounds individual blocked reads and the 1 MiB total JSON response limit remains. Deadline failures are sanitized and do not commit conversation history.

Each incoming JSON frame is limited to 64 KiB, streams to 4096 frames or 2 MiB wire data, and combined text output to 1 MiB UTF-8. A stream also has a 15-minute total elapsed-time guard against slow-trickle responses, checked even within individual NDJSON frames (with one final socket-byte-read timeout overrun possible); exceeding it fails closed without a completed answer. Unsupported tool/image output, unexpected model identity, malformed JSON, invalid completion flags, missing final completion, HTTP redirects, and service failures fail closed. Consumers should observe an explicit completed event before committing conversation state. This is an isolated Developer API and CLI feature, not a connected Glaze streaming interface.

## Private multi-turn chat (Development)

Run interactive local chat using an already-installed local model:

    python3 scripts/ai_local.py repl --model llama3.2

The repl streams by default; add --no-stream to display only completed answers. /help shows the supported controls and // at the start sends a literal slash-prefixed message. Unknown commands are not forwarded as prompts. /status displays only a count and configuration, never conversation content. EOF or /exit ends the process; all remembered turn references are cleared on exit.

The LocalChatSession reference API retains only successfully completed user/assistant pairs **in process memory**. Incomplete, failed, interrupted or malformed responses are not added. Before each generation, it drops the oldest *complete* pairs to fit the 32-message and 64 KiB request bounds. Model output larger than 16 KiB, empty output or output containing NUL cannot be kept as a valid future conversation message: that response is shown but the context is reset, with a clear warning, rather than silently claiming continuity. reset() immediately discards the retained transcript references. It cannot erase copies held by terminal scrollback, the local runtime, operating-system swap/core dumps, shell capture, monitoring, or other tools.

This session is designed for **one sequential local console user**, not concurrent clients, accounts or trusted persistent history. No session database, file, network synchronization, external model fallback or plugin/tool execution is implemented. Chat content is sent to the selected local Ollama runtime, not persisted by this adapter. The caller is responsible for authenticating any future service/UI integration and verifying the runtime's retention policy.

## Session controls (Development)

The interactive local console also includes explicit privacy-aware controls:

- `/models` lists installed local model names. `/model NAME` switches only to a verified installed model and clears prior turns and system instruction to avoid cross-model context leaks. Invalid, absent or unavailable models do not change session state.
- `/system TEXT` installs an in-memory system instruction first in the local request, clearing the previous conversation. `/system off` clears instruction and conversation; `/system` reports only enabled/disabled status, not the instruction itself.
- `/undo` discards the latest *completed* user/assistant pair in process memory, without another request. It cannot revoke previous inference, output in terminal scrollback or copies held by a runtime.
- `/rewind N` keeps only the first N completed pairs (N may be 0); later turns are forgotten from process memory without inference. Use `/turns` for redacted turn numbers before choosing N.
- `/forget N` discards the oldest N completed pairs without contacting the model, retaining the newer turns. Invalid, negative and out-of-range counts leave the conversation unchanged.
- `/again` **explicitly** requests another response to the most recent retained user prompt, with its previous assistant answer excluded from the request. Both streamed and non-streamed modes commit a replacement only after valid completion. A failed, canceled, empty, invalid or unretainably large replacement leaves the previous completed pair intact. It is unavailable in stateless mode or without a retained turn. This is a user-triggered extra inference call, never an automatic retry.
- `/once TEXT` sends just this one prompt plus the current ephemeral system instruction to the selected local model, never the retained conversation pairs. Completed replies are displayed but not added to the in-process transcript. This also works in streamed mode; unfinished or canceled streams cannot commit a turn. Existing retained turns, the retention setting and system instruction remain unchanged. The response still appears in terminal output, and the local model runtime receives the new prompt; neither can be erased by this command. No automatic retry or external model routing is involved.
- `/edit TEXT` revises the most recent retained user question and requests a new local answer without including its superseded question or reply in the request. Both streaming and non-streaming replacements are committed only on valid completion; malformed input, failed inference, interruption or unretainable output preserve the former completed pair. This is an explicit new inference call and does not undo earlier runtime processing.
- `/status` shows retained-turn count, active model and instruction state without printing confidential prompt or instruction content.

These features still obey existing 32-message and 64 KiB payload limits, do not save a session or invoke tools, and do not make external-provider requests. They do not establish a multi-user service, authenticated application UI, permanent deletion at the model runtime or production readiness.

## Current capability and limits

- Models: retrieve, normalize and sort at most 200 locally installed Ollama model identifiers.
- Chat: up to 32 text-only messages, 16 KiB per message, 64 KiB serialized overall, and up to 1 MiB JSON response.
- Roles: system only in the first message; user and assistant allowed; final message must come from the user.
- Error behavior: bounded timeouts, sanitized errors, fail-closed invalid responses and prohibited redirects.
- Provider identity: a normalized result explicitly identifies Ollama and local processing.
- No external provider, automatic fallback, tool execution, attachments, retrieval, image input, persistence or UI integration is implemented.

The adapter confines outbound transport to a loopback address but does not enforce GoreeCloud Identity, Privacy Shield, Wardveil, Policy or sandbox authorization. Those remain responsibilities of the actual application and platform integration. Model output is untrusted and confers no permission for file operations or tool execution.

## Validation and acceptance

The private-session suite additionally validates multi-turn context, complete-pair eviction, reset, explicit stream completion, failed-response rollback, terminal REPL commands, and malformed Unicode handling. The deterministic regression suite uses a synthetic HTTP service bound to loopback, covering catalog, chat, malformed data, input limits, redirects, provider errors, offline behavior, and actual CLI subprocess calls. The separate streaming suite tests token deltas, completion, partial failures, interruption/iterator closing, CLI behavior, frame/answer bounds, and prohibited tool output. It does not establish live Ollama model inference, deployed authorization, mobile compatibility, Glaze interface accessibility, independent security review or production acceptance.

Further provider integration should follow [Model Provider Architecture](MODEL_PROVIDER_ARCHITECTURE.md), and any exposed application surface must retain provider-neutral contracts and explicit local/external processing disclosure.
