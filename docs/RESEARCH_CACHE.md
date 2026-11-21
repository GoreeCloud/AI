# GoreeCloud AI — exact research-answer reuse with live-source validation

**Status:** Source and synthetic test implementation, not production deployment.

The optional local_answer_cache=true flag on the authenticated
POST /api/v1/research/answer endpoint can reuse an exact earlier answer
to the same query, selected provider and current document source versions.
Without the flag, every request calls the provider as before.

The server re-runs SQLite FTS5 retrieval on **every** request. The cache
key is a process-random HMAC of the exact question, provider context,
system instruction, selected document IDs, titles, snippets, update
timestamps and order. An edit, new relevant match, changed ranking or
deletion changes the lookup key and requires fresh inference. The cache
never substitutes an answer based on loose phrase similarity: that would
risk confidently returning a wrong response for a different question.

Local reused outputs are kept only in bounded RAM for up to 300 seconds;
the research cache has a separate 64-entry LRU from chat. The provider is
not contacted on a hit, so no cloud key-budget preflight or paid admission
is consumed. Owner authentication, the cloud-consent gate and strict OIDC
cloud capability checks still apply, including for hits.

A hit returns sent_to_cloud=false and original_provider to distinguish
current transmission from the cached answer origin. It never fabricates
new model token usage or generation IDs. The existing authenticated
cache/status route reports a research sub-counter. The explicitly approved
admin-capability cache/clear clears both chat and research entries only
within the handling API worker. Other replicas, backups, swap and remote
provider-managed caches are not affected.

**Risks:** The local result stores model text as plaintext in worker RAM.
Document edit timestamps are updated transactionally by GoreeCloud AI;
external direct SQLite writes that bypass app methods are not supported and
can defeat freshness guarantees. Data can change immediately after retrieval
or between read and reuse, as with any database-backed query: this is not
a serializable source lock or real-time freshness guarantee. No semantic
embedding provider is called or installed. Automatic semantic answer reuse
remains disabled pending owner-verified safe thresholds and provenance.

Source: server/app/storage.py, server/app/main.py,
server/app/token_savings.py, web/src/App.tsx.
Tests: server/tests/test_research_answer_cache.py.
Use the centralized Google Drive CLI Commands/GoreeCloud/AI.md
for locked synthetic verification commands; no external model calls needed.
