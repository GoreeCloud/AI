# GoreeCloud AI — product and engineering objectives

**Purpose:** Deliver an original, locally owned hybrid AI workspace that
supports user-controlled model routing and interoperable tools while keeping
personal/family information private by default.

**Product classification:** Native GoreeCloud implementation with
appropriately licensed third-party frameworks and attributed source,
including the official pinned GoreeCloud UI Material 3 Expressive adapter.
See README and THIRD_PARTY_NOTICES.md.

## Required user outcomes

1. **Useful hybrid AI:** Operate chat, streams, image creation, document
   workflows, source-linked retrieval and approved agents across a web,
   Linux and Android application. Preserve legitimate capabilities while
   enforcing precise action permissions, data controls and safe failure.
2. **Data ownership:** Keep documents, conversations and local searches
   private by default, minimize cloud disclosures and make cloud/model costs
   understandable before paid actions. Support explicit retention, export,
   deletion, recoverable backups and safe migration.
3. **Security:** Enforce identity, scoped authorization, least-privilege
   worker isolation, bounded and explicitly approved MCP tool calls, input
   boundaries, secret management and tested rollback.
   The separate GoreeShield privacy and Wardveil cybersecurity responsibilities
   must not be conflated.
4. **Integrations:** Connect only through verified authenticated contracts;
   share permissioned capabilities with GoreeCloud Mesh without making cloud
   access or one service mandatory for local use.
5. **Interface quality:** Use verified GoreeCloud UI assets, Kotlin Compose
   Material 3 Expressive Android styling and appropriate native Linux
   controls. Require practical responsive, keyboard, screen-reader and
   device testing before claiming high-quality release acceptance.
6. **Maintainability:** Keep one public source repository, legally usable
   dependencies and notices, protected pull-request CI, locked builds,
   reproducible inventories, clear CLI guidance and recoverable releases.

## Verified baseline versus pending acceptance

The source provides an authenticated FastAPI preview, React web UI, Qt Linux
UI, Android Compose UI, consent-gated cloud routing, local SQLite documents
with source-tested opt-in SQLCipher full-DB/FTS5 encryption and offline migration,
and conversations, metadata-only approval receipts, synthetic backup/restore
tests, bounded parser subprocesses with opt-in Bubblewrap isolation, and
offline pinned-JWKS authentication.
The optional per-route capability checks remain source-tested and are not a
verified issuer/delegation integration. No physical user-device acceptance,
real model cost reconciliation, activated and operated encrypted live database,
complete sandbox qualification, signed production package, or deployed five-MIPS
integration is demonstrated by this document.

## Evidence before promotion

- API and privacy regressions with both authorized and denied behavior
- Actual private-safe OpenRouter/Ollama integration and billing evidence
  gathered only with approved provider credentials and budget
- Real Linux/Android/browser accessibility and interactive testing
- GoreeShield privacy and retention acceptance, Wardveil security acceptance,
  GoreeCloud Identity source-authenticated issuer/session contract and
  GoreeCloud Mesh authentication/data-policy interoperability
- Encrypted live-data migration, off-host recovery/restore and rollback drills
- Reproducible signed artifacts, licensing/provenance review and staged
  deployment observations

Maintain concrete work in [ROADMAP.md](ROADMAP.md) and verify the status of
[RELEASE_GATES.md](RELEASE_GATES.md). Neither this objective statement nor
passing CI establishes a deployed, Stable or Anchor release.
