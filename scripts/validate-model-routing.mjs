/**
 * Explicit, operator-initiated Development diagnostic for the local model router.
 * This script reads a protected policy file and calls only loopback /api/tags.
 * It does not run inference, expose an HTTP API, or authorize a model request.
 */
import { isAbsolute } from 'node:path'
import { createLocalPolicyLoader, createLoopbackModelDiscovery } from '../server/model-local-adapters.mjs'
import { createModelRoutePreflight } from '../server/model-route-preflight.mjs'

function emit(status, reason, extra = {}) {
  const message = { status, ...(reason ? { reason } : {}), ...extra }
  process.stdout.write(JSON.stringify(message) + '\n')
  process.exitCode = status === 'selected' ? 0 : 2
}

const env = process.env
const hasArgs = process.argv.length !== 2
const timeoutRaw = env.VALIDATE_MODEL_TIMEOUT_MS
const timeoutMs = timeoutRaw === undefined ? 5000 : Number(timeoutRaw)

if (hasArgs || env.VALIDATE_MODEL_ROUTING !== 'local-development-only') {
  emit('invalid', 'explicit_local_development_opt_in_required')
} else if (!env.VALIDATE_MODEL_POLICY_PATH || !isAbsolute(env.VALIDATE_MODEL_POLICY_PATH) ||
           !env.VALIDATE_MODEL_ROLE ||
           (timeoutRaw !== undefined && !/^[1-9][0-9]*$/.test(timeoutRaw)) ||
           !Number.isSafeInteger(timeoutMs) || timeoutMs > 30000) {
  emit('invalid', 'invalid_local_diagnostic_configuration')
} else {
  try {
    const loadPolicy = createLocalPolicyLoader({
      policyPath: env.VALIDATE_MODEL_POLICY_PATH,
    })
    const discoverModels = createLoopbackModelDiscovery({
      baseUrl: env.VALIDATE_MODEL_RUNTIME_URL ?? 'http://127.0.0.1:11434',
    })
    const prepare = createModelRoutePreflight({
      loadPolicy, discoverModels, timeoutMs,
    })
    const result = await prepare({
      role: env.VALIDATE_MODEL_ROLE,
      ...(env.VALIDATE_MODEL_PREFERRED
        ? { preferredModel: env.VALIDATE_MODEL_PREFERRED } : {}),
    })
    if (result.status === 'selected') {
      emit('selected', undefined, {
        role: result.role,
        model: result.model,
        family: result.family,
        selection: result.selection,
        policyRevision: result.policyRevision,
        policyTrust: result.policyTrust,
        processingZone: result.processingZone,
        inferenceAuthorized: false,
      })
    } else {
      // Reason codes only. Never print policy bytes, paths or upstream bodies.
      emit(result.status, result.reason)
    }
  } catch {
    emit('unavailable', 'local_diagnostic_configuration_unavailable')
  }
}
