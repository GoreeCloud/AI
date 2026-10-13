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

Integration point: import `GoreeCloudOpenUI` from `src/GoreeCloudOpenUI.tsx` into an authorized React client and pass the **normalized OpenUI Lang text** emitted by a GoreeCloud-controlled backend. A model prompt can be generated from `glazeOpenUIPrompt`; keep this prompt on a trusted server for production integrations. The current contract contains `GlzNotice`, `GlzMetric`, and `GlzText` only.

The provider backend must enforce Privacy Shield routing, identity, transport controls, quotas, data minimization, tool permissions, and Wardveil artifact scanning independently. The React renderer receives **no toolProvider, onAction callback, secrets, arbitrary HTML component, or direct provider credentials**. The UI-response boundary rejects known action syntax, but this filter is **defense in depth only, not a parser or security sandbox**. Validate final output using the OpenUI parser and schema; streaming partial output can be incomplete.

The example is scoped to new Development usage and does not modify an existing stable client. A live Ollama transport, streaming contract verification, actual screen/device tests, and end-to-end model responses remain unverified and are required before promotion.

## Attribution

OpenUI framework is MIT licensed, Copyright (c) 2011-2024 Thesys Inc. Its repository license and legal notice must accompany any distributed upstream code or substantial derivative. See [upstream license](https://github.com/thesysdev/openui/blob/main/LICENSE). GoreeCloud-owned glue code is under GoreeCloud AI's repository license.
