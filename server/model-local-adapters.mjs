/**
 * Development-only server-owned adapters for local model routing.
 *
 * These are intentionally not connected to HTTP routes or live inference.
 * They do not establish authenticated administrative provenance, Identity,
 * Privacy Shield, Policy, deployment, or production approval.
 */
import { constants } from 'node:fs'
import { open, realpath } from 'node:fs/promises'
import { dirname, isAbsolute } from 'node:path'

const POLICY_MAX_BYTES = 64 * 1024
const DISCOVERY_MAX_BYTES = 256 * 1024
const MAX_MODELS = 512

function boundedBytes(value, ceiling) {
  return Number.isSafeInteger(value) && value > 0 && value <= ceiling
}

/**
 * Reads an explicit, server-configured private JSON file. No request-controlled
 * path is accepted. On Linux, reject symlinks, nonregular files, extra hard
 * links, wrong ownership, permissive mode, and oversized policy input.
 * All policy structure and freshness remain the preflight module's job.
 */
export function createLocalPolicyLoader({ policyPath, maxBytes = POLICY_MAX_BYTES } = {}) {
  if (typeof policyPath !== 'string' || !isAbsolute(policyPath) ||
      policyPath.includes('\0') || !boundedBytes(maxBytes, POLICY_MAX_BYTES) ||
      !Number.isInteger(constants.O_NOFOLLOW) || typeof process.getuid !== 'function') {
    throw new TypeError('An absolute Linux policy path and bounded file size are required')
  }
  return async function loadPolicy({ signal } = {}) {
    if (signal?.aborted) throw new Error('policy_read_cancelled')
    // A trusted operator must configure the path in a protected directory.
    // Reject a symlinked immediate parent; O_NOFOLLOW secures the final item.
    const parent = dirname(policyPath)
    if (await realpath(parent) !== parent) throw new Error('policy_parent_not_canonical')
    const handle = await open(policyPath, constants.O_RDONLY | constants.O_NOFOLLOW)
    try {
      const before = await handle.stat()
      if (!before.isFile() || before.nlink !== 1 ||
          before.uid !== process.getuid() || (before.mode & 0o077) !== 0 ||
          before.size <= 0 || before.size > maxBytes) {
        throw new Error('invalid_local_policy_file')
      }
      if (signal?.aborted) throw new Error('policy_read_cancelled')
      const source = await handle.readFile({ encoding: 'utf8', signal })
      const after = await handle.stat()
      if (after.ino !== before.ino || after.dev !== before.dev ||
          after.size !== before.size || after.mtimeMs !== before.mtimeMs ||
          Buffer.byteLength(source, 'utf8') !== before.size) {
        throw new Error('policy_file_changed_during_read')
      }
      if (signal?.aborted) throw new Error('policy_read_cancelled')
      return JSON.parse(source)
    } finally {
      await handle.close()
    }
  }
}

function validateLocalBaseUrl(baseUrl) {
  if (typeof baseUrl !== 'string') throw new TypeError('Explicit local runtime URL required')
  let url
  try { url = new URL(baseUrl) } catch { throw new TypeError('Invalid local runtime URL') }
  if (url.protocol !== 'http:' ||
      !['127.0.0.1', '[::1]'].includes(url.hostname) ||
      (url.pathname !== '/' && url.pathname !== '') ||
      url.username || url.password || url.search || url.hash ||
      (url.port && (!Number.isSafeInteger(Number(url.port)) || Number(url.port) < 1 || Number(url.port) > 65535))) {
    throw new TypeError('Only literal loopback HTTP runtime endpoints are allowed')
  }
  return new URL('/api/tags', url)
}

/**
 * Fetch only the runtime's loopback model inventory. No DNS names, arbitrary
 * private hosts, redirects, or user-supplied URL paths are accepted. The
 * injected preflight owns timeout/cancellation; fetch receives its signal.
 */
export function createLoopbackModelDiscovery({
  baseUrl = 'http://127.0.0.1:11434',
  fetchImpl = globalThis.fetch,
  maxBytes = DISCOVERY_MAX_BYTES,
} = {}) {
  const endpoint = validateLocalBaseUrl(baseUrl)
  if (typeof fetchImpl !== 'function' || !boundedBytes(maxBytes, DISCOVERY_MAX_BYTES)) {
    throw new TypeError('Valid fetch adapter and bounded response size required')
  }

  return async function discoverModels({ signal } = {}) {
    if (signal?.aborted) throw new Error('model_discovery_cancelled')
    const response = await fetchImpl(endpoint, {
      method: 'GET', redirect: 'error', credentials: 'omit',
      headers: { Accept: 'application/json' }, signal,
    })
    if (!response?.ok || !response.body || typeof response.body.getReader !== 'function') {
      throw new Error('local_model_discovery_failed')
    }
    const advertised = response.headers?.get?.('content-length')
    if (advertised !== null && advertised !== undefined &&
        (!/^\d+$/.test(advertised) || Number(advertised) > maxBytes)) {
      await response.body.cancel()
      throw new Error('local_model_catalog_exceeds_limit')
    }
    const reader = response.body.getReader()
    const chunks = []
    let total = 0
    try {
      while (true) {
        if (signal?.aborted) throw new Error('model_discovery_cancelled')
        const { done, value } = await reader.read()
        if (done) break
        if (!(value instanceof Uint8Array)) throw new Error('invalid_local_model_catalog')
        total += value.byteLength
        if (total > maxBytes) throw new Error('local_model_catalog_exceeds_limit')
        chunks.push(value)
      }
    } catch (error) {
      await reader.cancel().catch(() => {})
      throw error
    } finally {
      reader.releaseLock()
    }
    if (signal?.aborted) throw new Error('model_discovery_cancelled')
    const decoded = new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks))
    const parsed = JSON.parse(decoded)
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed) ||
        !Array.isArray(parsed.models) || parsed.models.length > MAX_MODELS) {
      throw new Error('invalid_local_model_catalog')
    }
    // Deliberately strip runtime metadata and return no purported capabilities.
    // The approved-role selector checks exact model names and duplicates.
    return parsed.models.map((entry) => ({ name: entry?.name }))
  }
}
