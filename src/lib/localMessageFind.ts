import type { ChatMessage } from './ollama'

const MAX_QUERY_CHARS = 120
const MAX_TERMS = 16

function fold(text: string): string {
  return text.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase()
}

/** Pure, local-only search over the currently displayed conversation. */
export function findLocalMessages(messages: readonly ChatMessage[], query: string): number[] {
  const terms = fold(query.slice(0, MAX_QUERY_CHARS)).trim().split(/\s+/u).filter(Boolean).slice(0, MAX_TERMS)
  if (terms.length === 0) return []
  const indices: number[] = []
  messages.forEach((message, index) => {
    const content = fold(message.content)
    if (terms.every(term => content.includes(term))) indices.push(index)
  })
  return indices
}

/** Move predictably between visible message matches; -1 means none selected yet. */
export function nextLocalMatchCursor(count: number, current: number, direction: -1 | 1): number {
  if (!Number.isSafeInteger(count) || count <= 0 || !Number.isSafeInteger(current)) return -1
  if (current < 0 || current >= count) return direction > 0 ? 0 : count - 1
  return (current + direction + count) % count
}
