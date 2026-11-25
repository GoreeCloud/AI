# GoreeCloud AI Android — development source

Jetpack Compose Material 3 app with the **official GoreeCloud UI Material 3
Expressive source adapter** integrated as the in-repository gc-ui-compose module.

The Android Material 3 Expressive adapter and the shared Kotlin Compose
Multiplatform UI source are pinned to the reviewed official
[GoreeCloud UI commit](https://github.com/GoreeCloud/gc-ui/commit/f501d92ba1f6698fa99427c564bf838954ce8bc1)
(MIT). See [the Android adapter provenance](gc-ui-compose/UPSTREAM.md)
and [the shared snapshot checksums](vendor/gc-ui/SOURCE-MANIFEST.json).
The canonical `design/gc.tokens.json` is byte-identical to upstream and
the two Kotlin palette sources match. The Android host continues to supply
Material 3 Expressive; portable `GoreeCloudAction` is used in the confirmed
saved-conversation deletion dialog without changing deletion authorization.
These are local source modules, **not** published Maven libraries, a signed
APK, a deployed app, or proof of real-device acceptance.

Shared Android/Apple ARM64 source is maintained centrally in
`GoreeCloud/gc-ui` and consumed as a checked-in source snapshot. For
Android, the project also compiles the `:gc-ui-shared` module.
It does not authorize Compose as the primary Linux desktop GUI.

Before a source refresh or a release, verify checksums, provenance and
licenses, examine dependencies and build/manifest behavior, and rerun CI.

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

Native chat supports local/cloud consent, selectable full/4/8/16 message
history sent to the model, 256–2048 response-token caps, and deliberate
opt-in to local completed-answer/stream RAM reuse or OpenRouter response caching.
Unconfirmed or interrupted streams cannot populate the server replay cache.
These are server options; the app retains no cached model output on-device.
Opening or starting a new chat resets caching consent; cloud consent remains
separately required. The source and pure policy tests do not prove real
provider cache hits or on-device behavior. Images have separate paid-request
approval. The image studio can now deliberately list and select read-only
OpenRouter Image API model capabilities via the owner-authenticated API;
discovery does not itself authorize paid generation. Markdown documents,
agent plans and manual MCP discovery/calls have
development UI screens. Browser-only or unfinished native parity includes
conversation renaming, Markdown chat export, general document file import/export
and image reference picking.
The Chat screen now includes an explicit local-snapshot save control and a
saved-conversations view with refresh, bounded local FTS search, and opening
previously saved messages. Opening a snapshot or starting a new chat clears
cloud-processing consent. No local snapshot is uploaded automatically and
the owner token remains in memory only. These native history controls are
source-tested/build-checked, not qualified on a physical device.

An explicit Android system file picker now supports importing a user-selected
GoreeCloud AI v1 conversation JSON export into a new snapshot, or exporting
one chosen saved chat as JSON to a user-selected destination. Imports and
exports are bounded to 1.25 MB. The destination may sync to cloud storage;
the UI warns about plaintext, and only the user chooses the destination.
Saved-chat deletion uses a separate confirmation dialog and scoped HTTP
DELETE supporting an empty 204 response. Pure host-side transport-policy
tests guard route restrictions. No background sharing occurs.

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
