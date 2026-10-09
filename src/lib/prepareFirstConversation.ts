import type { ChatMessage } from './ollama'

export interface FirstConversationResult {
  id: string
  /** Non-null when a replay finds newer saved turns; do not generate again. */
  recoveredMessages: ChatMessage[] | null
}

/** A matching original prefix is required; appended saved turns are valid replay progress. */
export function initialConversationAcknowledged(
  value: { id?: unknown; messages?: unknown } | null,
  expected: readonly ChatMessage[],
): value is { id: string; messages: ChatMessage[] } {
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[a-f0-9]{12}$/i
  if (!value || typeof value.id !== 'string' || !uuid.test(value.id)) return false
  const received = value.messages
  return expected.length > 0 && Array.isArray(received) &&
    received.length >= expected.length && received.length <= 4096 &&
    received.every(message => message && (message.role === 'user' || message.role === 'assistant') &&
      typeof message.content === 'string' && message.content.length <= 250_000) &&
    expected.every((message, index) => (
      received[index].role === message.role && received[index].content === message.content
    ))
}

/**
 * Atomic create/replay: never select on mismatched acknowledgement or stale navigation.
 * A replay with additional saved turns must restore that state, not regenerate the model.
 */
export async function prepareFirstConversation(options: {
  create: () => Promise<{ id: string; messages: ChatMessage[] }>
  expectedMessages: readonly ChatMessage[]
  afterCreate?: () => Promise<void>
  isCurrent: () => boolean
  select: (id: string) => void
}): Promise<FirstConversationResult> {
  if (!options.isCurrent()) throw new Error('Conversation selection changed before creation.')
  const created = await options.create()
  if (!options.isCurrent()) throw new Error('Conversation selection changed during creation.')
  if (!initialConversationAcknowledged(created, options.expectedMessages))
    throw new Error('The server did not confirm the original messages. Review saved history before retrying.')
  if (options.afterCreate) await options.afterCreate()
  if (!options.isCurrent()) throw new Error('Conversation selection changed during preparation.')
  options.select(created.id)
  return {
    id: created.id,
    recoveredMessages: created.messages.length > options.expectedMessages.length ? created.messages : null,
  }
}
