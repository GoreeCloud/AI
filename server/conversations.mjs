import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import { createMutationQueue } from './mutation-queue.mjs'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const STORE_PATH = path.join(DATA_DIR, 'conversations.json')
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const CREATE_FIELDS = new Set(['title', 'model', 'workspaceId', 'parentConversationId', 'parentMessageIndex'])
const PATCH_FIELDS = new Set(['title', 'model', 'workspaceId', 'messages'])
const MESSAGE_ROLES = new Set(['user', 'assistant'])
const withMutation = createMutationQueue()

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validOptionalUuid(value) {
  return value === null || (typeof value === 'string' && UUID.test(value))
}

function validModel(value) {
  return typeof value === 'string' && value.length <= 512 && value.trim() === value
}

function validTitle(value) {
  return typeof value === 'string' && value.trim().length >= 1 && value.trim().length <= 120
}

function validMessages(value) {
  return Array.isArray(value) && value.length <= 4096 && value.every((message) =>
    record(message) &&
    Object.keys(message).every((key) => key === 'role' || key === 'content') &&
    MESSAGE_ROLES.has(message.role) &&
    typeof message.content === 'string' &&
    message.content.length <= 250_000
  )
}

export function validateConversationCreateInput(input) {
  if (!record(input) || Object.keys(input).some((key) => !CREATE_FIELDS.has(key))) return false
  if (input.title !== undefined && !validTitle(input.title)) return false
  if (input.model !== undefined && !validModel(input.model)) return false
  if (input.workspaceId !== undefined && !validOptionalUuid(input.workspaceId)) return false
  if (input.parentConversationId !== undefined && !validOptionalUuid(input.parentConversationId)) return false
  if (input.parentMessageIndex !== undefined && input.parentMessageIndex !== null &&
      (!Number.isSafeInteger(input.parentMessageIndex) || input.parentMessageIndex < 0 || input.parentMessageIndex > 1_000_000)) return false
  if ((input.parentConversationId === null || input.parentConversationId === undefined) &&
      input.parentMessageIndex !== null && input.parentMessageIndex !== undefined) return false
  return true
}

export function validateConversationPatch(input) {
  if (!record(input) || Object.keys(input).some((key) => !PATCH_FIELDS.has(key))) return false
  if (input.title !== undefined && !validTitle(input.title)) return false
  if (input.model !== undefined && !validModel(input.model)) return false
  if (input.workspaceId !== undefined && !validOptionalUuid(input.workspaceId)) return false
  if (input.messages !== undefined && !validMessages(input.messages)) return false
  return true
}

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
  await mkdir(DATA_DIR, { recursive: true, mode: 0o700 })
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
  return withMutation(async () => {
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
  })
}

export async function updateConversation(id, patch = {}) {
  return withMutation(async () => {
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
  })
}

export async function deleteConversation(id) {
  return withMutation(async () => {
    const conversations = await load()
  const next = conversations.filter((item) => item.id !== id)
  if (next.length === conversations.length) return false
    await save(next)
    return true
  })
}

export async function detachWorkspaceFromConversations(workspaceId) {
  if (typeof workspaceId !== 'string' || !UUID.test(workspaceId)) return 0
  return withMutation(async () => {
    const conversations = await load()
  let changed = 0
  const timestamp = now()
  const next = conversations.map((conversation) => {
    if (conversation.workspaceId !== workspaceId) return conversation
    changed += 1
    return { ...conversation, workspaceId: null, updatedAt: timestamp }
  })
    if (changed) await save(next)
    return changed
  })
}
