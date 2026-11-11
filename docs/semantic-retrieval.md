# GoreeCloud AI — Opt-in Ollama semantic retrieval

**Status:** Source-level experimental local semantic retrieval. Real embeddings and quality metrics remain to be validated with installed model weights and actual hardware. This is NOT a production vector database.

## Ollama API

GoreeCloud AI calls Ollama POST /api/embed with an explicitly chosen installed embedding model and an array of text chunks. Requests set truncate=false so inputs that exceed model context fail rather than silently losing data. The selected model must already be available in Ollama; the application never downloads it.

The official API describes input as a string or array of strings and returns a corresponding array of embeddings. Use the **same model** for indexing and searching.

## Indexing

Create a local text document in Knowledge first. Call POST /api/knowledge/semantic/index with JSON fields document_id and model. The server checks model availability and document existence, splits the selected document into bounded, overlapping 800-character chunks, requests embeddings, validates vector dimensions/values, and transactionally writes the vectors to SQLite. Existing vectors for the same document/model are replaced only after a valid batch. The document itself remains unchanged.

One explicit indexing request operates on one local document. There is no automatic background scan or auto-indexing.

## Search and chat

POST /api/knowledge/semantic/search with query and model to embed a question and compare it with indexed chunks using cosine similarity. The API returns relevant document titles, excerpts, scores and retrieval method.

For optional grounded chat send use_knowledge=true, knowledge_mode=semantic and embedding_model equal to the indexed Ollama embedding model. Ordinary Use knowledge remains keyword-based by default. In the Knowledge dialog select an installed embedding-capable Ollama model, explicitly index each document using Index, and choose Semantic in the search method. In chat enable Use knowledge and select Semantic (experimental) as the knowledge mode; the same Knowledge-selected embedding model is used. Backend API access remains available. Choosing a model name does not verify that the model actually supports embeddings.

## Privacy, security, and limits

Embeddings and excerpts remain local in the configured SQLite database but may encode sensitive characteristics of the original text. The embedding input is sent to the configured Ollama server, which may be remote if an operator changes the origin. Use only trusted endpoints and apply GoreeShield privacy policy.

Indexing is explicit and authenticated, but the prototype's shared token is not per-user resource authorization. Input is limited to 80 chunks per document; each vector is limited to 4096 dimensions; search examines at most 4096 stored chunks. Score ranking is a similarity heuristic and not proof of document relevance or citation correctness. Long-running inference can consume substantial CPU/GPU resources, and there is no production queue or rate limiting.

This increment does not cover PDF/OCR parsing, hybrid ranking, vector database scaling, citations verified against sources, prompt-injection resistance, or real retrieval benchmarks. Keep issue #5 open until those acceptance criteria are independently verified.
