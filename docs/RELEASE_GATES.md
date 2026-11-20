# AI product acceptance gates

| Gate | Required evidence | Preview status |
|---|---|---|
| API | Regression, compatibility, explicit contracts | CI/mock tests only |
| Web | Build, browsers, accessibility | Build tests; user tests pending |
| Linux | Qt startup, real desktop, packaging | Headless smoke; desktop acceptance pending |
| Android | Material3 Expressive build, emulator/device, signing | Debug build; device acceptance pending |
| GoreeShield | Privacy consent records, retention/encryption | Preview opt-in only |
| Wardveil | Threat assessment, sandbox, scans | Source tests; not runtime qualified |
| Identity | OIDC/OAuth source contract and scopes | Unverified/inaccessible |
| Mesh | Authenticated service integration | Not implemented |
| Billing | Hard USD limit and actual provider reconciliation | Count quota only |
| Recovery | Encrypted backup and restore exercise | Not configured |
| Dependencies | Locks, SBOM and redistribution notices | Partial; audit outstanding |
| Deployment | TLS, auth, monitoring, rollback | None verified |

No Stable or production release without all applicable approvals.
