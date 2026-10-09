/** Explicit-click clipboard adapter. The caller supplies content lazily. */
export async function writeTranscriptOnRequest(
  getText: () => string,
  writer: ((text: string) => Promise<void>) | undefined,
): Promise<'copied' | 'unavailable' | 'empty' | 'failed'> {
  if (!writer) return 'unavailable'
  let content: string
  try {
    content = getText()
  } catch {
    return 'failed'
  }
  if (!content) return 'empty'
  try {
    await writer(content)
    return 'copied'
  } catch {
    return 'failed'
  }
}
