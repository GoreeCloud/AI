# Third-party notices and provenance

Original GoreeCloud AI code: MIT (see repository root LICENSE).

- GoreeCloud UI, MIT: design/gc.tokens.json and web/src/gc-tokens.css are
  attributed snapshots from https://github.com/GoreeCloud/gc-ui.
  The source-included Android gc-ui-compose files derive from immutable
  upstream commit 5625121316230d78dd40a6e41a0671a250cb873b; see
  android/gc-ui-compose/UPSTREAM.md. Original files are copied, not rewritten.
  This is an alpha adapter, not a published SDK.
- FastAPI, Starlette, httpx, Python-Multipart, pypdf, python-docx, PyJWT, cryptography and MCP SDK:
  Python package dependencies governed by their upstream licenses.
- React, React DOM, Vite and TypeScript: JavaScript package dependencies,
  governed by upstream licenses and web/package-lock.json.
- PySide6/Qt Quick: LGPL/commercial Qt licensing and redistributed Qt plugin
  notices must be evaluated before building distribution packages.
- Kotlin, AndroidX, Jetpack Compose and Material3: upstream license/Android
  redistribution rules apply. Android SDK license requirements apply.
- OpenRouter: externally hosted API and model marketplace, not rehosted source;
  model licenses, pricing, privacy and availability must be evaluated.
- Ollama: optional independently installed runtime. Model weights and
  licenses are never bundled by GoreeCloud AI.
- Open WebUI, AnythingLLM, LibreChat: comparison references only. Their
  application code is not copied or redistributed. Newer Open WebUI uses
  branding restrictions and is not assumed standard OSI-open-source code.

No dependency security or legal compliance claim follows from this notice;
maintain a current SBOM/license audit before release. Never place paid keys,
private user content or model weights in the public repo.
