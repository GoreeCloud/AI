const MAX_PUBLIC_ERROR_DETAIL_CHARS = 320

interface ApiErrorPayload {
  error?: unknown
  message?: unknown
  reason?: unknown
}

function boundedDetail(value: string): string {
  return value.replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, MAX_PUBLIC_ERROR_DETAIL_CHARS)
}

export async function responseError(response: Response, fallback: string): Promise<Error> {
  let detail = ''
  try {
    const payload = await response.clone().json() as ApiErrorPayload
    const primary = typeof payload.message === 'string' && payload.message.trim()
      ? boundedDetail(payload.message)
      : typeof payload.error === 'string' ? boundedDetail(payload.error) : ''
    const reason = typeof payload.reason === 'string' ? boundedDetail(payload.reason) : ''
    detail = [primary, reason].filter(Boolean).join(' · ')
  } catch {}
  return new Error(detail ? `${fallback} (${response.status}): ${detail}` : `${fallback} (${response.status})`)
}


export async function fetchWithDeadline(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 15_000): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(input, { ...init, signal: controller.signal })
  } catch (error) {
    if (controller.signal.aborted) throw new Error('Local GoreeCloud AI request timed out.')
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}
