# GoreeCloud AI — Privacy Policy

**Document version:** 0.1  
**Lifecycle:** Development  
**Applies to:** GoreeCloud AI development source and future supported deployments

GoreeCloud AI is designed to be private by default, local-first, purpose-limited, and explicit about when information leaves the local AI boundary. This document states the intended privacy contract and current Development limitations; it is not evidence that Privacy Shield runtime acceptance has already occurred.

## Local-first processing

The primary model runtime is Ollama and is intended to operate privately. The GoreeCloud AI backend owns model access so browsers and clients do not need direct Ollama access. Local conversations must remain usable when external research providers are unavailable.

GoreeCloud AI does not require advertising telemetry, behavioral profiling, or mandatory remote analytics for normal local AI operation. New telemetry or external processing requires explicit GoreeCloud privacy authority, documented purpose, minimization, retention, and user-facing disclosure.

## Data categories

Depending on enabled features, GoreeCloud AI may process:

- conversation messages and conversation metadata;
- Workspace configuration and membership/authorization state;
- uploaded files and derived extraction/indexing records;
- model selections and bounded generation metadata;
- local operational and security evidence;
- research queries and returned sources when GoreeCloud Search is explicitly used;
- generated artifacts or images when those capabilities are implemented and enabled.

Credentials, authorization evidence, and sensitive security material must not be exposed in ordinary model context, logs, analytics, citations, or generated artifacts.

## Attachments and knowledge use

Upload does not equal trust or permission for model use. Files remain staged until required Wardveil evidence, application authorization, Privacy Shield authorization, parser/extraction safety, and later knowledge-stage controls are satisfied.

The current Development knowledge-assessment surfaces are deliberately non-authorizing. Caller-supplied Identity, Privacy Shield, Wardveil, or runtime-evidence-shaped JSON cannot establish production trust by itself. Indexing, retrieval, and model-context use must fail closed when required authority or evidence is missing, expired, mismatched, revoked, replayed, or unverified.

Derived indexes and embeddings are derived state. Authoritative source documents remain authoritative. Deleting or revoking a source must propagate through future derived-state handling according to the accepted retention and recovery contract.

## External research and providers

GoreeCloud Search is the intended first-party current-information and Internet-research provider. External research must be clearly distinguishable from fully local conversation and local knowledge use. Search queries must be minimized to the requested purpose, and retrieved external content must be treated as untrusted input.

No future external AI, image, speech, or tool provider may silently receive conversation, file, Workspace, identity, or knowledge data. External processing requires an approved adapter, Privacy Shield authorization, destination and purpose binding, security review, and user-facing disclosure where required.

## Retention, deletion, export, and recovery

Users must have governed controls for conversation, Workspace, file, derived-state, and generated-artifact retention where applicable. Deletion must remove application-owned state and account for derived records rather than only hiding UI references.

Export, portability, backup, and restore must be designed with Everkeep. Backup scope must not silently expand into unrelated user data. Restore evidence must establish integrity and authorization before recovered knowledge or credentials are treated as usable.

## Privacy Shield boundary

Privacy Shield is the GoreeCloud privacy authorization authority. GoreeCloud AI remains responsible for its own resource and Workspace authorization while consuming verified Privacy Shield decisions for governed data operations.

Development source that validates the structure of a Privacy Shield-shaped record does not make that record authoritative. Production use requires authenticated decision provenance, exact request/resource/operation binding, expiry and retention enforcement, revocation/replay handling, durable evidence where required, and target-runtime acceptance.

## Current Development limitations

At the current Development checkpoint, authenticated Privacy Shield runtime integration and acceptance are not established. Production-trusted authorization, persistent authorization creation, execution authorization, and knowledge-stage eligibility therefore remain fail-closed. GoreeCloud AI must not be represented as production privacy-accepted until authoritative evidence says otherwise.
