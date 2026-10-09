// Mirrors the server's per-message UTF-16 length bound. No truncation.
export const MAX_COMPOSER_CHARS = 250_000

export interface DraftReuseResult {
  draft: string
  error: string | null
}

/** Reuse a prior user message without overwriting an unsent draft or sending it. */
export function appendPreviousPrompt(currentDraft: string, previousPrompt: string): DraftReuseResult {
  if (!previousPrompt.trim()) return { draft: currentDraft, error: 'The selected prompt is empty.' }
  const separator = currentDraft.trim() ? '\n\n' : ''
  // Preserve any existing draft bytes. The UI never implicitly replaces or sends text.
  const result = currentDraft + separator + previousPrompt
  if (result.length > MAX_COMPOSER_CHARS) {
    return { draft: currentDraft, error: 'This prompt would exceed the 250,000-character message limit. Shorten the draft before reusing it.' }
  }
  return { draft: result, error: null }
}

/** Mirrors backend rejection before a request leaves the composer. */
export function composerDraftError(draft: string): string | null {
  if (!draft.trim()) return 'Enter a message before sending.'
  if (draft.trim().length > MAX_COMPOSER_CHARS) {
    return 'This message exceeds the 250,000-character limit. Shorten it before sending.'
  }
  return null
}
