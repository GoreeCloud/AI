# Official GoreeCloud UI Android Material 3 Expressive source snapshot

Upstream: https://github.com/GoreeCloud/gc-ui
Pinned Git commit: f501d92ba1f6698fa99427c564bf838954ce8bc1
MIT license: ../vendor/gc-ui/LICENSE and upstream root LICENSE.
Canonical tokens: ../../design/gc.tokens.json (byte-identical to upstream).
Source checksum registry: ../vendor/gc-ui/SOURCE-MANIFEST.json.

Source files copied from upstream android/material3-expressive/gc-ui-compose:
- build.gradle.kts and AndroidManifest.xml
- GeneratedGoreePalettes.kt
- GoreeCloudExpressiveTheme.kt
- GoreeFloatingNavigationBar.kt

This remains a first-party attributed source adapter, not an official Maven
publication or native-device certification. It is the **outer Android Material
3 Expressive theme host**. Shared Kotlin Compose components are sourced from
../vendor/gc-ui/compose-multiplatform, not a conflicting nested MaterialTheme.
