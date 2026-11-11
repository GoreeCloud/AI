# GoreeCloud AI — Smart Model Profiles

**Implemented:** deterministic routing over model names returned by the local Ollama runtime. It does not benchmark models, detect installed hardware, download models, or prove response quality.

## Selection policies

- Smart Model and Smart Model · Balanced: prefer installed Qwen for coding and reasoning requests, Gemma for general chat; choose by stable name ordering within the task's family.
- Smart Model · Fast: prefer the variant with the smallest advertised parameter-count label among installed models in the preferred family.
- Smart Model · Quality preference: prefer the variant with the largest advertised parameter-count label within that family.
- Coding tasks prefer a Qwen model with coder in the name when installed. If the preferred family is absent, fall back only to another installed Qwen/Gemma variant.
- A manual model selection overrides Smart Model and may use any installed model.

**Important:** Smaller labels are not proven faster on a given CPU/GPU; larger labels are not proven more accurate or safe. Memory, quantization, architecture and workload affect actual performance. Missing size tags sort after known tags.

## Controls

Use the model chooser in the UI or set the chat model field to smart, smart:fast, smart:balanced or smart:quality. These policy strings work with the existing Chat and Smart Model route preview APIs. Route explanations are included with responses.

## Validation remaining

Benchmark each candidate with real Qwen/Gemma weights on authorized hardware. Evaluate response quality, latency, resource footprint, memory use, thermal constraints, and privacy-aware routing before claiming hardware-adaptive Smart Model features.
