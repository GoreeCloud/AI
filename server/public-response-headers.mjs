export function publicResponseHeaders(contentType) {
  if (typeof contentType !== 'string' || !contentType.trim()) {
    throw new Error('contentType is required')
  }
  return {
    'Content-Type': contentType,
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
  }
}
