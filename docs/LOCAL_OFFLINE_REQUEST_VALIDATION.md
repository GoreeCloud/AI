# Offline one-shot local request validation (Development)

When a local model runtime is unavailable or an existing host has insufficient free memory, verify the **request shape** without starting Ollama or using a model. No dedicated AI VM is required.

```sh
printf '%s' 'A synthetic test prompt' | python3 scripts/ai_local.py chat --model example:latest --validate-only
printf '%s' 'A synthetic test prompt' | python3 scripts/ai_local.py chat --model example:latest --stream --max-tokens 32 --validate-only
```

The `--validate-only` flag is available only for one-shot `chat`, not `models` or the private `repl`. It validates the explicit literal loopback endpoint, timeout, model identifier, bounded stdin UTF-8 prompt and supported nonempty message shape, as well as any optional `--max-tokens` argument. It returns redacted JSON:

```json
{"inference_attempted": false, "model_installed_verified": false, "network_attempted": false, "processing": "local", "status": "valid"}
```

The input prompt, model identifier and model-generated text are never echoed. No HTTP connection, model catalog lookup, inference, model download, file persistence or remote fallback occurs. Validation does **not** claim that Ollama is installed, that the selected model is present, that generation can finish, or that production authorization/security integrations are ready.

For a later real local runtime check, use the separate explicit synthetic smoke tools on an authorized host with adequate resources. Do not install a large model or start expensive inference merely to test request formatting. Offline regression tests cover validation success and adverse paths, including malformed UTF-8, bad model names, invalid endpoint, empty/oversized prompts, and out-of-range generation limits.
