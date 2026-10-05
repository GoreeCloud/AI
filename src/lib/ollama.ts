import { fetchWithDeadline, responseError } from './http'

export type ChatRole = 'user' | 'assistant'

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

const MAX_STREAM_BUFFER_CHARS = 1_100_000
const MAX_DISCOVERED_MODELS = 256
const MAX_MODEL_STRING_CHARS = 512

function boundedModelString(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const normalized = value.trim()
  if (!normalized || normalized.length > MAX_MODEL_STRING_CHARS) return undefined
  return normalized
}

function parseDiscoveredModel(value: unknown): OllamaModel | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  const row = value as Record<string, unknown>
  const name = boundedModelString(row.name)
  if (!name) return undefined

  const model = boundedModelString(row.model)
  const modifiedAt = boundedModelString(row.modified_at)
  const digest = boundedModelString(row.digest)
  const numericSize = Number(row.size)
  const size = Number.isFinite(numericSize) && numericSize >= 0 ? numericSize : undefined

  return {
    name,
    ...(model ? { model } : {}),
    ...(modifiedAt ? { modified_at: modifiedAt } : {}),
    ...(size !== undefined ? { size } : {}),
    ...(digest ? { digest } : {}),
  }
}


function parseChatChunk(line: string): ChatChunk {
  let value: unknown
  try { value = JSON.parse(line) }
  catch { throw new Error('Streaming response contained invalid NDJSON') }
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Streaming response chunk is invalid')
  const chunk = value as ChatChunk
  if (chunk.error !== undefined && typeof chunk.error !== 'string') throw new Error('Streaming response error is invalid')
  if (chunk.done !== undefined && typeof chunk.done !== 'boolean') throw new Error('Streaming response completion state is invalid')
  if (chunk.message !== undefined) {
    if (!chunk.message || typeof chunk.message !== 'object' || chunk.message.role !== 'assistant' || typeof chunk.message.content !== 'string') {
      throw new Error('Streaming response message is invalid')
    }
  }
  return chunk
}

export interface StreamChatOptions {
  model: string
  messages: ChatMessage[]
  workspaceId?: string | null
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
    const response = await fetchWithDeadline(`${this.baseUrl}/models`, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
    if (!response.ok) throw await responseError(response, 'Model discovery failed')
    const data = (await response.json()) as ListModelsResponse
    if (!Array.isArray(data.models)) return []
    const models: OllamaModel[] = []
    const seen = new Set<string>()
    for (const value of data.models) {
      const model = parseDiscoveredModel(value)
      if (!model || seen.has(model.name)) continue
      seen.add(model.name)
      models.push(model)
      if (models.length >= MAX_DISCOVERED_MODELS) break
    }
    return models
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
        workspaceId: options.workspaceId ?? null,
        stream: true,
      }),
    })

    if (!response.ok) throw await responseError(response, 'Chat request failed')
    if (!response.body) throw new Error('Streaming response body is unavailable')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    let completed = false
    let terminalChunkSeen = false
    try {
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        if (buffer.length > MAX_STREAM_BUFFER_CHARS) throw new Error('Streaming response exceeded the client buffer limit')
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed) continue
          const chunk = parseChatChunk(trimmed)
          if (terminalChunkSeen) throw new Error('Streaming response continued after completion')
          if (chunk.error) throw new Error(chunk.error)
          if (chunk.done === true) terminalChunkSeen = true
          const token = chunk.message?.content
          if (token) options.onToken(token)
        }
      }

      buffer += decoder.decode()
      if (buffer.length > MAX_STREAM_BUFFER_CHARS) throw new Error('Streaming response exceeded the client buffer limit')
      if (buffer.trim()) {
        const chunk = parseChatChunk(buffer.trim())
        if (terminalChunkSeen) throw new Error('Streaming response continued after completion')
        if (chunk.error) throw new Error(chunk.error)
        if (chunk.done === true) terminalChunkSeen = true
        const token = chunk.message?.content
        if (token) options.onToken(token)
      }
      if (!terminalChunkSeen) throw new Error('Streaming response ended before completion')
      completed = true
    } finally {
      if (!completed) {
        try { await reader.cancel() } catch {}
      }
      reader.releaseLock()
    }
  }
}
