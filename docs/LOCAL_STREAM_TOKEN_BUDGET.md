# Optional local streaming token budgets (Development)

For one-shot local CLI inference, pass `--max-tokens N` (1–512) with either streaming (`--stream`) or nonstreaming chat. For example: `python3 scripts/ai_local.py chat --model llama3.2 --stream --max-tokens 64` with the prompt on stdin. The flag only sets Ollama `options.num_predict`; omitted flags preserve original request payloads. Invalid bounds are rejected before a network request. The in-memory REPL and existing private conversation settings remain unchanged.

The token budget is not a guarantee about total GPU/CPU time or processing cost. Existing local-only endpoint restrictions, stream completion semantics, timeouts, payload bounds, and privacy rules still apply. Synthetic offline CI does not verify a real installed Ollama model, production platform integration, or recovery readiness.
