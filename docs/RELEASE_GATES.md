# AI product acceptance gates

| Gate | Required evidence | Preview status |
|---|---|---|
| API | Regression, compatibility, explicit contracts | Python CI/mock tests include bounded provider image responses and capability discovery; live-provider contract acceptance pending |
| Web | Build, browsers, accessibility | TypeScript build covers image catalog selector; browser and accessibility verification pending |
| Linux | Qt startup, real desktop, packaging | Headless smoke; desktop acceptance pending |
| Android | Material3 Expressive build, emulator/device, signing | Debug build; device acceptance pending |
| GoreeShield | Privacy consent records, retention/encryption | Opt-in consent and explicitly approved snapshot retention purge; live DB unencrypted |
| Wardveil | Threat assessment, sandbox, scans | Linux subprocess import limits and tests; OS sandbox and runtime security acceptance remain pending |
| Identity | OIDC/OAuth source contract and scopes | Offline pinned-JWKS RS256 adapter tested; no verified GoreeCloud Identity issuer/deployment |
| Mesh | Authenticated service integration | Authenticated read-only capability manifest; not a registered Mesh adapter |
| Billing | Hard USD limit and actual provider reconciliation | Count guard + optional per-key credit-cap preflight; no USD reservation/reconciliation |
| Recovery | Encrypted backup and restore exercise | AES-256-GCM offline backup/restore with synthetic test; external recovery planning open |
| Dependencies | Locks, SBOM and redistribution notices | Locked Python production-dependency vulnerability audit added to CI; complete SBOM, license and Android/Qt review open |
| Deployment | TLS, auth, monitoring, rollback | None verified |

No Stable or production release without all applicable approvals.
