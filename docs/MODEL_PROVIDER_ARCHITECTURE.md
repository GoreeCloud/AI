# GoreeCloud AI Model Provider Architecture

**Status:** Approved architecture direction; implementation and production acceptance remain evidence-bound  
**Decision date:** October 6, 2026  
**Scope:** Model-provider selection, optional OpenAI API integration, local/external processing boundaries, routing, credentials, tools, privacy, security, cost, and provider independence

## 1. Decision

I will design GoreeCloud AI so that the OpenAI API can be enabled as an optional external AI provider.

I will not make OpenAI a mandatory dependency of GoreeCloud AI, and I will not make OpenAI the architectural authority for GoreeCloud AI. GoreeCloud AI will remain the stable first-party product boundary. Local models and other approved model providers must remain usable without requiring OpenAI.

My intended model is:

```text
GoreeCloud AI client
        |
        v
GoreeCloud AI backend
        |
        v
Model Provider Gateway
        |
   +----+---------------------+
   |                          |
   v                          v
Local provider            OpenAI provider
(initially Ollama)        (optional)
   |                          |
   +------------+-------------+
                |
                v
Normalized GoreeCloud AI response
```

I may add other approved providers later without changing the GoreeCloud AI product contract.

## 2. Provider Independence

I will keep GoreeCloud AI provider-independent at the application layer.

The core application must not require users, Workspaces, conversations, tools, retrieval, permissions, or storage to understand provider-specific request formats. Provider-specific behavior belongs behind adapters and the Model Provider Gateway.

I will avoid placing OpenAI-specific model identifiers, response structures, conversation state, billing assumptions, tool semantics, or authentication behavior directly into the core GoreeCloud AI domain model when a normalized GoreeCloud representation is practical.

Disabling or removing the OpenAI provider must not make the rest of GoreeCloud AI unusable.

## 3. Local-First Model Runtime

Ollama remains the initial replaceable local model-runtime foundation for GoreeCloud AI.

I will preserve a local-only operating mode in which prompts, retrieved local context, and model responses can remain inside the approved GoreeCloud environment without being sent to OpenAI or another external model provider.

Local model operation must remain independent from optional external-provider availability.

## 4. Optional OpenAI Provider

I may enable OpenAI as an external model provider when I want access to approved OpenAI models or capabilities.

For new OpenAI integration work, I will use the current supported OpenAI API surface appropriate to the capability. As of this decision, the Responses API is the primary integration surface for new general model interactions.

The OpenAI integration will be implemented through a GoreeCloud-owned provider adapter rather than direct client-to-OpenAI communication.

The intended flow is:

```text
GoreeCloud AI
   -> GoreeCloud AI backend
      -> OpenAI provider adapter
         -> OpenAI API
         -> normalized result
      -> GoreeCloud AI
```

I will keep OpenAI API credentials on the trusted backend side. I will not embed reusable OpenAI API credentials in browser, desktop, or mobile client code.

## 5. Provider Modes

I intend GoreeCloud AI to support clear provider-selection modes such as:

### Local only

I will use only approved local model providers. GoreeCloud AI will not send model prompts or model context to OpenAI.

### OpenAI enabled

I may select an approved OpenAI model for individual conversations, Workspaces, tasks, or model roles while local models remain available.

### OpenAI preferred

I may configure an approved OpenAI model as the preferred provider for a defined scope while retaining a local or other approved fallback where appropriate.

### Automatic routing

I may allow GoreeCloud AI to choose among approved providers based on capability requirements, user preference, administrator policy, privacy classification, availability, latency, context requirements, and cost.

Automatic routing must remain explainable and policy-bound. It must not silently route sensitive information to an external provider when the applicable privacy or authorization rules do not permit that processing.

## 6. User and Administrator Control

I want users and administrators to be able to understand which provider is being used.

Where applicable, GoreeCloud AI should expose:

- the selected provider;
- the selected model or model role;
- whether processing is local or external;
- applicable capability limitations;
- availability or fallback state;
- relevant usage or cost information;
- privacy implications; and
- any policy reason that prevents a requested provider from being used.

I will support configurations in which OpenAI is completely disabled.

## 7. Privacy Shield Boundary

Privacy Shield will govern whether data may be sent to an external model provider.

Before GoreeCloud AI sends conversation content, attachments, retrieved knowledge, repository context, search results, user data, or other protected context to OpenAI, the applicable privacy and authorization rules must permit that external processing.

I will minimize external context to what is necessary for the approved task.

I will not treat access to a Workspace or conversation as blanket authorization to transmit all associated files or knowledge to an external provider.

The interface should clearly distinguish fully local processing from external processing.

## 8. Wardveil Security Boundary

Wardveil Security will govern security-sensitive provider and tool behavior.

A model provider does not become an authorization authority merely because it can reason about a request or request a tool invocation.

OpenAI, local models, and future providers must all remain subordinate to GoreeCloud authorization, trust, and execution controls.

Provider output must be treated as model output rather than verified authority unless an applicable GoreeCloud evidence process establishes otherwise.

## 9. Tools and the AI Capability Broker

I will keep tool execution under GoreeCloud control.

The intended model is:

```text
Model Provider
      |
      | requested tool/action
      v
GoreeCloud AI
      |
      v
AI Capability Broker
      |
   +--+-----------+-----------+
   |              |           |
Permissions    Approval    Execution
   |              |           |
   +--------------+-----------+
                  |
                  v
             GoreeCloud Mesh
```

An OpenAI model may reason about or request an approved tool operation, but the OpenAI provider will not directly control GoreeCloud Drive, GoreeCloud Code, GoreeCloud Search, GoreeCloud Launcher, local files, infrastructure, or other GoreeCloud services.

GoreeCloud will remain responsible for discovery, permissions, approvals, execution, result evidence, audit, failure handling, and rollback requirements.

Provider-specific tools or hosted tool capabilities must not silently bypass GoreeCloud first-party authorization or evidence boundaries.

## 10. GoreeCloud Search

Enabling OpenAI as a model provider does not replace GoreeCloud Search as the first-party current-information and Internet-research integration for GoreeCloud AI.

I will continue to use GoreeCloud Search as the normal GoreeCloud-owned research boundary unless I separately approve another provider-specific capability for a defined purpose.

An OpenAI model provider and a search provider are separate architectural roles.

## 11. Retrieval and Knowledge

GoreeCloud AI will continue to own its first-party knowledge, retrieval, and RAG boundaries.

I may send only the retrieved context necessary for an approved request to an external provider.

I will not make an external provider's proprietary project, memory, vector-store, or retrieval model the only authoritative storage location for GoreeCloud conversations, Workspaces, knowledge, or application state.

Authoritative GoreeCloud source material remains authoritative regardless of which model provider reasons over it.

## 12. Credentials and Secret Handling

OpenAI API credentials are secrets.

I will:

- keep them out of source control;
- keep them out of ordinary documentation;
- store them through approved GoreeCloud secret-management mechanisms;
- scope them to the minimum required purpose where supported;
- support rotation and revocation;
- avoid sharing one unrestricted administrative credential across unrelated environments or users; and
- prevent clients from receiving reusable backend credentials.

Provider credentials must not grant implicit access to GoreeCloud tools or data.

## 13. Cost and Usage

OpenAI usage can create external API costs.

When practical, GoreeCloud AI should make provider usage observable through model identity, request usage, budgets, limits, and other available accounting information.

I may support provider-specific budgets, rate limits, quotas, or administrator policies.

Automatic routing should be able to consider cost, but cost optimization must not override privacy, security, user choice, correctness, or required capability.

## 14. Availability and Fallback

GoreeCloud AI must not assume that an external provider is always reachable.

An OpenAI outage, quota problem, authentication failure, policy restriction, or account issue should fail clearly and should not disable local AI capabilities that remain independently available.

I may support fallback between approved providers when doing so preserves user intent, privacy, security, capability requirements, and model compatibility.

GoreeCloud AI must not silently change from local processing to external processing merely to recover from an outage.

## 15. Future Providers

The Model Provider Gateway is intended to support future approved runtimes and providers.

I may integrate additional local or external model providers when they provide a justified capability, deployment, privacy, reliability, cost, compatibility, or independence benefit.

Every provider will remain behind the same GoreeCloud-owned application, authorization, privacy, tool-execution, and evidence boundaries.

## 16. Native Prompt Caching Architecture (Planned)

### Decision and scope

I will make **prompt caching a native, provider-aware Model Provider Gateway capability** instead of duplicating caching logic throughout GoreeCloud AI and its integrations. The intended benefits are reduced repeated prompt-processing work, eligible model-input charges, and latency. This is a design requirement, **not evidence that caching is implemented or production-accepted**.

Asterport may adopt compatible contracts in its own independently operated backend. A common design must not mean shared tenancy, owner infrastructure, credentials, cached private data, or mandatory runtime coupling between Asterport and GoreeCloud AI.

### Required capabilities

1. **Shared instruction caching:** Keep stable, authorized system instructions and development standards in reusable prefixes where the selected provider supports them. Do not incorrectly elevate project-specific, user-specific, or untrusted text into broadly shared instructions.
2. **Project-context caching:** Reuse eligible architecture specifications, documentation, reference context, and persistent project instructions only while source versions and access permissions remain valid. The cache does not replace the authoritative source.
3. **Agent-context caching:** Permit compatible parallel development agents to reuse eligible context only when their identities, permissions, project scopes, model/provider choices, and data classifications permit it. Isolated agents must not gain additional information or privileges through caching.
4. **Provider-aware caching:** Route through adapters for supported OpenAI, Anthropic, Google, and approved self-hosted runtimes. Honor each provider's actual cache eligibility, matching, retention, billing, expiration, and usage-reporting behavior. Lack of cache support must fall back to ordinary authorized inference.
5. **Cache analytics:** Expose eligible tokens, provider-reported cached tokens where available, reuse rate, time to first token, end-to-end latency, costs, and appropriately qualified savings. Do not represent inferred hits as provider-confirmed results.
6. **Security isolation:** Enforce authenticated principal, deployment owner, account, business, workspace, project, agent, permissions, and data-classification boundaries as applicable. Scope caching behavior by provider, model, instruction/context version, and relevant policy. A provider's internal cache is never GoreeCloud's authorization system.

### Intended processing flow

```text
Authorized GoreeCloud AI client / application
    -> Authentication and application permissions
    -> Privacy Shield context and egress policy
    -> Model Provider Gateway
       -> Stable eligible prefix + dynamic request suffix
       -> Scope, version, and cache-policy validation
       -> Provider-specific cache adapter and metrics
    -> Approved local or external model inference
    -> Fresh normalized model response
```

Keep stable content before changing content when safe and compatible with provider matching rules. Internal cache fingerprints are design aids; some providers expose only implicit prefix reuse rather than an application-managed cache key. Neither caching nor retry behavior may silently move local-only data to an external model or bypass the AI Capability Broker, Wardveil Security, and Privacy Shield.

### Lifecycle, observability, and security

Re-evaluate eligibility whenever instructions, documents, repository revisions, permissions, data classification, provider/model selection, policies, or deployment configuration change. Reject reuse after access revocation or scope mismatch, even if provider-held computations have not yet expired. Follow provider-specific expiration, deletion, retention, and cost rules rather than assuming a universal TTL or purge API.

Protect credentials and private prompts from cache keys and telemetry. Prefer aggregate metrics and opaque identifiers. Distinguish cached-input rates, cache-write/storage charges, ordinary input and output tokens, and estimates where those charges exist. Provider-side caching of transmitted data remains subject to explicit external-processing authorization.

### Distinction and acceptance gates

**Prompt caching is not response caching, RAG retrieval, project memory, or storage of an authoritative document.** It normally reuses eligible model prompt-processing computations while producing a new answer.

Before any implementation or Stable claim, verify prefix matching and misses, invalidation, authorization across accounts/businesses/projects/agents, privacy-mode egress, local-only fallback, provider capability negotiation, error handling, metrics integrity, and representative latency/cost behavior. Do not claim provider parity or universal caching eligibility without live evidence.

## 17. Current Implementation State

The current verified repository remains centered on the existing local-model foundation and other first-party GoreeCloud integration work.

This document establishes the architecture and product direction for optional OpenAI provider support. It does not claim that an OpenAI provider adapter, provider-selection interface, automatic routing, external-provider billing controls, or production OpenAI integration has already been implemented or accepted.

Those capabilities become implemented only when the authoritative source and applicable validation evidence establish that state.

## 18. Final Architecture Decision

I will support the OpenAI API as an optional external AI provider inside GoreeCloud AI.

I will keep GoreeCloud AI itself provider-independent, local-capable, and first-party controlled.

I will preserve Ollama or another approved local runtime as a valid path, allow OpenAI to be enabled when I choose, and leave room for additional approved providers later.

GoreeCloud AI will own the stable application contract, model routing, privacy boundary, tool authorization, capability brokering, evidence, and user experience. OpenAI will provide optional model capabilities behind that GoreeCloud-owned boundary rather than becoming a mandatory dependency or the authority for the platform.
