import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const STORE_PATH = path.join(DATA_DIR, 'conversations.json')

function now() { return new Date().toISOString() }

async function load() {
  try {
    const raw = await readFile(STORE_PATH, 'utf8')
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed.conversations) ? parsed.conversations : []
  } catch (error) {
    if (error?.code === 'ENOENT') return []
    throw error
  }
}

async function save(conversations) {
  await mkdir(DATA_DIR, { recursive: true })
  const temp = `${STORE_PATH}.tmp`
  await writeFile(temp, JSON.stringify({ version: 1, conversations }, null, 2), { mode: 0o600 })
  await rename(temp, STORE_PATH)
}

export async function listConversations() {
  const conversations = await load()
  return conversations
    .map(({ messages, ...item }) => ({ ...item, messageCount: messages.length }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export async function getConversation(id) {
  return (await load()).find((item) => item.id === id) ?? null
}

export async function createConversation(input = {}) {
  const conversations = await load()
  const timestamp = now()
  const conversation = {
    id: randomUUID(),
    title: typeof input.title === 'string' && input.title.trim() ? input.title.trim().slice(0, 120) : 'New conversation',
    model: typeof input.model === 'string' ? input.model : '',
    workspaceId: typeof input.workspaceId === 'string' ? input.workspaceId : null,
    messages: [],
    parentConversationId: typeof input.parentConversationId === 'string' ? input.parentConversationId : null,
    parentMessageIndex: Number.isInteger(input.parentMessageIndex) && input.parentMessageIndex >= 0 ? input.parentMessageIndex : null,
    createdAt: timestamp,
    updatedAt: timestamp,
  }
  conversations.push(conversation)
  await save(conversations)
  return conversation
}

export async function updateConversation(id, patch = {}) {
  const conversations = await load()
  const index = conversations.findIndex((item) => item.id === id)
  if (index < 0) return null
  const current = conversations[index]
  conversations[index] = {
    ...current,
    ...(typeof patch.title === 'string' ? { title: patch.title.trim().slice(0, 120) || current.title } : {}),
    ...(typeof patch.model === 'string' ? { model: patch.model } : {}),
    ...(patch.workspaceId === null || typeof patch.workspaceId === 'string' ? { workspaceId: patch.workspaceId } : {}),
    ...(Array.isArray(patch.messages) ? { messages: patch.messages } : {}),
    updatedAt: now(),
  }
  await save(conversations)
  return conversations[index]
}

export async function deleteConversation(id) {
  const conversations = await load()
  const next = conversations.filter((item) => item.id !== id)
  if (next.length === conversations.length) return false
  await save(next)
  return true
}
