import test from 'node:test'
import assert from 'node:assert/strict'
import { createModelRoutePreflight } from './model-route-preflight.mjs'

const NOW = Date.parse('2026-09-23T09:00:00Z')
const approval = Object.freeze([
  { name: 'gemma3:12b', family: 'gemma', roles: ['general', 'reasoning', 'writing'] },
  { name: 'qwen3-coder:latest', family: 'qwen', roles: ['coding', 'reasoning', 'agent'] },
  { name: 'qwen3:8b', family: 'qwen', roles: ['general', 'fast'] },
])
const policy = () => ({
  source: 'server-local-config', revision: 'dev:1',
  observedAt: '2026-09-23T08:59:00Z', expiresAt: '2026-09-23T09:59:00Z',
  approvedModels: approval,
})
const models = () => [
  { name: 'gemma3:12b' }, { name: 'qwen3-coder:latest' }, { name: 'qwen3:8b' },
]
const build = (overrides = {}) => createModelRoutePreflight({
  loadPolicy: async () => policy(), discoverModels: async () => models(),
  now: () => NOW, timeoutMs: 500, ...overrides,
})

test('selects only an approved installed model and marks result non-authorizing', async () => {
  const selected = await build()({ role: 'general' })
  assert.deepEqual(selected, {
    status: 'selected', role: 'general', model: 'gemma3:12b', family: 'gemma',
    selection: 'automatic', policyRevision: 'dev:1',
    policyTrust: 'development-unverified', processingZone: 'local-only-intended',
    inferenceAuthorized: false,
  })
})

test('prefers Qwen only when approved for the requested coding role', async () => {
  assert.equal((await build()({ role: 'coding' })).model, 'qwen3-coder:latest')
})

test('manual selection cannot bypass explicit role assignment', async () => {
  const denied = await build()({ role: 'coding', preferredModel: 'gemma3:12b' })
  assert.equal(denied.status, 'unavailable')
  assert.equal(denied.reason, 'preferred_model_not_approved_and_installed_for_role')
  assert.equal((await build()({ role: 'general', preferredModel: 'qwen3:8b' })).model, 'qwen3:8b')
})

test('rejects request-provided approvals, extraneous fields, or malformed signals before loading policy', async () => {
  let reads = 0
  const prepare = build({ loadPolicy: async () => { reads++; return policy() } })
  assert.equal((await prepare({ role: 'general', approvedModels: approval })).status, 'invalid')
  assert.equal((await prepare({ role: 'general', signal: {} })).status, 'invalid')
  assert.equal((await prepare({ role: 'bad-role' })).status, 'invalid')
  assert.equal((await prepare({ role: 'general', preferredModel: '../bad' })).status, 'invalid')
  assert.equal(reads, 0)
})

test('never discovers models if the server policy source is invalid', async () => {
  let discoveries = 0
  const prepare = build({
    loadPolicy: async () => ({ ...policy(), source: 'client-supplied' }),
    discoverModels: async () => { discoveries++; return models() },
  })
  assert.deepEqual(await prepare({ role: 'general' }), { status: 'unavailable', reason: 'invalid_server_model_policy' })
  assert.equal(discoveries, 0)
})

test('rejects unrecognized policy envelope fields', async () => {
  const prepare = build({ loadPolicy: async () => ({ ...policy(), extra: true }) })
  assert.equal((await prepare({ role: 'general' })).reason, 'invalid_server_model_policy')
})

test('rejects expired, future-dated, excessive-lifetime and malformed server policy', async () => {
  for (const patch of [
    { expiresAt: '2026-09-23T08:59:30Z' },
    { observedAt: '2026-09-23T10:00:00Z', expiresAt: '2026-09-23T10:01:00Z' },
    { observedAt: '2026-09-23T08:00:00Z', expiresAt: '2026-09-25T08:00:00Z' },
    { observedAt: 'not-a-date' },
  ]) {
    const result = await build({ loadPolicy: async () => ({ ...policy(), ...patch }) })({ role: 'general' })
    assert.equal(result.status, 'unavailable')
  }
})

test('expires exactly at the evaluation clock and rejects stale policy', async () => {
  const prepare = build({ loadPolicy: async () => ({ ...policy(), expiresAt: '2026-09-23T09:00:00Z' }) })
  assert.equal((await prepare({ role: 'general' })).reason, 'expired_server_model_policy')
})

test('fails closed when policy or model discovery throws, without exposing exception details', async () => {
  const p = await build({ loadPolicy: async () => { throw new Error('credential=secret') } })({ role: 'general' })
  const d = await build({ discoverModels: async () => { throw new Error('internal network details') } })({ role: 'general' })
  assert.deepEqual(p, { status: 'unavailable', reason: 'server_model_policy_unavailable' })
  assert.deepEqual(d, { status: 'unavailable', reason: 'model_discovery_unavailable' })
})

test('times out ignored abort during policy retrieval', async () => {
  const start = Date.now()
  const prepare = build({ loadPolicy: () => new Promise(() => {}), timeoutMs: 15 })
  assert.deepEqual(await prepare({ role: 'general' }), { status: 'unavailable', reason: 'policy_timeout' })
  assert.ok(Date.now() - start < 1000)
})

test('times out ignored abort during model discovery', async () => {
  const prepare = build({ discoverModels: () => new Promise(() => {}), timeoutMs: 15 })
  assert.deepEqual(await prepare({ role: 'coding' }), { status: 'unavailable', reason: 'model_discovery_timeout' })
})

test('rejects pre-aborted requests without calling any adapters', async () => {
  const controller = new AbortController(); controller.abort()
  let called = false
  const prepare = build({ loadPolicy: async () => { called = true; return policy() } })
  assert.deepEqual(await prepare({ role: 'general', signal: controller.signal }), { status: 'cancelled', reason: 'request_cancelled' })
  assert.equal(called, false)
})

test('aborts in-progress discovery even when the adapter ignores its signal', async () => {
  const controller = new AbortController()
  const prepare = build({
    discoverModels: async () => {
      queueMicrotask(() => controller.abort())
      return new Promise(() => {})
    },
  })
  assert.deepEqual(await prepare({ role: 'general', signal: controller.signal }), { status: 'cancelled', reason: 'request_cancelled' })
})

test('returns unavailable for unapproved or undiscovered roles without a fallback', async () => {
  assert.equal((await build()({ role: 'embedding' })).status, 'unavailable')
  assert.equal((await build({ discoverModels: async () => [] })({ role: 'general' })).status, 'unavailable')
})

test('rejects oversize and malformed discovery, even if valid model is present', async () => {
  const huge = models().concat(Array.from({ length: 511 }, (_, i) => ({ name: `unapproved-${i}` })))
  assert.equal((await build({ discoverModels: async () => huge })({ role: 'general' })).reason, 'invalid_model_discovery_result')
  assert.equal((await build({ discoverModels: async () => [{ name: 'gemma3:12b' }, { name: '../other' }] })({ role: 'general' })).reason, 'invalid_server_model_catalog')
})

test('rejects invalid server clock rather than incorrectly accepting stale policy', async () => {
  assert.deepEqual(await build({ now: () => Number.NaN })({ role: 'general' }), { status: 'unavailable', reason: 'invalid_server_clock' })
})

test('factory rejects missing adapters and unsafe timeouts', () => {
  assert.throws(() => createModelRoutePreflight({}), TypeError)
  assert.throws(() => build({ timeoutMs: 0 }), TypeError)
  assert.throws(() => build({ timeoutMs: 30001 }), TypeError)
})
