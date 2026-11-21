# AI product acceptance gates

| Gate | Required evidence | Preview status |
|---|---|---|
| API | Regression, compatibility, explicit contracts | Python CI/mock tests include bounded provider image responses and capability discovery; live-provider contract acceptance pending |
| Web | Build, browsers, accessibility | TypeScript build covers image catalog selector; browser and accessibility verification pending |
| Linux | Qt startup, real desktop, packaging | Qt source includes image model discovery plus SSE stream/cancel and bounded parser; offscreen QML smoke and synthetic loopback/redirect/cancel tests passed, but interactive desktop, accessibility and signed package pending |
| Android | Material3 Expressive build, emulator/device, signing | Compose image discovery and streaming/cancel source; debug build and native SSE JUnit parser CI, but emulator/physical-device, screen reader and signed distribution pending |
| GoreeShield | Privacy consent records, retention/encryption | Consent receipts, opt-in dry-run/apply local retention CLI and uninstalled systemd timer template, optional SQLCipher/FTS and encrypted backup tests; actual scheduler, activation, key custody, policy and erasure acceptance pending |
| Wardveil | Threat assessment, sandbox, scans | Source-tested PDF/DOCX magic-byte and UTF-8 text preflight before parser spawn, opt-in Bubblewrap isolation, bounded/approved MCP boundaries; no malware scan, seccomp, isolated MCP worker, host resource acceptance or independent review |
| Identity | OIDC/OAuth source contract and scopes | Offline pinned-JWKS RS256 adapter and optional route capability matrix tested; no verified GoreeCloud Identity issuer, delegated multiuser scopes or deployment |
| Mesh | Authenticated service integration | Authenticated read-only capability manifest; not a registered Mesh adapter |
| Billing | Hard USD limit and actual provider reconciliation | Count guard + optional credit-cap preflight and synthetic-tested manual metadata-only OpenRouter generation-cost lookup; no actual provider/billing acceptance, USD reservation or invoice reconciliation |
| Recovery | Encrypted backup and restore exercise | AES-GCM offline backup/restore for plaintext or SQLCipher source, source-preserving migration and source-preserving SQLCipher key rotation synthetic-tested; off-host key custody/restore and rollback acceptance open |
| Dependencies | Locks, SBOM and redistribution notices | SHA-pinned actions, locked Python/web scans, Python/npm source-lock inventories plus Android directly declared Maven/plugin IDs and selected installed PySide6 wheels in CI; resolved Android graph, Qt/OS native libraries, licenses, provenance and complete SBOM open |
| Deployment | TLS, auth, monitoring, rollback | None verified |

No Stable or production release without all applicable approvals.
