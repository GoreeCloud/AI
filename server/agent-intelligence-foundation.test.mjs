import assert from 'node:assert/strict'
import test from 'node:test'
import { chooseAgentRecovery, classifyAgentExecutionMode, planAgentWork, selectAgentCapability, selectAgentContext } from './agent-intelligence-foundation.mjs'

const baseTask = (id, extra = {}) => ({ id, goalId: 'goal', state: 'ready', dependencies: [], sharedResources: [], priority: 10, risk: 'low', effect: 'read-only', authorization: 'authorized', verificationRequired: false, verificationSatisfied: false, ...extra })

test('context selection applies freshness and goal scope', () => {
  const item = { id: 'ctx', kind: 'governance', source: 'instructions', authority: 'governing', observedAtMs: 10, expiresAtMs: 100, sensitivity: 'internal', sharing: 'local-only', scope: 'goal', reference: 'current' }
  assert.equal(selectAgentContext({ items: [item], nowMs: 50, scope: 'goal', requiredKinds: ['governance'] }).status, 'selected')
  assert.equal(selectAgentContext({ items: [{ ...item, expiresAtMs: 40 }], nowMs: 50, scope: 'goal' }).rejected[0].reasons[0], 'stale')
  assert.equal(selectAgentContext({ items: [{ ...item, scope: 'other' }], nowMs: 50, scope: 'goal' }).rejected[0].reasons[0], 'scope_mismatch')
})

test('work planner respects dependencies and shared resources', () => {
  const result = planAgentWork({ tasks: [
    baseTask('done', { state: 'completed' }),
    baseTask('first', { dependencies: ['done'], sharedResources: ['branch'], priority: 1, effect: 'reversible-write', actionId: 'act-1' }),
    baseTask('second', { dependencies: ['done'], sharedResources: ['branch'], priority: 2, effect: 'reversible-write', actionId: 'act-2' }),
    baseTask('independent', { sharedResources: ['docs'] }),
  ] })
  assert.deepEqual(result.runnable.map((item) => item.id), ['first', 'independent'])
  assert.equal(result.blocked.find((item) => item.id === 'second').reason, 'shared_resource_conflict')
})

test('duplicate mutation action identities are rejected', () => {
  const result = planAgentWork({ tasks: [
    baseTask('one', { effect: 'reversible-write', actionId: 'same' }),
    baseTask('two', { effect: 'reversible-write', actionId: 'same' }),
  ] })
  assert.equal(result.status, 'invalid')
})

test('capability selection prefers authoritative read-only fit', () => {
  const common = { kind: 'tool', operations: ['repo.read'], permission: 'allowed', health: 'healthy', maxSensitivity: 'internal', priority: 10 }
  const result = selectAgentCapability({ operation: 'repo.read', sensitivity: 'internal', requiresAuthoritativeOwner: true, candidates: [
    { id: 'writer', ...common, authority: 'authoritative-owner', effect: 'reversible-write' },
    { id: 'reader', ...common, authority: 'authoritative-owner', effect: 'read-only', priority: 100 },
  ] })
  assert.equal(result.capabilityId, 'reader')
  assert.equal(result.executionAuthorized, false)
})

test('execution mode scales with complexity and consequence', () => {
  assert.equal(classifyAgentExecutionMode({ taskCount: 1, systemCount: 1, ambiguity: 'low', risk: 'low', consequentialWrites: 0 }).mode, 'direct')
  assert.equal(classifyAgentExecutionMode({ taskCount: 5, systemCount: 3, ambiguity: 'moderate', risk: 'moderate', consequentialWrites: 0 }).mode, 'complex')
  assert.equal(classifyAgentExecutionMode({ taskCount: 2, systemCount: 1, ambiguity: 'low', risk: 'moderate', consequentialWrites: 1 }).mode, 'high-consequence')
})


test('bounded retry planning', () => {
  const retry = chooseAgentRecovery({ failureClass: 'transient', retryCount: 1, maxRetries: 2 })
  assert.equal(retry.action, 'retry')
  assert.equal(retry.requiresReverification, true)
  assert.equal(retry.executionAuthorized, false)
  const exhausted = chooseAgentRecovery({ failureClass: 'transient', retryCount: 2, maxRetries: 2 })
  assert.equal(exhausted.action, 'stop')
})

test('available recovery paths are explicit', () => {
  assert.equal(chooseAgentRecovery({ failureClass: 'recoverable', repairAvailable: true }).action, 'repair')
  assert.equal(chooseAgentRecovery({ failureClass: 'fallback', alternateAvailable: true }).action, 'fallback')
  assert.equal(chooseAgentRecovery({ failureClass: 'degraded', degradationAvailable: true }).action, 'degrade')
  assert.equal(chooseAgentRecovery({ failureClass: 'blocking' }).action, 'stop')
})
