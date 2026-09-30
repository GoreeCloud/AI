import test from 'node:test'
import assert from 'node:assert/strict'
import { assessDevelopmentModelResourcePlan as assess } from './model-resource-readiness.mjs'

const NOW = Date.parse('2026-09-23T12:00:00Z')
const selection = {
  status: 'selected', role: 'coding', model: 'qwen3-coder:latest', family: 'qwen',
  selection: 'automatic', policyRevision: 'dev:1', policyTrust: 'development-unverified',
  processingZone: 'local-only-intended', inferenceAuthorized: false,
}
const workload = {
  role: 'coding', inputModalities: ['text'], estimatedInputTokens: 2048,
  maxOutputTokens: 1024, requiresToolCalling: false, processingZone: 'local-only',
}
const approvedProfile = {
  source: 'operator-reviewed-development', revision: 'dev:profile1',
  model: 'qwen3-coder:latest', supportedRoles: ['coding'], inputModalities: ['text'],
  contextWindowTokens: 8192, estimatedResidentMemoryMiB: 8192,
  supportsToolCalling: false, observedAt: '2026-09-23T11:00:00Z',
  expiresAt: '2026-09-23T13:00:00Z',
}
const hostSnapshot = {
  source: 'operator-observed-development', availableMemoryMiB: 12288,
  safetyReserveMiB: 1024, maxParallelRequests: 2, activeRequests: 0,
  observedAt: '2026-09-23T11:59:00Z', expiresAt: '2026-09-23T12:01:00Z',
}
const run = patch => assess({ selection, workload, approvedProfile, hostSnapshot, now: NOW, ...patch })
const denied = (result, reason) => {
  assert.deepEqual(result, { status: 'blocked', reason, inferenceAuthorized: false })
}
test('positive fit remains explicitly non-authorizing and unverified', () => {
  const result = run()
  assert.deepEqual(result, {
    status: 'candidate', model: 'qwen3-coder:latest', role: 'coding',
    profileRevision: 'dev:profile1', fit: 'operator-declared-estimate-only',
    profileTrust: 'development-unverified', capacityTrust: 'development-unverified',
    inferenceAuthorized: false, toolExecutionAuthorized: false, runtimeValidated: false,
  })
})
test('rejects malformed or unexpected top-level request fields', () => {
  denied(assess(null), 'invalid_assessment_request')
  denied(run({ clientApproved: true }), 'invalid_assessment_request')
})
test('rejects forged authority and wrong preflight processing zone', () => {
  for (const patch of [
    { inferenceAuthorized: true }, { policyTrust: 'production-trusted' },
    { processingZone: 'external' }, { status: 'unavailable' },
    { model: '../bad' }, { selection: 'manual-override' },
  ]) denied(run({ selection: { ...selection, ...patch } }), 'invalid_preflight_selection')
})
test('rejects malformed and extra preflight properties', () => {
  denied(run({ selection: { ...selection, secret: true } }), 'invalid_preflight_selection')
  denied(run({ selection: { ...selection, policyRevision: '' } }), 'invalid_preflight_selection')
})
test('prevents cross-role and external workload substitution', () => {
  for (const patch of [
    { role: 'general' }, { processingZone: 'external' },
    { estimatedInputTokens: -1 }, { maxOutputTokens: 1.2 },
    { inputModalities: ['text', 'text'] }, { requiresToolCalling: 'true' },
  ]) denied(run({ workload: { ...workload, ...patch } }), 'invalid_workload')
})
test('disallows unexpected workload fields', () => {
  denied(run({ workload: { ...workload, adminApproval: true } }), 'invalid_workload')
})
test('profile must be operator-declared, exact-model matched and role listed', () => {
  for (const patch of [
    { source: 'runtime-advertised' }, { model: 'qwen3:8b' },
    { supportedRoles: ['general'] }, { supportedRoles: ['coding', 'coding'] },
    { inputModalities: [] }, { contextWindowTokens: 0 },
    { estimatedResidentMemoryMiB: -1 }, { supportsToolCalling: null },
  ]) denied(run({ approvedProfile: { ...approvedProfile, ...patch } }),
             'invalid_or_unmatched_development_profile')
})
test('rejects unknown profile fields, even if otherwise valid', () => {
  denied(run({ approvedProfile: { ...approvedProfile, unrestricted: true } }),
         'invalid_or_unmatched_development_profile')
})
test('rejects expired, future-dated, invalid-lifetime profile snapshots', () => {
  for (const patch of [
    { expiresAt: '2026-09-23T12:00:00Z' },
    { observedAt: '2026-09-23T12:10:00Z', expiresAt: '2026-09-23T13:00:00Z' },
    { observedAt: '2026-09-22T10:00:00Z', expiresAt: '2026-09-23T13:00:00Z' },
    { observedAt: 'broken' },
  ]) denied(run({ approvedProfile: { ...approvedProfile, ...patch } }),
             'stale_development_profile')
})
test('rejects invalid host budget, congestion and untrusted source metadata', () => {
  for (const patch of [
    { source: 'client-reported' }, { availableMemoryMiB: -1 },
    { safetyReserveMiB: NaN }, { maxParallelRequests: 0 },
    { activeRequests: 2.1 }, { speculativeCapacity: true },
  ]) denied(run({ hostSnapshot: { ...hostSnapshot, ...patch } }),
             'invalid_development_host_snapshot')
})
test('rejects expired, future-dated and overlong host snapshots', () => {
  for (const patch of [
    { expiresAt: '2026-09-23T12:00:00Z' },
    { observedAt: '2026-09-23T12:01:00Z', expiresAt: '2026-09-23T12:02:00Z' },
    { observedAt: '2026-09-23T11:00:00Z', expiresAt: '2026-09-23T12:01:00Z' },
  ]) denied(run({ hostSnapshot: { ...hostSnapshot, ...patch } }),
             'stale_development_host_snapshot')
})
test('does not infer image or audio support from model names', () => {
  denied(run({ workload: { ...workload, inputModalities: ['image'] } }),
         'unsupported_declared_input_modality')
  denied(run({ workload: { ...workload, inputModalities: ['audio'] } }),
         'unsupported_declared_input_modality')
})
test('requires explicitly declared tool calling yet never authorizes it', () => {
  denied(run({ workload: { ...workload, requiresToolCalling: true } }),
         'tool_calling_not_declared')
  const result = run({
    workload: { ...workload, requiresToolCalling: true },
    approvedProfile: { ...approvedProfile, supportsToolCalling: true },
  })
  assert.equal(result.status, 'candidate')
  assert.equal(result.toolExecutionAuthorized, false)
})
test('rejects context overflow with input and reserved output tokens combined', () => {
  denied(run({ workload: { ...workload, estimatedInputTokens: 7500 } }),
         'declared_context_window_exceeded')
  assert.equal(run({ workload: { ...workload, estimatedInputTokens: 7168 } }).status, 'candidate')
})
test('rejects parallel request exhaustion and memory deficits including reserve', () => {
  denied(run({ hostSnapshot: { ...hostSnapshot, activeRequests: 2 } }),
         'declared_parallel_capacity_exhausted')
  denied(run({ hostSnapshot: { ...hostSnapshot, availableMemoryMiB: 9215 } }),
         'declared_memory_budget_exceeded')
  assert.equal(run({ hostSnapshot: { ...hostSnapshot, availableMemoryMiB: 9216 } }).status, 'candidate')
})
test('rejects invalid assessment clocks rather than accepting stale state', () => {
  for (const now of [NaN, Infinity, -1, '2026-09-23T12:00:00Z']) {
    denied(run({ now }), 'invalid_assessment_clock')
  }
})
