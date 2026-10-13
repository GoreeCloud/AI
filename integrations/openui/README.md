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

The example is scoped to new Development usage and does not modify an existing stable client. A live Ollama transport, streaming contract verification, native-device and assistive-technology qualification, and end-to-end model-generated responses remain unverified and are required before promotion. The isolated React DOM and Chromium interaction tests below do not establish production or native acceptance. Reuse the separate approved GoreeCloud AI local-model gateway, rather than creating a second provider or relying on a paid OpenUI Gateway.

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

## Verified isolated browser evidence — October 13, 2026

At source revision `77fcaeb04f7f22773442c4e33e1140726e163941`, I validated the adapter in a clean, temporary Next.js **16.4.0** consumer using the public MIT OpenUI runtime and a headless Chromium session. TypeScript and optimized production build/static prerender passed. A `GlzChoice` radio control rendered and changed the displayed choice, a page reload reset the non-persisted choice, and both **390×844 mobile** and **1180×720 desktop** viewport configurations rendered two choices. The model-supplied unknown component was rejected by the completed-response schema and displayed one meaningful error message. The valid interface did not show the former false error notice. No page-level JavaScript exception occurred. Test marker: `OPENUI_CHROMIUM_INTERACTION_VERIFIED`.

The first browser attempt identified that `Renderer.onError([])` can be called with no errors; the wrapper incorrectly marked that as failure. The callback now treats only **nonempty** error arrays as errors, and the automated source test covers this regression. The Chromium test used **synthetic static OpenUI Lang**, not actual Ollama output, AI inference, connected credentials, protected data or a live tool action.

This is Developer-environment evidence, not an all-platform accessibility, security, privacy, performance or release-acceptance result. The temporary test consumer was cleaned up after execution. Package-install warnings and optional install scripts still require dependency review before a production consumer is selected.
