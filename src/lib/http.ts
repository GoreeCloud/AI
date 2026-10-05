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
