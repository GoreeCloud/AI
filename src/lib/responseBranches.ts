import type { ChatMessage } from './ollama'
const MAX_MESSAGES = 4096
const MAX_EDIT_CHARS = 250_000 // Backend per-message limit in UTF-16 code units

function validPrefix(messages: readonly ChatMessage[], lastExclusive: number): ChatMessage[] {
  const prefix = messages.slice(0, lastExclusive).filter((message) =>
    (message.role === 'user' || message.role === 'assistant') && message.content.trim()
  ).map((message) => ({ role: message.role, content: message.content }))
  // A welcome card is not a historical assistant turn.
  while (prefix.length && prefix[0].role !== 'user') prefix.shift()
  return prefix
}

/** Construct an independent edited request without mutating source messages. */
export function editedMessageBranch(messages: readonly ChatMessage[], index: number, content: string): ChatMessage[] | null {
  if (!Number.isSafeInteger(index) || index < 0 || index >= messages.length || messages[index].role !== 'user') return null
  if (!content.trim() || content.trim().length > MAX_EDIT_CHARS) return null
  const prefix = validPrefix(messages, index + 1)
  if (!prefix.length || prefix.length > MAX_MESSAGES || prefix.at(-1)?.role !== 'user') return null
  prefix[prefix.length - 1] = { role: 'user', content: content.trim() }
  return prefix
}

/** Regenerate from an assistant turn as a separate request, preserving history. */
export function regenerationBranch(messages: readonly ChatMessage[], index: number): ChatMessage[] | null {
  if (!Number.isSafeInteger(index) || index < 0 || index >= messages.length || messages[index].role !== 'assistant') return null
  const prefix = validPrefix(messages, index)
  if (!prefix.length || prefix.length > MAX_MESSAGES || prefix.at(-1)?.role !== 'user') return null
  return prefix
}
