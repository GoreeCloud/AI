interface ApiErrorPayload {
  error?: unknown
  message?: unknown
  reason?: unknown
}

export async function responseError(response: Response, fallback: string): Promise<Error> {
  let detail = ''
  try {
    const payload = await response.clone().json() as ApiErrorPayload
    const primary = typeof payload.message === 'string' && payload.message.trim()
      ? payload.message.trim()
      : typeof payload.error === 'string' ? payload.error.trim() : ''
    const reason = typeof payload.reason === 'string' ? payload.reason.trim() : ''
    detail = [primary, reason].filter(Boolean).join(' · ')
  } catch {}
  return new Error(detail ? `${fallback} (${response.status}): ${detail}` : `${fallback} (${response.status})`)
}
