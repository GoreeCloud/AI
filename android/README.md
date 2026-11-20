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
    gradle :app:assembleDebug

Native chat supports local/cloud consent; images have separate paid-request
approval. Markdown documents, agent plans and manual MCP discovery/calls have
development UI screens. Browser-only or unfinished native parity includes
conversation save history, file import/export, image reference picking and
stream cancellation.

Debug emulator can use local http://10.0.2.2:8000; release is HTTPS only.
API provider credentials must stay on the server. No production user Identity,
privacy retention policy, signed release or physical device verification yet.
