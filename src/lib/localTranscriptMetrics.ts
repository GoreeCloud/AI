import type { ChatMessage } from './ollama'

export interface LocalTranscriptMetrics {
  userCharacters: number
  assistantCharacters: number
  totalCharacters: number
}

/**
 * Count Unicode code points in the loaded visible transcript.
 * Does not read storage, call a model, estimate tokens, or persist results.
 */
export function summarizeLocalTranscript(
  messages: readonly ChatMessage[],
  ignoreMessage?: ChatMessage,
): LocalTranscriptMetrics {
  let userCharacters = 0
  let assistantCharacters = 0
  for (const message of messages) {
    if (message === ignoreMessage || !message.content.trim()) continue
    if (message.role !== 'user' && message.role !== 'assistant') continue
    let characters = 0
    for (const _character of message.content) characters += 1
    if (message.role === 'user') userCharacters += characters
    else assistantCharacters += characters
  }
  return { userCharacters, assistantCharacters, totalCharacters: userCharacters + assistantCharacters }
}
