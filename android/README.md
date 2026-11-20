# GoreeCloud AI native Android source

Native Kotlin + Jetpack Compose Material 3, built using the verified GoreeCloud UI
Android framework standard. Android Gradle Plugin 9.2.0, Kotlin Compose plugin
2.2.10, Compose 1.13.0 and Material3 1.5.0. API/provider keys are never
embedded in the APK; only an owner token is entered at runtime (memory only).

Open android/ as an Android Studio project with JDK 17 and Android SDK 37.1
or run from its root with installed compatible Gradle 9.4.1:

    gradle :app:assembleDebug

The Android emulator can access a local host-server at 10.0.2.2:8000, with
HTTP permitted in debug builds only. Release builds require HTTPS.
Do not distribute this preview or connect it to sensitive production accounts.

Current screens: hybrid model chat, image generation previews, Markdown
document editing, approved agent planning and MCP discovery/calls.
Native document list/PUT parity, import/export file pickers, reference-image
edits, and fully integrated GoreeCloud UI source adapter are not complete.
See ../docs/ROADMAP.md for acceptance and security work.

Material3 color roles are from the exact GoreeCloud/gc-ui provisional
dark Iris snapshot in ../design/gc.tokens.json. The existing reusable
gc-ui Android Material3 Expressive adapter has not been embedded yet.
Do not claim a device-qualified SDK or complete Expressive design compliance.
