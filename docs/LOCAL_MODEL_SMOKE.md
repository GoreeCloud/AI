# GoreeCloud AI — Synthetic Local Inference Smoke Test (Development)

The separate catalog-only readiness probe is tracked in [Draft PR #58](https://github.com/GoreeCloud/AI/pull/58) and is not a dependency of this feature branch. This opt-in smoke check confirms that an **already-installed** local Ollama model can respond to one synthetic, fixed prompt. It does not establish model quality, accuracy, device/GPU readiness, authorization, Glaze accessibility, or production acceptance.

```sh
python3 scripts/ai_smoke.py --model llama3.2
python3 scripts/ai_smoke.py --model llama3.2 --timeout 120 --max-tokens 16 --json
python3 scripts/ai_smoke.py --model llama3.2 --strict-ready --json
```

The check first fetches the local installed-model catalog (`GET /api/tags`). It makes **one** `POST /api/chat` with a fixed synthetic prompt only when the requested model is installed. No user prompt, session transcript, secret or file contents are sent. Strict HTTP loopback validation, redirect refusal, sanitized failures and gateway size/deadline checks remain in force. There is no automatic retry, model installation, remote provider routing, credential use, tool execution or persistence.

The probe requests at most 16 output tokens by default, configurable with `--max-tokens N` (1-128). The gateway passes this as Ollama `options.num_predict`; existing ordinary chat calls are unchanged. Invalid budgets fail before any network request. This is a token-generation cap, not an overall GPU execution deadline.

`--strict-ready` additionally requires exactly `READY` after trimming surrounding whitespace (case-sensitive). A mismatch returns `unexpected_output` without displaying the model text. Without this option, a nonempty response counts as a smoke success; neither mode proves general model quality.

The model's generated text is never printed. Default terminal output gives a plain success/failure status. `--json` produces a redacted JSON result containing `status`, stable `code`, `inference_attempted`, `inference_verified`, and `processing: "local"`. Successful inference means only that a nonempty local assistant text response was received. It **does not require or claim** semantic compliance with the synthetic instruction.

The command may load a model and consume CPU, GPU, memory, energy or inference time. Run it only deliberately on a trusted approved local host with sufficient resources. No real AI Services VM inference was performed during offline test development.
