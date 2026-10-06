import assert from 'node:assert/strict'
import test from 'node:test'
import { assessKnowledgeAuthorizationInput, KNOWLEDGE_OPERATIONS } from './knowledge-authorization.mjs'

const now = Date.parse('2026-08-30T20:30:00.000Z')
const record = {
  id: '11111111-1111-4111-8111-111111111111',
  resourceId: 'goreecloud-ai-file:11111111-1111-4111-8111-111111111111',
}

function input(overrides = {}) {
  const operation = overrides.operation ?? KNOWLEDGE_OPERATIONS.index
  return {
    operation,
    identity: {
      version: 1,
      authority: 'GoreeCloud Identity',
      actor: { id: 'user-1', type: 'user' },
      authenticated: true,
      observedAt: '2026-08-30T20:29:00.000Z',
      expiresAt: '2026-08-30T21:30:00.000Z',
      applicationAuthorization: {
        resourceId: record.resourceId,
        permittedOperations: [operation],
      },
      ...(overrides.identity ?? {}),
    },
    privacy: {
      request: {
        request_id: 'privacy-request-1',
        requester: { id: 'goreecloud-ai', type: 'application', acting_user: 'user-1' },
        resource: { id: record.resourceId, classification: 'private-user-content' },
        operation,
        purpose: 'user-requested-private-knowledge',
        processing_zone: 'local',
        destination: 'goreecloud-ai-local-knowledge',
        retention: { mode: 'user_defined' },
        external_disclosure: false,
      },
      decision: {
        decision_id: 'privacy-decision-1',
        request_id: 'privacy-request-1',
        outcome: 'ALLOW',
        reason_code: 'policy_and_consent_allow',
        effective_scope: null,
        permitted_operations: [operation],
        processing_zone: 'local',
        permitted_destinations: ['goreecloud-ai-local-knowledge'],
        retention: { mode: 'user_defined' },
        expires_at: '2026-08-30T21:30:00.000Z',
        obligations: ['preserve-private-local-processing'],
      },
      ...(overrides.privacy ?? {}),
    },
  }
}

test('accepts structurally bound Identity and Privacy inputs without creating execution authority', () => {
  const assessment = assessKnowledgeAuthorizationInput(record, input(), now)
  assert.equal(assessment.identity.status, 'satisfied')
  assert.equal(assessment.privacy.status, 'satisfied')
  assert.equal(assessment.sourceTrust.productionTrustedInput, false)
  assert.equal(assessment.persistentAuthorizationCreated, false)
  assert.equal(assessment.executionAuthorized, false)
})

test('treats GoreeCloud AI operation names as application-local authorization operations', () => {
  assert.deepEqual(Object.values(KNOWLEDGE_OPERATIONS), [
    'goreecloud-ai.knowledge.index',
    'goreecloud-ai.knowledge.retrieve',
    'goreecloud-ai.knowledge.model-context',
  ])
})

test('blocks unauthenticated or application-unauthorized Identity input', () => {
  const unauthenticated = input({ identity: { authenticated: false } })
  assert.equal(assessKnowledgeAuthorizationInput(record, unauthenticated, now).identity.reason, 'identity_not_authenticated')

  const operation = KNOWLEDGE_OPERATIONS.retrieve
  const unauthorized = input({ operation })
  unauthorized.identity.applicationAuthorization.permittedOperations = [KNOWLEDGE_OPERATIONS.index]
  assert.equal(assessKnowledgeAuthorizationInput(record, unauthorized, now).identity.reason, 'application_operation_not_authorized')
})

test('blocks expired Identity authorization input and rejects invalid time ordering', () => {
  const expired = input({ identity: { observedAt: '2026-08-30T19:59:00.000Z', expiresAt: '2026-08-30T20:00:00.000Z' } })
  assert.equal(assessKnowledgeAuthorizationInput(record, expired, now).identity.reason, 'identity_authorization_expired')

  const future = input({ identity: { observedAt: '2026-08-30T20:31:00.000Z' } })
  assert.throws(() => assessKnowledgeAuthorizationInput(record, future, now), /observedAt cannot be in the future/)

  const reversed = input({ identity: { observedAt: '2026-08-30T20:29:00.000Z', expiresAt: '2026-08-30T20:28:00.000Z' } })
  assert.throws(() => assessKnowledgeAuthorizationInput(record, reversed, now), /expiresAt must be later than observedAt/)
})

test('rejects a non-finite assessment clock instead of bypassing temporal gates', () => {
  assert.throws(
    () => assessKnowledgeAuthorizationInput(record, input(), Number.NaN),
    /assessment time must be finite/,
  )
  assert.throws(
    () => assessKnowledgeAuthorizationInput(record, input(), Number.POSITIVE_INFINITY),
    /assessment time must be finite/,
  )
})

test('honors Privacy Shield deny and require-user-decision outcomes', () => {
  const denied = input()
  denied.privacy.decision.outcome = 'DENY'
  denied.privacy.decision.reason_code = 'purpose_not_allowed'
  assert.deepEqual(assessKnowledgeAuthorizationInput(record, denied, now).privacy, {
    status: 'blocked',
    authority: 'Privacy Shield',
    reason: 'purpose_not_allowed',
  })

  const decisionRequired = input()
  decisionRequired.privacy.decision.outcome = 'REQUIRE_USER_DECISION'
  decisionRequired.privacy.decision.reason_code = 'fresh_consent_required'
  assert.deepEqual(assessKnowledgeAuthorizationInput(record, decisionRequired, now).privacy, {
    status: 'pending',
    authority: 'Privacy Shield',
    reason: 'fresh_consent_required',
  })
})

test('blocks mismatched Privacy Shield resource, operation, requester, destination, and expiry bindings', () => {
  const resourceMismatch = input()
  resourceMismatch.privacy.request.resource.id = 'different-resource'
  assert.equal(assessKnowledgeAuthorizationInput(record, resourceMismatch, now).privacy.reason, 'privacy_resource_mismatch')

  const operationMismatch = input()
  operationMismatch.privacy.request.operation = KNOWLEDGE_OPERATIONS.retrieve
  assert.equal(assessKnowledgeAuthorizationInput(record, operationMismatch, now).privacy.reason, 'privacy_operation_mismatch')

  const actorMismatch = input()
  actorMismatch.privacy.request.requester.acting_user = 'user-2'
  assert.equal(assessKnowledgeAuthorizationInput(record, actorMismatch, now).privacy.reason, 'privacy_requester_actor_mismatch')

  const destinationMismatch = input()
  destinationMismatch.privacy.decision.permitted_destinations = ['other-destination']
  assert.equal(assessKnowledgeAuthorizationInput(record, destinationMismatch, now).privacy.reason, 'privacy_destination_not_permitted')

  const expired = input()
  expired.privacy.decision.expires_at = '2026-08-30T20:00:00.000Z'
  assert.equal(assessKnowledgeAuthorizationInput(record, expired, now).privacy.reason, 'privacy_decision_expired')
})

test('blocks a structurally valid Privacy Shield request whose retention window already expired', () => {
  const expired = input()
  expired.privacy.request.retention.expires_at = '2026-08-30T20:00:00.000Z'
  const assessment = assessKnowledgeAuthorizationInput(record, expired, now)
  assert.deepEqual(assessment.privacy, {
    status: 'blocked',
    reason: 'privacy_request_retention_expired',
  })
  assert.equal(assessment.persistentAuthorizationCreated, false)
  assert.equal(assessment.executionAuthorized, false)

  const future = input()
  future.privacy.request.retention.expires_at = '2026-08-31T00:00:00.000Z'
  assert.equal(assessKnowledgeAuthorizationInput(record, future, now).privacy.status, 'satisfied')
})

test('fails closed when a service or agent is wrapped as an application requester without a valid actor binding', () => {
  const service = input({
    identity: { actor: { id: 'service-1', type: 'service' } },
  })
  service.privacy.request.requester = { id: 'goreecloud-ai', type: 'application' }
  assert.equal(assessKnowledgeAuthorizationInput(record, service, now).privacy.reason, 'privacy_requester_actor_mismatch')

  const application = input({
    identity: { actor: { id: 'goreecloud-ai', type: 'application' } },
  })
  application.privacy.request.requester = { id: 'goreecloud-ai', type: 'application' }
  const assessment = assessKnowledgeAuthorizationInput(record, application, now)
  assert.equal(assessment.privacy.status, 'satisfied')
})

test('requires Privacy Shield effective_scope as part of the current decision contract', () => {
  const malformed = input()
  delete malformed.privacy.decision.effective_scope
  assert.throws(() => assessKnowledgeAuthorizationInput(record, malformed, now), /effective_scope is required/)
})

test('validates optional Privacy Shield request retention expiry', () => {
  const valid = input()
  valid.privacy.request.retention.expires_at = '2026-08-31T00:00:00.000Z'
  assert.equal(assessKnowledgeAuthorizationInput(record, valid, now).privacy.status, 'satisfied')

  const malformed = input()
  malformed.privacy.request.retention.expires_at = 'not-a-date'
  assert.throws(
    () => assessKnowledgeAuthorizationInput(record, malformed, now),
    /request retention expires_at is invalid/,
  )
})

test('rejects unknown Privacy Shield fields where the authoritative contract is closed', () => {
  const requestField = input()
  requestField.privacy.request.unrecognized = true
  assert.throws(() => assessKnowledgeAuthorizationInput(record, requestField, now), /request contains unsupported fields/)

  const requesterField = input()
  requesterField.privacy.request.requester.unrecognized = true
  assert.throws(() => assessKnowledgeAuthorizationInput(record, requesterField, now), /requester contains unsupported fields/)

  const retentionField = input()
  retentionField.privacy.request.retention.unrecognized = true
  assert.throws(() => assessKnowledgeAuthorizationInput(record, retentionField, now), /request retention contains unsupported fields/)

  const decisionField = input()
  decisionField.privacy.decision.unrecognized = true
  assert.throws(() => assessKnowledgeAuthorizationInput(record, decisionField, now), /decision contains unsupported fields/)
})

test('validates known optional Privacy Shield field types instead of accepting malformed values', () => {
  const disclosure = input()
  disclosure.privacy.request.external_disclosure = 'false'
  assert.throws(() => assessKnowledgeAuthorizationInput(record, disclosure, now), /external_disclosure is invalid/)

  const context = input()
  context.privacy.request.context = []
  assert.throws(() => assessKnowledgeAuthorizationInput(record, context, now), /context is invalid/)

  const consentRequired = input()
  consentRequired.privacy.decision.consent_required = 'false'
  assert.throws(() => assessKnowledgeAuthorizationInput(record, consentRequired, now), /consent_required is invalid/)

  const policyReferences = input()
  policyReferences.privacy.decision.policy_references = ['policy-1', 2]
  assert.throws(() => assessKnowledgeAuthorizationInput(record, policyReferences, now), /policy_references is invalid/)
})

test('rejects malformed inputs instead of manufacturing authorization state', () => {
  assert.throws(() => assessKnowledgeAuthorizationInput(record, { operation: 'not-supported' }, now), (error) => {
    assert.equal(error.status, 400)
    assert.equal(error.code, 'invalid_knowledge_authorization_input')
    return true
  })
})
