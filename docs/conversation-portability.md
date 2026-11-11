# GoreeCloud AI — Conversation import and export

**Implemented:** versioned JSON export of one conversation and bounded, opt-in import of GoreeCloud AI version 1 exports into the current single-user database.

## Workflow

Export a conversation using the in-app Export button or the authenticated GET /api/chats/{id}/export endpoint. The file contains plaintext user/assistant messages, model labels, and historical metadata; treat the file as private.

Use the Import button to choose the exported JSON file, or POST it as application/json to /api/chats/import. A successful response returns a new conversation ID, leaving the original conversation unchanged.

## Import validation

- Only the GoreeCloud AI conversation format with version 1 is accepted.
- Input is read as bounded JSON (1,500,000 bytes), with no scripts, archives, shell commands, binary uploads, or external URLs evaluated.
- The imported title must be nonblank, at most 100 characters.
- At most 250 messages, in complete alternating user/assistant pairs, can be imported.
- User messages and assistant responses must meet configured character limits.
- The application generates new UUIDs and timestamps rather than trusting source IDs or source timestamps.
- All database inserts occur inside one transaction; malformed imports do not create partial conversation records.
- Imported content is untrusted data; the browser renders it as text.

## Limitations

This is not a multi-user portability or cross-product migration service. There is no import of other chat formats, file scanning, cloud synchronization, or sensitive-content de-identification. Existing exports over the current import limits cannot be imported unchanged; no silent truncation occurs. Store downloaded JSON only where GoreeShield privacy obligations and Wardveil security policies can be enforced.
