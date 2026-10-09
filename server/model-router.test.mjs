import test from 'node:test'
import assert from 'node:assert/strict'
import { MODEL_ROLES, selectApprovedModel } from './model-router.mjs'

const discoveredModels = [{ name: 'gemma3:12b' }, { name: 'qwen3-coder:latest' }, { name: 'qwen3:8b' }]
const approvedModels = [
  { name: 'gemma3:12b', family: 'gemma', roles: ['reasoning', 'general', 'writing'] },
  { name: 'qwen3-coder:latest', family: 'qwen', roles: ['reasoning', 'coding', 'agent'] },
  { name: 'qwen3:8b', family: 'qwen', roles: ['general', 'fast'] },
]
const route = (role, extra = {}) => selectApprovedModel({ role, discoveredModels, approvedModels, ...extra })

test('exposes each planned functional role exactly once', () => {
  assert.equal(MODEL_ROLES.length, 13)
  assert.equal(new Set(MODEL_ROLES).size, MODEL_ROLES.length)
})

test('prefers approved Gemma for the general role when priorities tie', () => {
  assert.deepEqual(route('general'), {
    status: 'selected', role: 'general', model: 'gemma3:12b', family: 'gemma', selection: 'automatic',
  })
})

test('prefers approved Qwen for the coding role', () => {
  assert.equal(route('coding').model, 'qwen3-coder:latest')
})

test('supports manual selection only within exact role approvals', () => {
  assert.deepEqual(route('general', { preferredModel: 'qwen3:8b' }), {
    status: 'selected', role: 'general', model: 'qwen3:8b', family: 'qwen', selection: 'manual',
  })
  assert.deepEqual(route('coding', { preferredModel: 'gemma3:12b' }), {
    status: 'unavailable', reason: 'preferred_model_not_approved_and_installed_for_role',
  })
})

test('does not infer approval from an installed model name', () => {
  assert.equal(route('embedding').status, 'unavailable')
  assert.equal(route('image').status, 'unavailable')
  assert.equal(route('vision').status, 'unavailable')
})

test('does not substitute a different model for a missing manual choice', () => {
  assert.deepEqual(route('general', { preferredModel: 'qwen-does-not-exist:latest' }), {
    status: 'unavailable', reason: 'preferred_model_not_approved_and_installed_for_role',
  })
})

test('never selects an approved model that has not been discovered', () => {
  assert.equal(route('general', { discoveredModels: [{ name: 'other:latest' }] }).status, 'unavailable')
})

test('admin priority overrides family tie-breaker', () => {
  const result = route('reasoning', { approvedModels: [
    { name: 'gemma3:12b', family: 'gemma', roles: ['reasoning'], priority: 50 },
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['reasoning'], priority: 10 },
  ] })
  assert.equal(result.model, 'qwen3-coder:latest')
})

test('sort order is deterministic regardless of discovery or approval order', () => {
  const approved = [
    { name: 'qwen3:8b', family: 'qwen', roles: ['general'] },
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['general'] },
  ]
  const a = route('general', { approvedModels: approved })
  const b = route('general', { approvedModels: approved.reverse(), discoveredModels: [...discoveredModels].reverse() })
  assert.deepEqual(a, b)
})

test('rejects invalid roles and empty catalogs without inferring a default', () => {
  assert.deepEqual(route('administrator'), { status: 'invalid', reason: 'unsupported_role' })
  assert.equal(route('general', { approvedModels: [] }).status, 'unavailable')
  assert.equal(route('general', { discoveredModels: [] }).status, 'unavailable')
})

test('rejects invalid catalog shapes and duplicate discovered model identifiers', () => {
  assert.equal(route('general', { discoveredModels: 'gemma3:12b' }).reason, 'invalid_model_catalog')
  assert.equal(route('general', { discoveredModels: [{ name: 'gemma3:12b' }, { name: 'gemma3:12b' }] }).reason, 'invalid_discovered_model')
  assert.equal(route('general', { discoveredModels: [{ name: '../escape' }] }).reason, 'invalid_discovered_model')
})

test('rejects malformed or duplicate admin approval entries rather than selecting partial input', () => {
  assert.equal(route('general', { approvedModels: [approvedModels[0], approvedModels[0]] }).reason, 'invalid_model_approval')
  assert.equal(route('general', { approvedModels: [{ ...approvedModels[0], roles: ['general', 'general'] }] }).reason, 'invalid_model_approval')
  assert.equal(route('general', { approvedModels: [{ ...approvedModels[0], roles: ['unknown'] }] }).reason, 'invalid_model_approval')
  assert.equal(route('general', { approvedModels: [{ ...approvedModels[0], priority: -1 }] }).reason, 'invalid_model_approval')
  assert.equal(route('general', { approvedModels: [{ ...approvedModels[0], priority: 1.5 }] }).reason, 'invalid_model_approval')
})

test('rejects a manually selected unsafe or malformed model identifier', () => {
  assert.deepEqual(route('general', { preferredModel: '../other' }), { status: 'invalid', reason: 'invalid_preferred_model' })
  assert.equal(route('general', { preferredModel: '' }).status, 'invalid')
})

test('validates all approvals, even those for a different role or an uninstalled model', () => {
  assert.equal(route('general', { approvedModels: [approvedModels[0], { name: 'not-installed', family: 'qwen', roles: ['bad-role'] }] }).reason, 'invalid_model_approval')
})

test('does not perform discovery, inference, network access, or any I/O', () => {
  assert.equal(route('research').status, 'unavailable')
})
