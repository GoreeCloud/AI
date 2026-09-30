export type ChatRole = 'system' | 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

export interface OllamaModel {
  name: string
  model?: string
  modified_at?: string
  size?: number
  digest?: string
  details?: Record<string, unknown>
}

interface ListModelsResponse {
  models?: OllamaModel[]
}

interface ChatChunk {
  message?: ChatMessage
  done?: boolean
  error?: string
}

export interface StreamChatOptions {
  model: string
  messages: ChatMessage[]
  signal?: AbortSignal
  onToken: (token: string) => void
}

/**
 * Browser-facing adapter for GoreeCloud AI's backend Ollama gateway.
 *
 * The browser intentionally does not call Ollama directly. The backend owns
 * runtime location, authentication, authorization, request limits, auditing,
 * privacy state, and future provider/runtime changes.
 */
export class OllamaClient {
  constructor(private readonly baseUrl: string) {}

  async listModels(): Promise<OllamaModel[]> {
    const response = await fetch(`${this.baseUrl}/models`, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
    if (!response.ok) throw new Error(`Model discovery failed (${response.status})`)
    const data = (await response.json()) as ListModelsResponse
    return Array.isArray(data.models) ? data.models : []
  }

  async streamChat(options: StreamChatOptions): Promise<void> {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      credentials: 'same-origin',
      signal: options.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/x-ndjson',
      },
      body: JSON.stringify({
        model: options.model,
        messages: options.messages,
        stream: true,
      }),
    })

    if (!response.ok) throw new Error(`Chat request failed (${response.status})`)
    if (!response.body) throw new Error('Streaming response body is unavailable')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue
        const chunk = JSON.parse(trimmed) as ChatChunk
        if (chunk.error) throw new Error(chunk.error)
        const token = chunk.message?.content
        if (token) options.onToken(token)
      }
    }

    if (buffer.trim()) {
      const chunk = JSON.parse(buffer) as ChatChunk
      if (chunk.error) throw new Error(chunk.error)
      const token = chunk.message?.content
      if (token) options.onToken(token)
    }
  }
}
