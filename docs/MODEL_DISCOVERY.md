# GoreeCloud AI — read-only text model discovery

**Status:** Developer-preview capability metadata. Not a provider-compatibility,
availability, price, billing, model-routing or production deployment guarantee.

## Behavior and privacy

An authenticated owner can deliberately request GET /api/v1/models/catalog to
browse OpenRouter text-model metadata using the already configured server-only
OPENROUTER_API_KEY. The API makes one fixed-origin GET to
https://openrouter.ai/api/v1/models?output_modalities=text, following the
provider's documented endpoint and server-side output-modality filter.
The upstream request transmits **no prompts, saved documents, chat history or
user-entered search strings**. Authentication credentials never reach the client.

The API refuses redirects, proxy environment inheritance, invalid source
shapes, oversized streamed responses (8 MB), and catalogs of more than 2,500
items. It accepts only validated IDs, short names, bounded context lengths
and supported-parameter tool flags; other provider fields are discarded.
Results are sorted and limited to 250 entries. Browser-side search filters
only this sanitized list. The browser does not silently opt into cloud
processing after a model is chosen.

The catalog requires the owner token or pinned signed-owner JWT and, when
strict OIDC capabilities are enabled, the read scope. No paid request or
generation is triggered by discovery; costs can change and metadata may be
stale or incomplete. There is no automatic model compatibility preflight.

## Reference and validation

Upstream API: https://openrouter.ai/docs/api/api-reference/models/get-models

Tests under server/tests/test_text_model_catalog.py use a synthetic HTTP
transport to validate fixed URL, bearer-key containment, metadata sanitization,
response bounds and error paths. The existing OIDC matrix tests check route
classification. Validate with the canonical locked commands in Google Drive
GoreeCloud/CLI Commands/GoreeCloud/AI.md; local source tests do not establish
real-provider compatibility, account spending caps or deployment.
