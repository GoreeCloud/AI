import type { ChatMessage } from './ollama'

/** Require the returned conversation to acknowledge the first message batch. */
export function initialConversationAcknowledged(
  value: { id?: unknown; messages?: unknown } | null,
  expected: readonly ChatMessage[],
): value is { id: string; messages: ChatMessage[] } {
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
  if (!value || typeof value.id !== 'string' || !uuid.test(value.id)) return false
  const received = value.messages
  return expected.length > 0 && Array.isArray(received) && received.length === expected.length
    && received.every((message, index) =>
      message?.role === expected[index]?.role && message?.content === expected[index]?.content)
}

/** Atomic server create replaces the old initial create-then-PATCH request sequence. */
export async function prepareFirstConversation(options: {
  create: () => Promise<{ id: string; messages: ChatMessage[] }>
  expectedMessages: readonly ChatMessage[]
  afterCreate?: () => Promise<void>
  isCurrent: () => boolean
  select: (id: string) => void
}): Promise<string> {
  if (!options.isCurrent()) throw new Error('Conversation selection changed before creation.')
  const created = await options.create()
  if (!options.isCurrent()) throw new Error('Conversation selection changed during creation.')
  if (!initialConversationAcknowledged(created, options.expectedMessages))
    throw new Error('The new conversation did not confirm its initial messages. Review conversation history before retrying.')
  if (options.afterCreate) await options.afterCreate()
  if (!options.isCurrent()) throw new Error('Conversation selection changed during preparation.')
  options.select(created.id)
  return created.id
}
