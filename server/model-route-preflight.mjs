/**
 * Development-only backend seam for approved local model-role routing.
 *
 * The caller provides backend-owned policy and discovery adapters. This module
 * does not expose HTTP routes, read caller-supplied approvals, call inference,
 * or confer Identity, Privacy Shield, Policy, or runtime authorization.
 * The existing chat endpoint remains unchanged until separately accepted.
 */
import { MODEL_ROLES, selectApprovedModel } from './model-router.mjs'

const ROLES = new Set(MODEL_ROLES)
const REVISION = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/
const MODEL_NAME = /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$/
const ISO_UTC = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/
const POLICY_FIELDS = new Set(['source', 'revision', 'observedAt', 'expiresAt', 'approvedModels'])
const REQUEST_FIELDS = new Set(['role', 'preferredModel', 'signal'])
const MAX_APPROVED_MODELS = 128
const MAX_DISCOVERED_MODELS = 512
const MAX_POLICY_LIFETIME_MS = 24 * 60 * 60 * 1000

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function onlyKeys(value, allowed) {
  return Object.keys(value).every((key) => allowed.has(key))
}

function outcome(status, reason) {
  return { status, reason }
}

function utcTimestamp(value) {
  if (typeof value !== 'string' || !ISO_UTC.test(value)) return NaN
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : NaN
}

function parsePolicy(snapshot, now) {
  if (!record(snapshot) || !onlyKeys(snapshot, POLICY_FIELDS) ||
      snapshot.source !== 'server-local-config' ||
      typeof snapshot.revision !== 'string' || !REVISION.test(snapshot.revision) ||
      !Array.isArray(snapshot.approvedModels) ||
      snapshot.approvedModels.length > MAX_APPROVED_MODELS) {
    return outcome('unavailable', 'invalid_server_model_policy')
  }

  const observed = utcTimestamp(snapshot.observedAt)
  const expires = utcTimestamp(snapshot.expiresAt)
  if (!Number.isFinite(observed) || !Number.isFinite(expires) ||
      observed > now || expires <= observed ||
      expires - observed > MAX_POLICY_LIFETIME_MS) {
    return outcome('unavailable', 'invalid_server_model_policy')
  }
  if (expires <= now) return outcome('unavailable', 'expired_server_model_policy')

  return { status: 'valid', approvedModels: snapshot.approvedModels, revision: snapshot.revision }
}

class BoundError extends Error {
  constructor(reason) {
    super(reason)
    this.reason = reason
  }
}

async function boundedCall(callback, signal, timeoutMs) {
  if (signal?.aborted) throw new BoundError('cancelled')
  const controller = new AbortController()
  let timer
  let onAbort
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => {
      controller.abort()
      reject(new BoundError('timeout'))
    }, timeoutMs)
  })
  const cancellation = new Promise((_, reject) => {
    if (!signal) return
    onAbort = () => {
      controller.abort()
      reject(new BoundError('cancelled'))
    }
    signal.addEventListener('abort', onAbort, { once: true })
    if (signal.aborted) onAbort()
  })
  try {
    return await Promise.race([
      Promise.resolve().then(() => callback({ signal: controller.signal })),
      timeout,
      cancellation,
    ])
  } finally {
    clearTimeout(timer)
    if (onAbort) signal.removeEventListener('abort', onAbort)
    controller.abort()
  }
}

/**
 * Build a preflight function with server-owned adapters. Do not pass these
 * adapters through a user request or derive them from model output.
 *
 * loadPolicy() must read a trusted server-side policy in the eventual runtime
 * integration. `source` is a structural label, not proof of authenticity.
 * Current output is deliberately marked development-only.
 */
export function createModelRoutePreflight({ loadPolicy, discoverModels, timeoutMs = 3_000, now = Date.now } = {}) {
  if (typeof loadPolicy !== 'function' || typeof discoverModels !== 'function' ||
      typeof now !== 'function' || !Number.isSafeInteger(timeoutMs) ||
      timeoutMs < 1 || timeoutMs > 30_000) {
    throw new TypeError('Valid backend adapters and a bounded timeout are required')
  }

  return async function preflight(request) {
    if (!record(request) || !onlyKeys(request, REQUEST_FIELDS) || !ROLES.has(request.role) ||
        (request.preferredModel !== undefined &&
         (typeof request.preferredModel !== 'string' || !MODEL_NAME.test(request.preferredModel))) ||
        (request.signal !== undefined && !(request.signal instanceof AbortSignal))) {
      return outcome('invalid', 'invalid_routing_request')
    }
    const { role, preferredModel, signal } = request
    if (signal?.aborted) return outcome('cancelled', 'request_cancelled')

    let policySnapshot
    try {
      policySnapshot = await boundedCall(loadPolicy, signal, timeoutMs)
    } catch (error) {
      return error instanceof BoundError
        ? outcome(error.reason === 'cancelled' ? 'cancelled' : 'unavailable',
            error.reason === 'cancelled' ? 'request_cancelled' : 'policy_timeout')
        : outcome('unavailable', 'server_model_policy_unavailable')
    }
    const currentTime = now()
    if (!Number.isSafeInteger(currentTime) || currentTime < 0) {
      return outcome('unavailable', 'invalid_server_clock')
    }
    const policy = parsePolicy(policySnapshot, currentTime)
    if (policy.status !== 'valid') return policy
    if (signal?.aborted) return outcome('cancelled', 'request_cancelled')

    let discovered
    try {
      discovered = await boundedCall(discoverModels, signal, timeoutMs)
    } catch (error) {
      return error instanceof BoundError
        ? outcome(error.reason === 'cancelled' ? 'cancelled' : 'unavailable',
            error.reason === 'cancelled' ? 'request_cancelled' : 'model_discovery_timeout')
        : outcome('unavailable', 'model_discovery_unavailable')
    }
    if (!Array.isArray(discovered) || discovered.length > MAX_DISCOVERED_MODELS || signal?.aborted) {
      return signal?.aborted
        ? outcome('cancelled', 'request_cancelled')
        : outcome('unavailable', 'invalid_model_discovery_result')
    }
    const selected = selectApprovedModel({
      role, discoveredModels: discovered,
      approvedModels: policy.approvedModels, preferredModel,
    })
    if (selected.status === 'invalid') return outcome('unavailable', 'invalid_server_model_catalog')
    if (selected.status !== 'selected') return selected
    return {
      ...selected,
      policyRevision: policy.revision,
      policyTrust: 'development-unverified',
      processingZone: 'local-only-intended',
      inferenceAuthorized: false,
    }
  }
}
