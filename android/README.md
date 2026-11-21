# GoreeCloud AI Android — development source

Jetpack Compose Material 3 app with the **official GoreeCloud UI Material 3
Expressive source adapter** integrated as the in-repository gc-ui-compose module.

The adapter is a source snapshot pinned at
https://github.com/GoreeCloud/gc-ui commit
5625121316230d78dd40a6e41a0671a250cb873b (MIT).
See gc-ui-compose/UPSTREAM.md for the attribution and source inventory.
Its brand palette is generated from design/gc.tokens.json at this same source
commit. This is not a published or production-certified gc-ui binary.

Run with JDK 17, Android SDK 37.1 and a supported Gradle toolchain:

    cd android
    gradle :app:testDebugUnitTest :app:assembleDebug

Native chat now supports bounded server SSE streaming and cancellation in addition
to ordinary complete responses; if local fallback is enabled, the UI uses the
existing non-streaming endpoint because the API does not support mid-stream
provider fallback. Streaming transmits the same approved chat body to the
configured owner API. Cancel disconnects the active HTTP request, stopping
local rendering and closing the server stream; it does not guarantee that an
upstream provider billed zero tokens before cancellation. Host-side JUnit
tests cover bounded SSE frames and cancellation state; physical-device
streaming, background lifecycle, accessibility and live-provider testing
remain unverified.

Native chat supports local/cloud consent; images have separate paid-request
approval. The image studio can now deliberately list and select read-only
OpenRouter Image API model capabilities via the owner-authenticated API;
discovery does not itself authorize paid generation. Markdown documents,
agent plans and manual MCP discovery/calls have
development UI screens. Browser-only or unfinished native parity includes
conversation save history, file import/export and image reference picking.

The debug source-set manifest now references a network security XML rule
allowing cleartext **only** to the Android emulator's `10.0.2.2` loopback
alias. Its base policy remains HTTPS-only, with no wildcard or custom trust
anchors; the main/release manifest retains `usesCleartextTraffic=false`
and `allowBackup=false`. BuildConfig.DEBUG also gates the Kotlin API's
emulator HTTP exception. This is a narrow development convenience, **not**
permission to use HTTP from a physical device, on a LAN or in production.

Python source tests verify the strict manifest/XML/client relationship;
the protected Android CI job compiles the debug app and checks the release
manifest processing task. Real Android emulator networking and release-device
acceptance are still unverified.

API provider credentials must stay on the server. No production user Identity,
privacy retention policy, signed release or physical device verification yet.
