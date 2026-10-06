# GoreeCloud AI Benefits

These benefits describe implemented architectural value and intended product value without asserting production acceptance.

## Current architectural benefits

- **Local-first runtime boundary:** clients reach Ollama through the GoreeCloud AI backend rather than coupling directly to the model runtime.
- **Replaceable model identity:** stable GoreeCloud model roles reduce product coupling to a particular installed model name.
- **First-party persistence:** conversations, Workspaces, and attachment metadata are owned by GoreeCloud AI rather than an adopted third-party AI interface.
- **Fail-closed attachment trust:** unverified, stale, unsupported, malicious, suspicious, or scanner-unavailable content is not silently presented as safe context.
- **Digest-bound post-release processing:** passive text extraction revalidates exact released bytes against the accepted attachment digest before parsing.
- **Small parser attack surface:** the initial extraction boundary accepts only passive UTF-8 text/Markdown/JSON and explicitly excludes complex/active formats.
- **Data lifecycle visibility:** quotas, trust state, released/staged state, derived extraction cleanup, and Workspace reference cleanup are explicit development states.

## Intended platform benefits

When separately implemented and accepted, GoreeCloud Identity, Wardveil Security, Privacy Shield, Everkeep, GoreeCloud Mesh, GoreeCloud Search, and Glaze UI are intended to provide consistent authorization, security, privacy, recovery, coordination, research, accessibility, and evidence presentation around AI use.

These intended benefits remain evidence-gated; current source work does not make a production privacy, security, resilience, or Anchor claim.
