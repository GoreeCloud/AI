# Local Model-Routing Adapters — Development

**Status:** Development source only. The existing HTTP routes, live chat path, client, installed models, deployed settings, and security gates are unchanged.

`server/model-local-adapters.mjs` adds two opt-in, backend-owned adapters for the existing `createModelRoutePreflight` seam. It is **not imported** by `server/index.mjs`, and it does not infer administrator approval, capabilities, privacy consent, or execution authority.

## Local administrator policy file

`createLocalPolicyLoader({ policyPath })` accepts only an explicit absolute path selected by the local server operator, never a request-provided path. On Linux it rejects a symlinked immediate parent, a symlinked final item, non-regular files, multiply hard-linked files, ownership mismatches, group/other permission bits, files larger than 64 KiB, cancellation, and files that change while being read. A valid file must be owned by the running application UID and have mode 0600 or stricter. Keep this configuration outside web-accessible, Workspace, attachment, and source-code directories. Do not put credentials in it. The preflight validates the JSON policy's schema, role approvals, timestamps, expiry, and revision.

A local file is not authenticated administrator-policy evidence. File metadata and a `source: server-local-config` field do not establish production trust, and a privileged operator must still configure the policy path and directory protections.

## Loopback-only model discovery

`createLoopbackModelDiscovery({ baseUrl })` allows literal HTTP loopback addresses only: `127.0.0.1` or `[::1]`, with an optional port. It refuses hostname resolution, remote/private non-loopback addresses, credentials, query strings, fragments, arbitrary paths, and HTTP redirects. It requests only `/api/tags`, accepts a bounded streamed JSON response of at most 256 KiB, and emits only model names. It does not assert that a model's advertised name gives it a capability. The enclosing preflight provides separate timeouts for local policy read and discovery, plus cancellation.

These defaults assume a runtime on the **same host**. A future container or approved remote-runtime adapter requires its own authenticated network and service-policy design; this development adapter does not weaken its destination allowlist to make such a deployment convenient.

## Developer-only composition

```js
import { createLocalPolicyLoader, createLoopbackModelDiscovery } from './server/model-local-adapters.mjs'
import { createModelRoutePreflight } from './server/model-route-preflight.mjs'

// Use this only in an isolated development script, not from an HTTP route.
const preflight = createModelRoutePreflight({
  loadPolicy: createLocalPolicyLoader({ policyPath: '/approved/private/config/model-policy.json' }),
  discoverModels: createLoopbackModelDiscovery({ baseUrl: 'http://127.0.0.1:11434' }),
})
const result = await preflight({ role: 'coding' })
// Even successful selections have inferenceAuthorized:false.
```

The policy path is an illustrative placeholder, not a claim that the path exists. No default policy file, runtime URL override, public API, or activation flag is introduced by this work.

## Validation and next acceptance requirements

The native `npm run test:server` suite discovers `server/model-local-adapters.test.mjs`. Its tests cover protected local file reads, symlink/hardlink and mode restrictions, local HTTP discovery, URL allowlisting, redirect refusal, response-size and parse failures, cancellation, and a complete preflight composition using a local test server. Tests cannot demonstrate authenticated policy provenance or a successful real Ollama runtime.

Before connecting to the live application, complete authenticated administrator-policy provenance, approved runtime/Identity/Privacy Shield/Policy checks, model capability and resource enforcement, live exact-revision model discovery and streamed generation, security review, and rollback acceptance. This module does not authorize inference, indexing, retrieval, model context, external transfers, tool execution, production deployment, release, or Stable status.
