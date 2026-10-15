# Private chat output budgets and context preview (Development)

This is an **opt-in, local-only, in-process** console capability. No dedicated VM or external provider is required. An installed Ollama runtime and an approved local model are needed for real inference, but **not** for previewing a request.

## REPL commands

```sh
python3 scripts/ai_local.py repl --model example:latest --max-tokens 64
```

- `/budget` reports the current requested output-token limit without contacting the model.
- `/budget N` applies a session-only budget from **1 through 512** tokens for later streaming or nonstreaming replies, including explicit edits, regeneration, and one-time responses.
- `/budget auto` removes the explicit cap, restoring the runtime's default. Omitted budgets preserve preexisting request payloads.
- `/preview TEXT` checks what an ordinary next response **would include**: request bytes, message count, completed turns included, old turns omitted to respect bounded context, and whether a system instruction is present. It does **not** print the prompt, instructions, prior messages, or generated text. No network call, model installation or inference occurs.
- `/status` includes the current generation budget alongside retained-turn counts.

Preview does not mutate conversation history, drop completed turns, change a model, or commit any messages. A later actual request may see different context if the session changes after preview. `/preview` models the next ordinary reply, not the special `/once`, `/edit` or `/again` behavior.

The model's `num_predict` option is only an **output-token request**, not a total CPU/GPU, elapsed-time, or monetary-cost cap. Existing loopback-only transport, request/response byte bounds, timeout behavior, failure rollback and untrusted-model-text restrictions are preserved. Session budget settings are kept only in process memory. `/reset` clears chat context, not the generation budget. Real model availability, Glaze/UI behavior, Identity/Policy/Wardveil integration and production acceptance remain separate release gates.
