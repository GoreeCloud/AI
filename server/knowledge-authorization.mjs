export const KNOWLEDGE_OPERATIONS = Object.freeze({
  index: 'goreecloud-ai.knowledge.index',
  retrieve: 'goreecloud-ai.knowledge.retrieve',
  modelContext: 'goreecloud-ai.knowledge.model-context',
})

const OPERATION_SET = new Set(Object.values(KNOWLEDGE_OPERATIONS))
const ACTOR_TYPES = new Set(['user', 'service', 'agent', 'application', 'system'])
const PRIVACY_REQUESTER_TYPES = new Set(['application', 'service', 'user', 'agent', 'model', 'system'])
const PRIVACY_ZONES = new Set(['local', 'private_goreecloud', 'trusted_service', 'external'])
const PRIVACY_RETENTION_MODES = new Set(['none', 'session', 'temporary', 'user_defined', 'application_defined', 'organizational', 'permanent'])
const PRIVACY_OUTCOMES = new Set(['ALLOW', 'DENY', 'ALLOW_WITH_CONSTRAINTS', 'REQUIRE_USER_DECISION'])
const PRIVACY_REQUEST_KEYS = new Set([
  'request_id',
  'requester',
  'resource',
  'operation',
  'purpose',
  'processing_zone',
  'destination',
  'retention',
  'external_disclosure',
  'context',
  'delegation_chain',
  'consent_reference',
  'manifest_reference',
  'wardveil_evidence_reference',
])
const PRIVACY_REQUESTER_KEYS = new Set(['id', 'type', 'acting_user'])
const PRIVACY_RETENTION_KEYS = new Set(['mode', 'expires_at'])
const PRIVACY_DECISION_KEYS = new Set([
  'decision_id',
  'request_id',
  'outcome',
  'reason_code',
  'effective_scope',
  'permitted_operations',
  'processing_zone',
  'permitted_destinations',
  'retention',
  'expires_at',
  'consent_required',
  'obligations',
  'policy_references',
  'capability_token_reference',
  'evidence_reference',
])

function invalid(message) {
  throw Object.assign(new Error(message), { status: 400, code: 'invalid_knowledge_authorization_input' })
}

function nonEmpty(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function dateMs(value) {
  if (!nonEmpty(value)) return null
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : null
}

function rejectUnknownKeys(value, allowed, message) {
  if (Object.keys(value).some((key) => !allowed.has(key))) invalid(message)
}

function optionalStringOrNull(value) {
  return value === undefined || value === null || typeof value === 'string'
}

function optionalStringArray(value) {
  return value === undefined || (Array.isArray(value) && value.every((entry) => typeof entry === 'string'))
}

function identityGate(record, operation, identity, nowMs) {
  if (!identity || typeof identity !== 'object' || Array.isArray(identity)) invalid('identity authorization input is required')
  if (identity.version !== 1 || identity.authority !== 'GoreeCloud Identity') invalid('unsupported identity authorization input')
  if (!identity.actor || typeof identity.actor !== 'object' || Array.isArray(identity.actor)) invalid('identity actor is required')
  if (!nonEmpty(identity.actor.id) || !ACTOR_TYPES.has(identity.actor.type)) invalid('identity actor is invalid')
  const observedAt = dateMs(identity.observedAt)
  if (observedAt === null) invalid('identity observedAt must be a valid date-time')
  const expiresAt = dateMs(identity.expiresAt)
  if (expiresAt === null) invalid('identity expiresAt must be a valid date-time')
  if (observedAt > nowMs) invalid('identity observedAt cannot be in the future')
  if (expiresAt <= observedAt) invalid('identity expiresAt must be later than observedAt')
  if (!identity.applicationAuthorization || typeof identity.applicationAuthorization !== 'object' || Array.isArray(identity.applicationAuthorization)) {
    invalid('application authorization context is required')
  }
  const app = identity.applicationAuthorization
  if (!nonEmpty(app.resourceId) || !Array.isArray(app.permittedOperations) || !app.permittedOperations.every(nonEmpty)) {
    invalid('application authorization context is invalid')
  }

  if (identity.authenticated !== true) return { status: 'blocked', reason: 'identity_not_authenticated' }
  if (expiresAt <= nowMs) return { status: 'blocked', reason: 'identity_authorization_expired' }
  if (app.resourceId !== record.resourceId) return { status: 'blocked', reason: 'identity_resource_mismatch' }
  if (!app.permittedOperations.includes(operation)) return { status: 'blocked', reason: 'application_operation_not_authorized' }

  return {
    status: 'satisfied',
    authority: 'GoreeCloud Identity + GoreeCloud AI application authorization',
    reason: 'identity_and_application_authorization_input_satisfied',
    actor: { id: identity.actor.id, type: identity.actor.type },
    expiresAt: identity.expiresAt,
  }
}

function validatePrivacyRequest(request) {
  if (!request || typeof request !== 'object' || Array.isArray(request)) invalid('Privacy Shield request is required')
  rejectUnknownKeys(request, PRIVACY_REQUEST_KEYS, 'Privacy Shield request contains unsupported fields')
  if (!nonEmpty(request.request_id)) invalid('Privacy Shield request_id is required')
  if (!request.requester || typeof request.requester !== 'object' || Array.isArray(request.requester)) invalid('Privacy Shield requester is required')
  rejectUnknownKeys(request.requester, PRIVACY_REQUESTER_KEYS, 'Privacy Shield requester contains unsupported fields')
  if (!nonEmpty(request.requester.id) || !PRIVACY_REQUESTER_TYPES.has(request.requester.type)) invalid('Privacy Shield requester is invalid')
  if (request.requester.acting_user !== undefined && request.requester.acting_user !== null && !nonEmpty(request.requester.acting_user)) invalid('Privacy Shield acting_user is invalid')
  if (!request.resource || typeof request.resource !== 'object' || Array.isArray(request.resource)) invalid('Privacy Shield resource is required')
  if (!nonEmpty(request.resource.id) || !nonEmpty(request.resource.classification)) invalid('Privacy Shield resource is invalid')
  if (!nonEmpty(request.operation) || !nonEmpty(request.purpose)) invalid('Privacy Shield operation and purpose are required')
  if (!PRIVACY_ZONES.has(request.processing_zone) || !nonEmpty(request.destination)) invalid('Privacy Shield processing zone or destination is invalid')
  if (!request.retention || typeof request.retention !== 'object' || Array.isArray(request.retention) || !PRIVACY_RETENTION_MODES.has(request.retention.mode)) invalid('Privacy Shield retention is invalid')
  rejectUnknownKeys(request.retention, PRIVACY_RETENTION_KEYS, 'Privacy Shield request retention contains unsupported fields')
  if (request.retention.expires_at !== undefined && request.retention.expires_at !== null && dateMs(request.retention.expires_at) === null) invalid('Privacy Shield request retention expires_at is invalid')
  if (request.external_disclosure !== undefined && typeof request.external_disclosure !== 'boolean') invalid('Privacy Shield external_disclosure is invalid')
  if (request.context !== undefined && (!request.context || typeof request.context !== 'object' || Array.isArray(request.context))) invalid('Privacy Shield context is invalid')
  if (!optionalStringArray(request.delegation_chain)) invalid('Privacy Shield delegation_chain is invalid')
  if (!optionalStringOrNull(request.consent_reference)) invalid('Privacy Shield consent_reference is invalid')
  if (!optionalStringOrNull(request.manifest_reference)) invalid('Privacy Shield manifest_reference is invalid')
  if (!optionalStringOrNull(request.wardveil_evidence_reference)) invalid('Privacy Shield wardveil_evidence_reference is invalid')
}

function validatePrivacyDecision(decision) {
  if (!decision || typeof decision !== 'object' || Array.isArray(decision)) invalid('Privacy Shield decision is required')
  rejectUnknownKeys(decision, PRIVACY_DECISION_KEYS, 'Privacy Shield decision contains unsupported fields')
  if (!nonEmpty(decision.decision_id) || !nonEmpty(decision.request_id) || !PRIVACY_OUTCOMES.has(decision.outcome) || !nonEmpty(decision.reason_code)) {
    invalid('Privacy Shield decision identity is invalid')
  }
  if (!Object.hasOwn(decision, 'effective_scope')) invalid('Privacy Shield effective_scope is required')
  if (decision.effective_scope !== null && typeof decision.effective_scope !== 'object' && typeof decision.effective_scope !== 'string') invalid('Privacy Shield effective_scope is invalid')
  if (!Array.isArray(decision.permitted_operations) || !decision.permitted_operations.every(nonEmpty)) invalid('Privacy Shield permitted_operations is invalid')
  if (!PRIVACY_ZONES.has(decision.processing_zone)) invalid('Privacy Shield decision processing_zone is invalid')
  if (!Array.isArray(decision.permitted_destinations) || !decision.permitted_destinations.every(nonEmpty)) invalid('Privacy Shield permitted_destinations is invalid')
  if (!decision.retention || typeof decision.retention !== 'object' || Array.isArray(decision.retention)) invalid('Privacy Shield decision retention is invalid')
  if (!Array.isArray(decision.obligations) || !decision.obligations.every(nonEmpty)) invalid('Privacy Shield obligations are invalid')
  if (decision.expires_at !== undefined && decision.expires_at !== null && dateMs(decision.expires_at) === null) invalid('Privacy Shield decision expires_at is invalid')
  if (decision.consent_required !== undefined && typeof decision.consent_required !== 'boolean') invalid('Privacy Shield consent_required is invalid')
  if (!optionalStringArray(decision.policy_references)) invalid('Privacy Shield policy_references is invalid')
  if (!optionalStringOrNull(decision.capability_token_reference)) invalid('Privacy Shield capability_token_reference is invalid')
  if (!optionalStringOrNull(decision.evidence_reference)) invalid('Privacy Shield evidence_reference is invalid')
}

function requesterMatchesActor(requester, actor) {
  if (requester.type === 'application') {
    if (actor.type === 'user') return requester.acting_user === actor.id
    if (actor.type === 'application') return requester.id === actor.id && (requester.acting_user === undefined || requester.acting_user === null)
    return false
  }
  return requester.id === actor.id && (requester.acting_user === undefined || requester.acting_user === null)
}

function privacyGate(record, operation, privacy, identity, nowMs) {
  if (!privacy || typeof privacy !== 'object' || Array.isArray(privacy)) invalid('privacy authorization input is required')
  validatePrivacyRequest(privacy.request)
  validatePrivacyDecision(privacy.decision)

  const { request, decision } = privacy
  if (request.resource.id !== record.resourceId) return { status: 'blocked', reason: 'privacy_resource_mismatch' }
  if (request.operation !== operation) return { status: 'blocked', reason: 'privacy_operation_mismatch' }
  if (decision.request_id !== request.request_id) return { status: 'blocked', reason: 'privacy_request_binding_mismatch' }
  if (!requesterMatchesActor(request.requester, identity.actor)) return { status: 'blocked', reason: 'privacy_requester_actor_mismatch' }
  if (request.retention.expires_at && Date.parse(request.retention.expires_at) <= nowMs) {
    return { status: 'blocked', reason: 'privacy_request_retention_expired' }
  }

  if (decision.outcome === 'DENY') {
    return { status: 'blocked', authority: 'Privacy Shield', reason: decision.reason_code }
  }
  if (decision.outcome === 'REQUIRE_USER_DECISION') {
    return { status: 'pending', authority: 'Privacy Shield', reason: decision.reason_code }
  }

  if (!decision.permitted_operations.includes(operation)) return { status: 'blocked', reason: 'privacy_operation_not_permitted' }
  if (decision.processing_zone !== request.processing_zone) return { status: 'blocked', reason: 'privacy_processing_zone_mismatch' }
  if (!decision.permitted_destinations.includes(request.destination)) return { status: 'blocked', reason: 'privacy_destination_not_permitted' }
  if (decision.expires_at && Date.parse(decision.expires_at) <= nowMs) return { status: 'blocked', reason: 'privacy_decision_expired' }

  return {
    status: 'satisfied',
    authority: 'Privacy Shield',
    reason: decision.outcome === 'ALLOW_WITH_CONSTRAINTS' ? 'privacy_allowed_with_constraints' : 'privacy_allowed',
    outcome: decision.outcome,
    decisionId: decision.decision_id,
    obligations: [...decision.obligations],
    expiresAt: decision.expires_at ?? null,
  }
}

export function assessKnowledgeAuthorizationInput(record, value, nowMs = Date.now()) {
  if (!record) invalid('attachment record is required')
  if (!Number.isFinite(nowMs)) invalid('authorization assessment time must be finite')
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid('knowledge authorization input must be an object')
  if (!OPERATION_SET.has(value.operation)) invalid('unsupported GoreeCloud AI knowledge operation')

  const identity = identityGate(record, value.operation, value.identity, nowMs)
  const privacy = privacyGate(record, value.operation, value.privacy, value.identity, nowMs)

  return {
    version: 1,
    operation: value.operation,
    identity,
    privacy,
    sourceTrust: {
      productionTrustedInput: false,
      reason: 'authenticated_identity_and_privacy_adapters_not_connected',
    },
    persistentAuthorizationCreated: false,
    executionAuthorized: false,
  }
}
