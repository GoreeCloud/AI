# Model-Role Routing — Development Source Foundation

**Status:** Development source only; not connected to the chat endpoint, installed-model discovery endpoint, or any production authorization path.

`server/model-router.mjs` provides a deterministic, side-effect-free selector for GoreeCloud AI's planned functional model roles. It accepts two inputs that must be assembled by a separately authorized backend integration: the models discovered from the approved local runtime and the administrator-approved model-to-role assignments. There is no automatic access grant based on a model's advertised family or name.

**Selection boundary:** `selectApprovedModel({ role, discoveredModels, approvedModels, preferredModel? })` returns an exact installed and role-approved model, an unavailable result, or an invalid-input result. Manual selection cannot bypass approval. Configured administrative priority takes precedence; Gemma/Qwen family preferences break ties. Model-family preference is not capability verification.

**Not implemented here:** runtime model loading, external providers, new chat endpoints, user authorizations, tool execution, inference, multimodal handling, runtime acceptance, and current Stable Glaze UI consumer acceptance. The existing attachment, Identity, Privacy Shield, Wardveil, and knowledge/RAG gates are untouched.

**Validation:** `node --check server/model-router.mjs && node --test server/model-router.test.mjs`. Existing `npm run test:server` will discover this test file when integrated into the application repository. Before enabling routing in a live request path, source-control review must establish authenticated model-policy provenance, safe handling of model discovery failures, permitted model capabilities, resource constraints, Privacy Shield processing-zone enforcement, and representative runtime tests.
