import type { ChatMessage } from './ollama'
import { composerDraftError } from './composerDraft'

const MAX_MESSAGES = 4096

/** Construct an independent edited request without mutating source messages. */
export function editedMessageBranch(messages: readonly ChatMessage[], index: number, content: string): ChatMessage[] | null {
  if (!Number.isSafeInteger(index) || index < 0 || index >= messages.length || messages[index].role !== 'user') return null
  if (composerDraftError(content)) return null
  const prefix = messages.slice(0, index + 1).filter((message) =>
    (message.role === 'user' || message.role === 'assistant') && message.content.trim()
  ).map((message) => ({ role: message.role, content: message.content }))
  if (!prefix.length || prefix.length > MAX_MESSAGES || prefix.at(-1)?.role !== 'user') return null
  prefix[prefix.length - 1] = { role: 'user', content: content.trim() }
  return prefix
}

/** Regenerate from an assistant turn as a separate request, preserving history. */
export function regenerationBranch(messages: readonly ChatMessage[], index: number): ChatMessage[] | null {
  if (!Number.isSafeInteger(index) || index < 0 || index >= messages.length || messages[index].role !== 'assistant') return null
  const prefix = messages.slice(0, index).filter((message) =>
    (message.role === 'user' || message.role === 'assistant') && message.content.trim()
  ).map((message) => ({ role: message.role, content: message.content }))
  if (!prefix.length || prefix.length > MAX_MESSAGES || prefix.at(-1)?.role !== 'user') return null
  return prefix
}
