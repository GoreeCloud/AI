/**
 * Development-only, side-effect-free model capability and resource fit check.
 * All model profiles and host snapshots must eventually come from approved
 * server-owned authorities. This module cannot authenticate or attest them.
 * It NEVER authorizes inference, model loading, tool use, or deployment.
 */
import { MODEL_ROLES } from './model-router.mjs'

const ROLE_SET = new Set(MODEL_ROLES)
const MODALITY_SET = new Set(['text', 'image', 'audio'])
const NAME = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/
const REV = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/
const ISO_UTC = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/
const ROOT = new Set(['selection', 'workload', 'approvedProfile', 'hostSnapshot', 'now'])
const SELECTION = new Set([
  'status', 'role', 'model', 'family', 'selection', 'policyRevision',
  'policyTrust', 'processingZone', 'inferenceAuthorized',
])
const WORKLOAD = new Set([
  'role', 'inputModalities', 'estimatedInputTokens', 'maxOutputTokens',
  'requiresToolCalling', 'processingZone',
])
const PROFILE = new Set([
  'source', 'revision', 'model', 'supportedRoles', 'inputModalities',
  'contextWindowTokens', 'estimatedResidentMemoryMiB', 'supportsToolCalling',
  'observedAt', 'expiresAt',
])
const SNAPSHOT = new Set([
  'source', 'availableMemoryMiB', 'safetyReserveMiB',
  'maxParallelRequests', 'activeRequests', 'observedAt', 'expiresAt',
])

const denied = reason => ({ status: 'blocked', reason, inferenceAuthorized: false })
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value)
const exact = (value, keys) => record(value) && Object.keys(value).every(key => keys.has(key))
const uint = (value, low, high) => Number.isSafeInteger(value) && value >= low && value <= high
const uniqueSubset = (array, allowed, max = 10) =>
  Array.isArray(array) && array.length > 0 && array.length <= max &&
  array.every(x => typeof x === 'string' && allowed.has(x)) &&
  new Set(array).size === array.length

function validWindow(observedAt, expiresAt, now, maxDuration) {
  if (typeof observedAt !== 'string' || typeof expiresAt !== 'string' ||
      !ISO_UTC.test(observedAt) || !ISO_UTC.test(expiresAt)) return false
  const observed = Date.parse(observedAt)
  const expires = Date.parse(expiresAt)
  return Number.isFinite(observed) && Number.isFinite(expires) &&
    observed <= now && expires > now && expires > observed &&
    expires - observed <= maxDuration
}

/**
 * Evaluate whether a Development preflight selection has an operator-declared
 * workload/profile/host fit. A positive result is ONLY a candidate for separate
 * real runtime validation, never proof of capability, capacity, or authorization.
 */
export function assessDevelopmentModelResourcePlan(input) {
  if (!exact(input, ROOT)) return denied('invalid_assessment_request')
  const { selection, workload, approvedProfile, hostSnapshot, now = Date.now() } = input
  if (!uint(now, 0, 8640000000000000)) return denied('invalid_assessment_clock')

  if (!exact(selection, SELECTION) || selection.status !== 'selected' ||
      !ROLE_SET.has(selection.role) || typeof selection.model !== 'string' ||
      !NAME.test(selection.model) || !['gemma', 'qwen', 'other'].includes(selection.family) ||
      !['automatic', 'manual'].includes(selection.selection) ||
      typeof selection.policyRevision !== 'string' || !REV.test(selection.policyRevision) ||
      selection.policyTrust !== 'development-unverified' ||
      selection.processingZone !== 'local-only-intended' ||
      selection.inferenceAuthorized !== false) return denied('invalid_preflight_selection')

  if (!exact(workload, WORKLOAD) || workload.role !== selection.role ||
      !uniqueSubset(workload.inputModalities, MODALITY_SET, 3) ||
      !uint(workload.estimatedInputTokens, 1, 131072) ||
      !uint(workload.maxOutputTokens, 1, 65536) ||
      typeof workload.requiresToolCalling !== 'boolean' ||
      workload.processingZone !== 'local-only') return denied('invalid_workload')

  if (!exact(approvedProfile, PROFILE) ||
      approvedProfile.source !== 'operator-reviewed-development' ||
      typeof approvedProfile.revision !== 'string' || !REV.test(approvedProfile.revision) ||
      approvedProfile.model !== selection.model ||
      !uniqueSubset(approvedProfile.supportedRoles, ROLE_SET, MODEL_ROLES.length) ||
      !approvedProfile.supportedRoles.includes(selection.role) ||
      !uniqueSubset(approvedProfile.inputModalities, MODALITY_SET, 3) ||
      !uint(approvedProfile.contextWindowTokens, 1, 1048576) ||
      !uint(approvedProfile.estimatedResidentMemoryMiB, 1, 1048576) ||
      typeof approvedProfile.supportsToolCalling !== 'boolean') {
    return denied('invalid_or_unmatched_development_profile')
  }
  if (!validWindow(approvedProfile.observedAt, approvedProfile.expiresAt,
                   now, 24 * 60 * 60 * 1000)) return denied('stale_development_profile')

  if (!exact(hostSnapshot, SNAPSHOT) ||
      hostSnapshot.source !== 'operator-observed-development' ||
      !uint(hostSnapshot.availableMemoryMiB, 0, 1048576) ||
      !uint(hostSnapshot.safetyReserveMiB, 0, 1048576) ||
      !uint(hostSnapshot.maxParallelRequests, 1, 1024) ||
      !uint(hostSnapshot.activeRequests, 0, 1024)) {
    return denied('invalid_development_host_snapshot')
  }
  if (!validWindow(hostSnapshot.observedAt, hostSnapshot.expiresAt,
                   now, 2 * 60 * 1000)) return denied('stale_development_host_snapshot')

  if (!workload.inputModalities.every(x => approvedProfile.inputModalities.includes(x))) {
    return denied('unsupported_declared_input_modality')
  }
  if (workload.requiresToolCalling && !approvedProfile.supportsToolCalling) {
    return denied('tool_calling_not_declared')
  }
  if (workload.estimatedInputTokens + workload.maxOutputTokens >
      approvedProfile.contextWindowTokens) return denied('declared_context_window_exceeded')

  if (hostSnapshot.activeRequests >= hostSnapshot.maxParallelRequests) {
    return denied('declared_parallel_capacity_exhausted')
  }
  if (approvedProfile.estimatedResidentMemoryMiB + hostSnapshot.safetyReserveMiB >
      hostSnapshot.availableMemoryMiB) return denied('declared_memory_budget_exceeded')

  return {
    status: 'candidate', model: selection.model, role: selection.role,
    profileRevision: approvedProfile.revision,
    fit: 'operator-declared-estimate-only',
    profileTrust: 'development-unverified',
    capacityTrust: 'development-unverified',
    inferenceAuthorized: false,
    toolExecutionAuthorized: false,
    runtimeValidated: false,
  }
}
