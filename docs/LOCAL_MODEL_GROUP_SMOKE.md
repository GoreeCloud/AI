# Group-model smoke verification (Development)

The optional `scripts/ai_smoke_group.py` checks one to four explicitly named, already-installed local Ollama models using one fixed synthetic prompt. It performs one catalog check, requests a bounded generation of 1–128 tokens (16 by default), and stops on the first failure. No user prompt, local model identifier or generated output appears in JSON results. No retries, model downloads, file persistence, or remote fallback.

```sh
python3 scripts/ai_smoke_group.py --models llama3.2 qwen2.5 --strict-ready --json
```

`--strict-ready` requires the whitespace-trimmed response `READY` exactly. Without it, a complete nonempty local response counts as a smoke success. The command can load multiple models sequentially and consume CPU/GPU/memory. Use only on trusted approved local systems.

The tests use fake Ollama responses. A successful CI run does not establish live model inference, user-facing application integration, GoreeCloud Identity/Policy/Wardveil compliance, Glaze, device compatibility, or production readiness.
