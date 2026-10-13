# GoreeCloud AI — OpenUI Lang / Glaze adapter (Development)

**Status:** Source-only Development integration. Not a released AI client, a deployed backend, or a production security claim.

This optional adapter uses the **MIT-licensed** [OpenUI Lang React runtime](https://github.com/thesysdev/openui) with a **GoreeCloud-owned, explicit Glaze component allowlist**. It does not require an OpenUI account, subscription, managed gateway, API key, or proprietary service. It does require a supported model to generate OpenUI Lang text; GoreeCloud's approved local Ollama-based model gateway remains a separate integration responsibility.

## Validate locally

```sh
cd integrations/openui
npm install --ignore-scripts --no-audit --no-fund
npm test
npm run typecheck
```

Integration point: import `GoreeCloudOpenUI` from `src/GoreeCloudOpenUI.tsx` into an authorized React client and pass the **normalized OpenUI Lang text** emitted by a GoreeCloud-controlled backend. A model prompt can be generated from `glazeOpenUIPrompt`; keep this prompt on a trusted server for production integrations. The current contract permits four native Glaze primitives: `GlzNotice`, `GlzMetric`, `GlzText`, and `GlzChoice`. The choice component supports accessible keyboard-controlled, local-only radio selection; no selection is saved or submitted.

The provider backend must enforce Privacy Shield routing, identity, transport controls, quotas, data minimization, tool permissions, and Wardveil artifact scanning independently. The React renderer receives **no toolProvider, onAction callback, secrets, arbitrary HTML component, or direct provider credentials**. The preliminary response boundary rejects oversized responses and recognizable action syntax. Completed responses are additionally parsed with the actual OpenUI Lang parser and validated against allowed component schemas; this Development implementation accepts **one complete root component only**. Both checks are defense in depth, not a tool-authorization system or security sandbox. Streaming partial output can be incomplete, so actual parser validation is deferred until generation finishes.

The example is scoped to new Development usage and does not modify an existing stable client. A live Ollama transport, streaming contract verification, actual screen/device tests, choice-state hydration, and end-to-end model responses remain unverified and are required before promotion. Reuse the separate approved GoreeCloud AI local-model gateway, rather than creating a second provider or relying on a paid OpenUI Gateway.

## Attribution

OpenUI framework is MIT licensed, Copyright (c) 2011-2024 Thesys Inc. Its repository license and legal notice must accompany any distributed upstream code or substantial derivative. See [upstream license](https://github.com/thesysdev/openui/blob/main/LICENSE). GoreeCloud-owned glue code is under GoreeCloud AI's repository license.

## OpenUI Lang examples

The framework uses a compact positional syntax. Supported examples include:

```text
root = GlzText("Local AI", "Running without the paid hosted gateway.")
```

```text
root = GlzChoice("Processing mode?", [{label: "Local", description: "Private inference"}, {label: "Offline", description: "No external access"}])
```

The earlier pseudo-syntax `GlzText({heading: ...})` is **not valid** for this parser. In this bounded Development version, only a single top-level `root` expression may be rendered; multi-component compositions remain future work and must be explicitly reviewed before being enabled. Test locally using `npm test` and `npm run typecheck`.
