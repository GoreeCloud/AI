import type { ChatMessage } from './ollama'

export interface ConversationSummary {
  id: string
  title: string
  model: string
  workspaceId?: string | null
  createdAt: string
  updatedAt: string
  messageCount: number
  parentConversationId?: string | null
  parentMessageIndex?: number | null
}

export interface Conversation extends Omit<ConversationSummary, 'messageCount'> {
  messages: ChatMessage[]
}

interface CreateConversationInput {
  model?: string
  title?: string
  workspaceId?: string | null
  parentConversationId?: string | null
  parentMessageIndex?: number | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', ...init, headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers } })
  if (!response.ok) throw new Error(`Conversation request failed (${response.status})`)
  return response.json() as Promise<T>
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const data = await request<{ conversations: ConversationSummary[] }>('/api/conversations')
  return data.conversations
}

export function getConversation(id: string): Promise<Conversation> {
  return request(`/api/conversations/${id}`)
}

export function createConversation(input: string | CreateConversationInput = ''): Promise<Conversation> {
  const body = typeof input === 'string' ? { model: input } : input
  return request('/api/conversations', { method: 'POST', body: JSON.stringify(body) })
}

export function saveConversation(conversation: Pick<Conversation, 'id' | 'title' | 'model' | 'messages'> & { workspaceId?: string | null }): Promise<Conversation> {
  return request(`/api/conversations/${conversation.id}`, {
    method: 'PATCH',
    body: JSON.stringify({ title: conversation.title, model: conversation.model, messages: conversation.messages, ...(conversation.workspaceId !== undefined ? { workspaceId: conversation.workspaceId } : {}) }),
  })
}

export async function removeConversation(id: string): Promise<void> {
  await request(`/api/conversations/${id}`, { method: 'DELETE' })
}
