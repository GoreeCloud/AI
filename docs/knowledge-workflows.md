# GoreeCloud AI — Local knowledge workflows

**Implementation:** explicit browser text-file import and authenticated in-dialog keyword search. This is not vector search, semantic RAG, PDF OCR, or automatic filesystem synchronization.

## Local text-file import

Open Knowledge and choose a local file with a .txt, .md, .csv or .json suffix. Only the selected file is read by the browser. Files are limited to 100 KB and document text to 50,000 characters. The file name becomes the bounded document title; file contents are sent to the existing local document API and stored as text in SQLite. CSV and JSON are not parsed or executed as code.

No directories are scanned, and no URLs are followed. Delete an imported document from the Knowledge list.

## Search and grounded conversation

The Knowledge dialog searches local keyword excerpts through POST /api/knowledge/search so query terms are not appended to URLs. Results use safe text rendering. The original GET /api/knowledge/search?q=... remains available for backward compatibility and may expose query strings in intermediary access logs.

Enable Use knowledge in the chat composer to include matching excerpts as untrusted context. Returned source metadata is a provenance aid, not a guarantee that generated claims are correct.

## Security limitations

Document data remains plaintext and shared by anyone with the current prototype API token. GoreeCloud Identity access control, GoreeShield retention policies and Wardveil review are required before multi-user or public deployment. There is no malware scanning beyond treating these explicit supported formats as inert text; additional format handlers must have dedicated security checks.

## Next milestones

Local embeddings, OCR/PDF extraction, chunking and retrieval evaluation remain planned.
