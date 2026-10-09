import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createHash, randomUUID } from 'node:crypto'
import { createMutationQueue } from './mutation-queue.mjs'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const STORE_PATH = path.join(DATA_DIR, 'conversations.json')
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const CREATE_FIELDS = new Set(['title', 'model', 'workspaceId', 'parentConversationId', 'parentMessageIndex', 'messages', 'clientRequestId'])
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

function firstCreateSignature(input) {
  return createHash('sha256').update(JSON.stringify({
    title: input.title ?? null, model: input.model ?? null, workspaceId: input.workspaceId ?? null,
    parentConversationId: input.parentConversationId ?? null, parentMessageIndex: input.parentMessageIndex ?? null,
    messages: input.messages ?? [],
  })).digest('hex')
}

/** The retry key and request signature are internal storage metadata. */
function publicConversation(conversation) {
  const { clientRequestId, clientRequestSignature, ...visible } = conversation
  return visible
}

function validTimestamp(value) {
  if (typeof value !== 'string' || value.length > 64) return false
  const parsed = new Date(value)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString() === value
}

export function validateStoredConversation(value) {
  if (!record(value) || typeof value.id !== 'string' || !UUID.test(value.id)) return false
  if (!validTitle(value.title) || value.title.trim() !== value.title || !validModel(value.model) || !validOptionalUuid(value.workspaceId)) return false
  if (!validMessages(value.messages) || !validOptionalUuid(value.parentConversationId)) return false
  if (value.clientRequestId !== undefined || value.clientRequestSignature !== undefined) {
    if (typeof value.clientRequestId !== 'string' || !UUID.test(value.clientRequestId) ||
        typeof value.clientRequestSignature !== 'string' || !/^[a-f0-9]{64}$/.test(value.clientRequestSignature)) return false
  }
  const hasParent = typeof value.parentConversationId === 'string'
  const hasParentIndex = Number.isSafeInteger(value.parentMessageIndex) && value.parentMessageIndex >= 0 && value.parentMessageIndex <= 1_000_000
  if (hasParent !== hasParentIndex) return false
  if (!hasParent && value.parentMessageIndex !== null) return false
  if (!validTimestamp(value.createdAt) || !validTimestamp(value.updatedAt)) return false
  return Date.parse(value.updatedAt) >= Date.parse(value.createdAt)
}

export function validateConversationStore(value) {
  if (!record(value) || value.version !== 1 || !Array.isArray(value.conversations)) return false
  if (value.conversations.length > 100_000 || !value.conversations.every(validateStoredConversation)) return false
  const ids = value.conversations.map((conversation) => conversation.id)
  if (new Set(ids).size !== ids.length) return false
  const requestIds = value.conversations.map(row => row.clientRequestId).filter(Boolean)
  return new Set(requestIds).size === requestIds.length
}

export function validateConversationCreateInput(input) {
  if (!record(input) || Object.keys(input).some((key) => !CREATE_FIELDS.has(key))) return false
  if (input.title !== undefined && !validTitle(input.title)) return false
  if (input.messages !== undefined && !validMessages(input.messages)) return false
  if (input.clientRequestId !== undefined && (
      typeof input.clientRequestId !== 'string' || !UUID.test(input.clientRequestId) ||
      !Array.isArray(input.messages) || input.messages.length === 0 ||
      input.messages.at(-1)?.role !== 'user')) return false
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
    if (!validateConversationStore(parsed)) throw new Error('Conversation store failed validation')
    return parsed.conversations
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
    .map(({ messages, clientRequestId, clientRequestSignature, ...item }) => ({ ...item, messageCount: messages.length }))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export async function getConversation(id) {
  const record = (await load()).find((item) => item.id === id)
  return record ? publicConversation(record) : null
}

export async function createConversation(input = {}) {
  return withMutation(async () => {
    if (!validateConversationCreateInput(input))
      throw Object.assign(new Error('Invalid conversation input'), { status: 400 })
    const conversations = await load()
    const requestId = input.clientRequestId
    const requestSignature = requestId ? firstCreateSignature(input) : null
    if (requestId) {
      const existing = conversations.find(item => item.clientRequestId === requestId)
      if (existing) {
        if (existing.clientRequestSignature !== requestSignature)
          throw Object.assign(new Error('Create request ID was already used for different content'), {
            status: 409, code: 'create_request_conflict',
          })
        return publicConversation(existing)
      }
    }
  const timestamp = now()
  const conversation = {
    id: randomUUID(),
    title: typeof input.title === 'string' && input.title.trim() ? input.title.trim().slice(0, 120) : 'New conversation',
    model: typeof input.model === 'string' ? input.model : '',
    workspaceId: typeof input.workspaceId === 'string' ? input.workspaceId : null,
    messages: Array.isArray(input.messages) ? input.messages : [],
    ...(requestId ? { clientRequestId: requestId, clientRequestSignature: requestSignature } : {}),
    parentConversationId: typeof input.parentConversationId === 'string' ? input.parentConversationId : null,
    parentMessageIndex: Number.isInteger(input.parentMessageIndex) && input.parentMessageIndex >= 0 ? input.parentMessageIndex : null,
    createdAt: timestamp,
    updatedAt: timestamp,
  }
  conversations.push(conversation)
    await save(conversations)
    return publicConversation(conversation)
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
    return publicConversation(conversations[index])
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
