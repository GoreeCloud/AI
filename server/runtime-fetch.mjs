export function createRuntimeFetch({ baseUrl, timeoutMs, fetchImpl = fetch }) {
  if (typeof baseUrl !== 'string' || !baseUrl) throw new Error('baseUrl is required')
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs <= 0) throw new Error('timeoutMs must be a positive integer')
  if (typeof fetchImpl !== 'function') throw new Error('fetchImpl must be a function')

  const normalizedBaseUrl = baseUrl.replace(/\/$/, '')

  return function runtimeFetch(path, init = {}) {
    if (typeof path !== 'string' || !path.startsWith('/')) {
      throw new Error('Runtime fetch path must be absolute-path relative')
    }
    const deadline = AbortSignal.timeout(timeoutMs)
    const signal = init.signal ? AbortSignal.any([init.signal, deadline]) : deadline
    return fetchImpl(`${normalizedBaseUrl}${path}`, {
      ...init,
      redirect: 'error',
      signal,
    })
  }
}
