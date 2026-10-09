import type { ChatMessage } from './ollama'

export interface OutlinePrompt {
  messageIndex: number
  turnNumber: number
  preview: string
}

export interface LocalConversationOutline {
  userTurns: number
  assistantTurns: number
  hiddenPrompts: number
  prompts: OutlinePrompt[]
}

const MAX_PROMPTS = 24
const MAX_PREVIEW_CHARS = 96

/** Browser-local navigation only. Nothing is indexed, transmitted, or stored. */
export function summarizeLocalConversation(
  messages: readonly ChatMessage[],
  ignoreMessage?: ChatMessage,
): LocalConversationOutline {
  let userTurns = 0
  let assistantTurns = 0
  const prompts: OutlinePrompt[] = []
  messages.forEach((message, messageIndex) => {
    if (message === ignoreMessage || !message.content.trim()) return
    if (message.role === 'assistant') {
      assistantTurns += 1
      return
    }
    if (message.role !== 'user') return
    userTurns += 1
    const normalized = message.content.replace(/[\u0000-\u001f\u007f-\u009f]+/g, ' ').replace(/\s+/gu, ' ').trim()
    const graphemes = Array.from(normalized)
    prompts.push({
      messageIndex,
      turnNumber: userTurns,
      preview: graphemes.length > MAX_PREVIEW_CHARS
        ? graphemes.slice(0, MAX_PREVIEW_CHARS - 1).join('') + '…'
        : normalized,
    })
    if (prompts.length > MAX_PROMPTS) prompts.shift()
  })
  return {
    userTurns,
    assistantTurns,
    hiddenPrompts: userTurns - prompts.length,
    prompts,
  }
}
