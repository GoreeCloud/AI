# GoreeCloud AI — Semantic Index Integrity and Diagnostics

**Status:** Source-level integrity safeguards for the opt-in local embedding index. These are not real-model retrieval benchmarks or proof of production readiness.

## Endpoints and behavior

- Authenticated `GET /api/knowledge/semantic/status` returns only indexed document and chunk counts grouped by embedding model. It does not expose prompts, document text or raw vectors.
- Semantic search requires that at least one document has been explicitly indexed with the requested installed embedding model. Otherwise it returns HTTP 409 before performing embedding inference.
- Semantically grounded chat has the same missing-index preflight; this prevents unintentionally falling back to keyword retrieval or creating a misleading chat response.
- An index with more than 4,096 stored chunks for the chosen model fails with an explicit capacity error, rather than scanning only the first records. The scan is deterministic.
- Invalid JSON, nonfinite vectors, or query/index dimension mismatch raises a validation error instead of silently omitting corrupted data.
- Cosine similarity normalizes operands before multiplication, avoiding arithmetic overflow for valid but unusually large finite vector values.
- Failures prior to streaming do not save chat exchanges; existing knowledge and previous history remain intact.

## Known limits

These changes protect **integrity and error reporting**, not semantic answer quality. The status endpoint reports aggregate counts only, not every vector's validity. It does not repair damaged indexes or make an index scalable beyond the configured scan bound. The local prototype still has a shared API token, plaintext SQLite storage, and no per-user knowledge boundaries. Indexing can be resource-intensive; Ollama must already have the explicitly chosen embedding model installed.

GoreeShield governs privacy and data consent, Wardveil governs cybersecurity safeguards, GoreeCloud Mesh governs integration, GoreeCloud UI governs interface standards, and GoreeCloud Identity governs authentication/authorization. None of those unimplemented integrations should be inferred from this feature.

## Testing

Synthetic vectors and fake Ollama responses validate index listing, missing-index rejection, overflow, corrupt vectors, incompatible dimensions, document-deletion cascades, and the absence of partial conversation persistence. Live Ollama models and real hardware performance remain separate acceptance items.
