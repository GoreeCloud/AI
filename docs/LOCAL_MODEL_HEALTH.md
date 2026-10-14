# GoreeCloud AI — Local Readiness Probe (Development)

Run `python3 scripts/ai_health.py` against an **already-running** trusted local Ollama service. The probe uses only `GET /api/tags` over the same strict loopback-only gateway as the chat console; it **does not** send prompts, run inference, download models, persist data or fall back to an external provider.

```sh
python3 scripts/ai_health.py
python3 scripts/ai_health.py --model llama3.2
python3 scripts/ai_health.py --endpoint http://127.0.0.1:11434 --timeout 5
```

A zero exit status confirms that the local catalog is reachable and contains at least one installed model, optionally including the requested model. Nonzero exit status covers invalid input, an unavailable/invalid catalog, no installed models and missing requested models. Standard output intentionally reports counts/status rather than catalog details; errors contain no model-runtime payload or prompt content.

## Structured status

Use `--json` for machine-readable output. It emits a single JSON object to stdout on both successful and failed runtime checks, with `status` (`ready` or `not_ready`), stable `code`, integer `model_count`, and `inference_tested: false`. No model names, prompts, endpoints, or raw provider-error details are included. Exit status remains zero for readiness and nonzero otherwise. This is suitable for a caller-owned development preflight; it is **not** a deployed health endpoint or proof of model loading.

```sh
python3 scripts/ai_health.py --model llama3.2 --json
```

**Scope:** This is a lightweight **readiness preflight**, not a live inference test. A listed model can still fail to load, generate, fit in GPU/RAM, satisfy privacy policy or meet performance/accessibility/production acceptance. Runtime authorization and the trusted local tunnel remain operator responsibilities. Probe read-only behavior and failure paths are tested with synthetic loopback HTTP in `scripts/test_local_health.py`.
