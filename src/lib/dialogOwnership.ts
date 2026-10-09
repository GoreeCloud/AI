import type { ChatMessage } from './ollama'

/** Confirm a historical edit still addresses the exact displayed prompt. */
export function editableDialogSourceIsCurrent(
  origin: { conversationId: string | null; index: number; originalContent: string },
  selectedConversationId: string | null,
  messages: readonly ChatMessage[]
): boolean {
  return origin.conversationId === selectedConversationId
    && Number.isSafeInteger(origin.index)
    && origin.index >= 0 && origin.index < messages.length
    && messages[origin.index]?.role === 'user'
    && messages[origin.index].content === origin.originalContent
}

/** Preserve Escape for an active IME composition rather than closing a dialog. */
export function shouldCloseTextDialog(event: {
  key: string
  isComposing?: boolean
  keyCode?: number
  ctrlKey?: boolean
  metaKey?: boolean
  altKey?: boolean
}, pending: boolean): boolean {
  return event.key === 'Escape' && !pending && !event.isComposing && event.keyCode !== 229
    && !event.ctrlKey && !event.metaKey && !event.altKey
}
