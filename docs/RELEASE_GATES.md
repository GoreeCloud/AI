# AI product acceptance gates

| Gate | Required evidence | Preview status |
|---|---|---|
| API | Regression, compatibility, explicit contracts | Python CI/mock tests include bounded provider image responses and capability discovery; live-provider contract acceptance pending |
| Web | Build, browsers, accessibility | TypeScript build covers image catalog selector; browser and accessibility verification pending |
| Linux | Qt startup, real desktop, packaging | Qt source includes image model discovery; headless smoke/real desktop acceptance pending |
| Android | Material3 Expressive build, emulator/device, signing | Image model discovery uses native Compose; debug build/device acceptance pending |
| GoreeShield | Privacy consent records, retention/encryption | Explicit cloud approvals, metadata-only admission receipts/owner clear, snapshot retention purge; policy integration and live DB encryption pending |
| Wardveil | Threat assessment, sandbox, scans | Synthetic-tested opt-in Bubblewrap parser isolation, bounded/approved MCP request-output boundary and unit tests; seccomp, isolated MCP workers, provider runtime and independent security acceptance remain open |
| Identity | OIDC/OAuth source contract and scopes | Offline pinned-JWKS RS256 adapter and optional route capability matrix tested; no verified GoreeCloud Identity issuer, delegated multiuser scopes or deployment |
| Mesh | Authenticated service integration | Authenticated read-only capability manifest; not a registered Mesh adapter |
| Billing | Hard USD limit and actual provider reconciliation | Count guard + optional per-key credit-cap preflight; no USD reservation/reconciliation |
| Recovery | Encrypted backup and restore exercise | AES-256-GCM offline backup/restore with synthetic test; external recovery planning open |
| Dependencies | Locks, SBOM and redistribution notices | SHA-pinned CI actions, locked Python/web vulnerability scans and Python/npm lockfile component inventories; Android/Qt, licenses, provenance and complete SBOM open |
| Deployment | TLS, auth, monitoring, rollback | None verified |

No Stable or production release without all applicable approvals.
