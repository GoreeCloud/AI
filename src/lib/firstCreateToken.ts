/** Browser-tab-only first-create request ID: never written to local storage or telemetry. */
export interface FirstCreateToken {
  fingerprint: string
  requestId: string
}

/** Reuse only for the same new-chat payload and navigation epoch after an uncertain response. */
export function getFirstCreateToken(
  ref: { current: FirstCreateToken | null },
  fingerprint: string,
  generate: () => string,
): string {
  if (ref.current?.fingerprint === fingerprint) return ref.current.requestId
  const requestId = generate()
  ref.current = { fingerprint, requestId }
  return requestId
}

export function clearFirstCreateToken(
  ref: { current: FirstCreateToken | null },
  requestId: string,
): void {
  if (ref.current?.requestId === requestId) ref.current = null
}
