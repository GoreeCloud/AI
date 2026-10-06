import assert from 'node:assert/strict'
import test from 'node:test'
import { assessKnowledgeAuthorizationInput, KNOWLEDGE_OPERATIONS } from './knowledge-authorization.mjs'
import { assessKnowledgeEligibility } from './knowledge-eligibility.mjs'

function record(overrides = {}) {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    resourceId: 'goreecloud-ai-file:11111111-1111-4111-8111-111111111111',
    digestSha256: 'a'.repeat(64),
    mediaType: 'text/plain',
    status: 'available',
    storageState: 'released',
    security: {
      releaseAllowed: true,
      useAsContextAllowed: true,
    },
    ...overrides,
  }
}

function extraction(overrides = {}) {
  return {
    version: 1,
    fileId: '11111111-1111-4111-8111-111111111111',
    sourceResourceId: 'goreecloud-ai-file:11111111-1111-4111-8111-111111111111',
    sourceDigestSha256: 'a'.repeat(64),
    state: 'extracted',
    ...overrides,
  }
}

function authorizationInput(targetRecord, outcome = 'ALLOW') {
  const operation = KNOWLEDGE_OPERATIONS.index
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
        resourceId: targetRecord.resourceId,
        permittedOperations: [operation],
      },
    },
    privacy: {
      request: {
        request_id: 'privacy-request-1',
        requester: { id: 'goreecloud-ai', type: 'application', acting_user: 'user-1' },
        resource: { id: targetRecord.resourceId, classification: 'private-user-content' },
        operation,
        purpose: 'user-requested-private-knowledge',
        processing_zone: 'local',
        destination: 'goreecloud-ai-local-knowledge',
        retention: { mode: 'user_defined' },
      },
      decision: {
        decision_id: 'privacy-decision-1',
        request_id: 'privacy-request-1',
        outcome,
        reason_code: outcome === 'REQUIRE_USER_DECISION' ? 'fresh_consent_required' : 'policy_and_consent_allow',
        effective_scope: null,
        permitted_operations: [operation],
        processing_zone: 'local',
        permitted_destinations: ['goreecloud-ai-local-knowledge'],
        retention: { mode: 'user_defined' },
        expires_at: '2026-08-30T21:30:00.000Z',
        obligations: [],
      },
    },
  }
}

test('blocks knowledge eligibility when Wardveil has not released the attachment', () => {
  const assessment = assessKnowledgeEligibility(record({
    status: 'unverified',
    storageState: 'staged',
    security: { releaseAllowed: false, useAsContextAllowed: false },
  }))

  assert.equal(assessment.assessment, 'blocked_security')
  assert.equal(assessment.gates.wardveil.status, 'blocked')
  assert.equal(assessment.eligibleForIndexing, false)
  assert.equal(assessment.eligibleForRetrieval, false)
  assert.equal(assessment.eligibleForModelContext, false)
})

test('reports safe text extraction as pending without creating derived content', () => {
  const assessment = assessKnowledgeEligibility(record())
  assert.equal(assessment.assessment, 'pending_extraction')
  assert.equal(assessment.gates.wardveil.status, 'satisfied')
  assert.deepEqual(assessment.gates.extraction, {
    status: 'pending',
    reason: 'safe_text_extraction_required',
  })
})

test('blocks unsupported parser formats even when Wardveil release is satisfied', () => {
  const assessment = assessKnowledgeEligibility(record({ mediaType: 'application/pdf' }))
  assert.equal(assessment.assessment, 'blocked_parser_or_extraction')
  assert.equal(assessment.gates.wardveil.status, 'satisfied')
  assert.deepEqual(assessment.gates.extraction, {
    status: 'blocked',
    reason: 'media_type_not_supported',
  })
})

test('keeps Identity, Privacy Shield, indexing, retrieval, and model context pending or disabled after a bound extraction', () => {
  const assessment = assessKnowledgeEligibility(record(), extraction())
  assert.equal(assessment.assessment, 'pending_authorization')
  assert.equal(assessment.gates.wardveil.status, 'satisfied')
  assert.equal(assessment.gates.extraction.status, 'satisfied')
  assert.equal(assessment.gates.identity.status, 'pending')
  assert.equal(assessment.gates.privacy.status, 'pending')
  assert.equal(assessment.gates.indexing.status, 'disabled')
  assert.equal(assessment.gates.retrieval.status, 'disabled')
  assert.equal(assessment.gates.modelContext.status, 'disabled')
  assert.equal(assessment.eligibleForIndexing, false)
  assert.equal(assessment.eligibleForRetrieval, false)
  assert.equal(assessment.eligibleForModelContext, false)
})

test('accepts bounded Identity and Privacy assessment inputs while keeping future stages disabled', () => {
  const target = record()
  const authorization = assessKnowledgeAuthorizationInput(target, authorizationInput(target), Date.parse('2026-08-30T20:30:00.000Z'))
  const assessment = assessKnowledgeEligibility(target, extraction(), authorization)

  assert.equal(assessment.assessment, 'pending_stage_implementation')
  assert.equal(assessment.gates.identity.status, 'satisfied')
  assert.equal(assessment.gates.privacy.status, 'satisfied')
  assert.equal(assessment.authorizationAssessment.sourceTrust.productionTrustedInput, false)
  assert.equal(assessment.authorizationAssessment.persistentAuthorizationCreated, false)
  assert.equal(assessment.authorizationAssessment.executionAuthorized, false)
  assert.equal(assessment.eligibleForIndexing, false)
  assert.equal(assessment.eligibleForRetrieval, false)
  assert.equal(assessment.eligibleForModelContext, false)
})

test('preserves Privacy Shield require-user-decision as pending rather than granting access', () => {
  const target = record()
  const authorization = assessKnowledgeAuthorizationInput(target, authorizationInput(target, 'REQUIRE_USER_DECISION'), Date.parse('2026-08-30T20:30:00.000Z'))
  const assessment = assessKnowledgeEligibility(target, extraction(), authorization)
  assert.equal(assessment.assessment, 'pending_privacy_user_decision')
  assert.equal(assessment.gates.privacy.status, 'pending')
  assert.equal(assessment.eligibleForModelContext, false)
})

test('fails the extraction gate when derived evidence is not bound to the current source', () => {
  const assessment = assessKnowledgeEligibility(record(), extraction({ sourceDigestSha256: 'b'.repeat(64) }))
  assert.equal(assessment.assessment, 'blocked_parser_or_extraction')
  assert.deepEqual(assessment.gates.extraction, {
    status: 'blocked',
    reason: 'extraction_binding_mismatch',
  })
})
