/**
 * Operator-initiated Development-only validation of one approved model through
 * the existing GoreeCloud AI application path. This script does not alter the
 * backend, grant product authorization, load models, or establish production
 * acceptance. Generated model content is never printed.
 */
import { isAbsolute } from 'node:path'
import { createLocalPolicyLoader } from '../server/model-local-adapters.mjs'
import { createModelRoutePreflight } from '../server/model-route-preflight.mjs'

const MAX_JSON_BYTES = 256 * 1024
const MAX_STREAM_BYTES = 1024 * 1024
const MAX_STREAM_EVENTS = 2048
const FIXED_PROMPT = 'Respond briefly to confirm local runtime validation.'

class SafeFailure extends Error {
  constructor(reason) {
    super(reason)
    this.reason = reason
  }
}

function emit(status, reason, extra = {}) {
  process.stdout.write(JSON.stringify({ status, ...(reason ? { reason } : {}), ...extra }) + '\n')
  process.exitCode = status === 'validated' ? 0 : 2
}

function positiveInt(raw, fallback) {
  if (raw === undefined) return fallback
  if (typeof raw !== 'string' || !/^[1-9][0-9]*$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) ? value : null
}

function validateLoopbackApplicationUrl(raw) {
  if (typeof raw !== 'string') throw new SafeFailure('invalid_local_application_url')
  let url
  try { url = new URL(raw) } catch { throw new SafeFailure('invalid_local_application_url') }
  if (url.protocol !== 'http:' || !['127.0.0.1', '[::1]'].includes(url.hostname) ||
      (url.pathname !== '/' && url.pathname !== '') || url.username || url.password ||
      url.search || url.hash ||
      (url.port && (!Number.isSafeInteger(Number(url.port)) || Number(url.port) < 1 || Number(url.port) > 65535))) {
    throw new SafeFailure('invalid_local_application_url')
  }
  return url
}

async function withTimeout(timeoutMs, task) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await task(controller.signal)
  } catch (error) {
    if (controller.signal.aborted) throw new SafeFailure('runtime_validation_timeout')
    throw error
  } finally {
    clearTimeout(timer)
  }
}

async function readBoundedText(response, maxBytes, signal) {
  if (!response.body || typeof response.body.getReader !== 'function') throw new SafeFailure('invalid_application_response')
  const advertised = response.headers.get('content-length')
  if (advertised !== null && (!/^\d+$/.test(advertised) || Number(advertised) > maxBytes)) {
    await response.body.cancel().catch(() => {})
    throw new SafeFailure('application_response_exceeds_limit')
  }
  const reader = response.body.getReader()
  const chunks = []
  let total = 0
  try {
    while (true) {
      if (signal?.aborted) throw new SafeFailure('runtime_validation_timeout')
      const { done, value } = await reader.read()
      if (done) break
      if (!(value instanceof Uint8Array)) throw new SafeFailure('invalid_application_response')
      total += value.byteLength
      if (total > maxBytes) throw new SafeFailure('application_response_exceeds_limit')
      chunks.push(value)
    }
  } catch (error) {
    await reader.cancel().catch(() => {})
    throw error
  } finally {
    reader.releaseLock()
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks))
  } catch {
    throw new SafeFailure('invalid_application_response')
  }
}

async function fetchJson(url, { headers = {}, signal } = {}) {
  let response
  try {
    response = await fetch(url, {
      method: 'GET', headers: { Accept: 'application/json', ...headers },
      redirect: 'error', credentials: 'omit', signal,
    })
  } catch {
    throw new SafeFailure('application_request_failed')
  }
  if (!response.ok) {
    await response.body?.cancel().catch(() => {})
    throw new SafeFailure('application_request_failed')
  }
  const text = await readBoundedText(response, MAX_JSON_BYTES, signal)
  try { return text ? JSON.parse(text) : null }
  catch { throw new SafeFailure('invalid_application_response') }
}

function installedModels(payload) {
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload) ||
      !Array.isArray(payload.models) || payload.models.length > 512) {
    throw new SafeFailure('invalid_model_discovery_result')
  }
  return payload.models.map(entry => ({ name: entry?.name ?? entry?.model }))
}

async function validateStream(url, { model, headers, timeoutMs }) {
  return withTimeout(timeoutMs, async signal => {
    let response
    const started = Date.now()
    try {
      response = await fetch(url, {
        method: 'POST', redirect: 'error', credentials: 'omit', signal,
        headers: { ...headers, 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
        body: JSON.stringify({ model, messages: [{ role: 'user', content: FIXED_PROMPT }] }),
      })
    } catch {
      throw new SafeFailure('stream_request_failed')
    }
    if (!response.ok || !response.body || typeof response.body.getReader !== 'function') {
      await response.body?.cancel().catch(() => {})
      throw new SafeFailure('stream_request_failed')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: true })
    let buffer = ''
    let bytes = 0
    let events = 0
    let contentChunks = 0
    let contentBytes = 0
    let doneSeen = false

    function acceptLine(line) {
      if (!line.trim()) return
      events += 1
      if (events > MAX_STREAM_EVENTS) throw new SafeFailure('stream_event_limit_exceeded')
      let event
      try { event = JSON.parse(line) } catch { throw new SafeFailure('invalid_stream_event') }
      if (event === null || typeof event !== 'object' || Array.isArray(event) || event.error !== undefined) {
        throw new SafeFailure('invalid_stream_event')
      }
      if (typeof event?.message?.content === 'string' && event.message.content.length > 0) {
        contentChunks += 1
        contentBytes += Buffer.byteLength(event.message.content, 'utf8')
      }
      if (event.done === true) doneSeen = true
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        if (!(value instanceof Uint8Array)) throw new SafeFailure('invalid_stream_event')
        bytes += value.byteLength
        if (bytes > MAX_STREAM_BYTES) throw new SafeFailure('stream_response_exceeds_limit')
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) acceptLine(line)
      }
      buffer += decoder.decode()
      if (buffer.trim()) acceptLine(buffer)
    } catch (error) {
      await reader.cancel().catch(() => {})
      throw error
    } finally {
      reader.releaseLock()
    }

    if (contentChunks < 1) throw new SafeFailure('stream_missing_assistant_content')
    if (!doneSeen) throw new SafeFailure('stream_missing_terminal_event')
    return {
      contentChunks, contentBytes, streamEvents: events, responseBytes: bytes,
      elapsedMs: Math.max(0, Date.now() - started),
    }
  })
}

const env = process.env
const timeoutMs = positiveInt(env.VALIDATE_APPROVED_MODEL_RUNTIME_TIMEOUT_MS, 30_000)

if (process.argv.length !== 2 || env.VALIDATE_APPROVED_MODEL_RUNTIME !== 'local-development-only') {
  emit('invalid', 'explicit_local_development_opt_in_required')
} else if (!env.VALIDATE_MODEL_POLICY_PATH || !isAbsolute(env.VALIDATE_MODEL_POLICY_PATH) ||
           !env.VALIDATE_MODEL_ROLE || !env.VALIDATE_MODEL_PREFERRED ||
           timeoutMs === null || timeoutMs > 120_000) {
  emit('invalid', 'invalid_local_runtime_validation_configuration')
} else {
  try {
    const base = validateLoopbackApplicationUrl(env.GOREECLOUD_AI_URL ?? 'http://127.0.0.1:8787')
    const headers = env.GOREECLOUD_AI_API_TOKEN?.trim()
      ? { Authorization: `Bearer ${env.GOREECLOUD_AI_API_TOKEN.trim()}` }
      : {}
    const healthUrl = new URL('/api/health', base)
    const modelsUrl = new URL('/api/ollama/models', base)
    const chatUrl = new URL('/api/ollama/chat', base)

    const health = await withTimeout(timeoutMs, signal => fetchJson(healthUrl, { signal }))
    if (health?.status !== 'ok' || health?.service !== 'goreecloud-ai' ||
        !['configured', 'unconfigured'].includes(health?.wardveilArtifactScanner)) {
      throw new SafeFailure('unexpected_application_health')
    }

    const prepare = createModelRoutePreflight({
      loadPolicy: createLocalPolicyLoader({ policyPath: env.VALIDATE_MODEL_POLICY_PATH }),
      discoverModels: async ({ signal } = {}) => installedModels(await fetchJson(modelsUrl, { headers, signal })),
      timeoutMs: Math.min(timeoutMs, 30_000),
    })
    const selection = await prepare({ role: env.VALIDATE_MODEL_ROLE, preferredModel: env.VALIDATE_MODEL_PREFERRED })
    if (selection.status !== 'selected') {
      emit(selection.status, selection.reason)
    } else {
      const stream = await validateStream(chatUrl, { model: selection.model, headers, timeoutMs })
      emit('validated', undefined, {
        scope: 'operator-initiated-local-development-runtime',
        role: selection.role,
        model: selection.model,
        family: selection.family,
        selection: selection.selection,
        policyRevision: selection.policyRevision,
        policyTrust: selection.policyTrust,
        applicationService: 'goreecloud-ai',
        wardveilArtifactScanner: health.wardveilArtifactScanner,
        ...stream,
        runtimeValidated: true,
        validationScope: 'one-approved-streamed-request-only',
        executionAuthority: 'operator-initiated-development-validation-only',
        productionInferenceAuthorized: false,
        productionAccepted: false,
        stableQualified: false,
      })
    }
  } catch (error) {
    // Never echo configured URLs, policy paths, tokens, response bodies or model output.
    emit('unavailable', error instanceof SafeFailure ? error.reason : 'approved_model_runtime_validation_unavailable')
  }
}
