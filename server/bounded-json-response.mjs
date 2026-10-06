export async function readBoundedJsonResponse(response, maxBytes) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes <= 0) {
    throw new Error('maxBytes must be a positive integer')
  }

  const declaredLength = Number(response.headers.get('content-length'))
  if (Number.isFinite(declaredLength) && declaredLength > maxBytes) {
    throw new Error('Upstream JSON response exceeded the configured limit')
  }
  if (!response.body) throw new Error('Upstream JSON response body is unavailable')

  const reader = response.body.getReader()
  const chunks = []
  let totalBytes = 0
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      if (!value?.length) continue
      totalBytes += value.length
      if (totalBytes > maxBytes) {
        try { await reader.cancel() } catch {}
        throw new Error('Upstream JSON response exceeded the configured limit')
      }
      chunks.push(value)
    }
  } finally {
    reader.releaseLock()
  }

  const body = new Uint8Array(totalBytes)
  let offset = 0
  for (const chunk of chunks) {
    body.set(chunk, offset)
    offset += chunk.length
  }

  let text
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(body)
  } catch {
    throw new Error('Upstream JSON response contained invalid UTF-8')
  }

  try {
    return JSON.parse(text)
  } catch {
    throw new Error('Upstream JSON response contained invalid JSON')
  }
}
