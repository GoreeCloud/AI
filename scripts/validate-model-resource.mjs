/**
 * Explicit development-only local model resource diagnostic. Never run inference.
 * It uses a private local policy and profile; reads only loopback Ollama tags;
 * samples host available system RAM. No HTTP route, tool access or deployment.
 */
import { isAbsolute } from 'node:path'
import { freemem } from 'node:os'
import { createLocalPolicyLoader, createLoopbackModelDiscovery } from '../server/model-local-adapters.mjs'
import { createModelRoutePreflight } from '../server/model-route-preflight.mjs'
import { assessDevelopmentModelResourcePlan } from '../server/model-resource-readiness.mjs'

function emit(status, reason, extra = {}) {
  process.stdout.write(JSON.stringify({ status, ...(reason ? { reason } : {}), ...extra }) + '\n')
  process.exitCode = status === 'candidate' ? 0 : 2
}

const env = process.env
const positiveInt = raw => typeof raw === 'string' && /^[1-9][0-9]*$/.test(raw) &&
  Number.isSafeInteger(Number(raw)) ? Number(raw) : null
const nonnegativeInt = raw => typeof raw === 'string' && /^(?:0|[1-9][0-9]*)$/.test(raw) &&
  Number.isSafeInteger(Number(raw)) ? Number(raw) : null
const timeout = env.VALIDATE_RESOURCE_TIMEOUT_MS === undefined ? 5000 : positiveInt(env.VALIDATE_RESOURCE_TIMEOUT_MS)
const inputTokens = positiveInt(env.VALIDATE_RESOURCE_INPUT_TOKENS ?? '2048')
const outputTokens = positiveInt(env.VALIDATE_RESOURCE_OUTPUT_TOKENS ?? '1024')
const reserveMiB = nonnegativeInt(env.VALIDATE_RESOURCE_SAFETY_RESERVE_MIB ?? '1024')
const active = nonnegativeInt(env.VALIDATE_RESOURCE_ACTIVE_REQUESTS ?? '0')
const maxParallel = positiveInt(env.VALIDATE_RESOURCE_MAX_PARALLEL ?? '1')

if (process.argv.length !== 2 || env.VALIDATE_MODEL_RESOURCE !== 'local-development-only') {
  emit('invalid', 'explicit_local_development_opt_in_required')
} else if (!env.VALIDATE_MODEL_POLICY_PATH || !isAbsolute(env.VALIDATE_MODEL_POLICY_PATH) ||
           !env.VALIDATE_MODEL_PROFILE_PATH || !isAbsolute(env.VALIDATE_MODEL_PROFILE_PATH) ||
           !env.VALIDATE_MODEL_ROLE || timeout === null || timeout > 30000 ||
           inputTokens === null || inputTokens > 131072 ||
           outputTokens === null || outputTokens > 65536 ||
           reserveMiB === null || reserveMiB > 1048576 ||
           active === null || active > 1024 ||
           maxParallel === null || maxParallel > 1024) {
  emit('invalid', 'invalid_local_resource_configuration')
} else {
  try {
    const prepare = createModelRoutePreflight({
      loadPolicy: createLocalPolicyLoader({ policyPath: env.VALIDATE_MODEL_POLICY_PATH }),
      discoverModels: createLoopbackModelDiscovery({
        baseUrl: env.VALIDATE_MODEL_RUNTIME_URL ?? 'http://127.0.0.1:11434',
      }),
      timeoutMs: timeout,
    })
    const selection = await prepare({
      role: env.VALIDATE_MODEL_ROLE,
      ...(env.VALIDATE_MODEL_PREFERRED ? { preferredModel: env.VALIDATE_MODEL_PREFERRED } : {}),
    })
    if (selection.status !== 'selected') {
      emit(selection.status, selection.reason)
    } else {
      let profile
      try {
        profile = await createLocalPolicyLoader({ policyPath: env.VALIDATE_MODEL_PROFILE_PATH })()
      } catch {
        emit('unavailable', 'local_development_profile_unavailable')
      }
      if (profile !== undefined) {
        const now = Date.now()
        const freeMiB = Math.floor(freemem() / 1048576)
        const result = assessDevelopmentModelResourcePlan({
          selection,
          workload: {
            role: env.VALIDATE_MODEL_ROLE,
            inputModalities: ['text'],
            estimatedInputTokens: inputTokens,
            maxOutputTokens: outputTokens,
            requiresToolCalling: false,
            processingZone: 'local-only',
          },
          approvedProfile: profile,
          hostSnapshot: {
            source: 'operator-observed-development',
            availableMemoryMiB: freeMiB,
            safetyReserveMiB: reserveMiB,
            maxParallelRequests: maxParallel,
            activeRequests: active,
            observedAt: new Date(now).toISOString(),
            expiresAt: new Date(now + 60000).toISOString(),
          },
          now,
        })
        if (result.status === 'candidate') {
          emit('candidate', undefined, {
            model: result.model, role: result.role,
            profileRevision: result.profileRevision,
            fit: result.fit, profileTrust: result.profileTrust,
            capacityTrust: result.capacityTrust,
            runtimeValidated: false, inferenceAuthorized: false,
            toolExecutionAuthorized: false,
          })
        } else {
          emit(result.status, result.reason)
        }
      }
    }
  } catch {
    // No private file contents, configured paths, exceptions, or runtime bodies.
    emit('unavailable', 'local_resource_diagnostic_unavailable')
  }
}
