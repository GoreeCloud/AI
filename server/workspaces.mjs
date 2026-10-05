import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import { createMutationQueue } from './mutation-queue.mjs'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const STORE_PATH = path.join(DATA_DIR, 'workspaces.json')
const MODEL_ROLE_IDS = new Set(['assistant', 'reasoner', 'engineer', 'utility', 'embeddings', 'vision', 'second-opinion'])
const CREATE_FIELDS = new Set(['name', 'instructions', 'defaultModelRole', 'researchEnabled'])
const PATCH_FIELDS = new Set(['name', 'instructions', 'defaultModelRole', 'fileIds', 'knowledgeCollectionIds', 'toolIds', 'researchEnabled'])
const withMutation = createMutationQueue()

function now() { return new Date().toISOString() }

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function validName(value) {
  return typeof value === 'string' && value.trim().length >= 1 && value.trim().length <= 120
}

function validInstructions(value) {
  return typeof value === 'string' && value.length <= 20_000
}

function validRole(value) {
  return typeof value === 'string' && MODEL_ROLE_IDS.has(value)
}

function validIdList(value) {
  return Array.isArray(value) &&
    value.length <= 1_000 &&
    new Set(value).size === value.length &&
    value.every((item) => typeof item === 'string' && item.length >= 1 && item.length <= 256 && item.trim() === item)
}

export function validateWorkspaceCreateInput(input) {
  if (!record(input) || Object.keys(input).some((key) => !CREATE_FIELDS.has(key))) return false
  if (input.name !== undefined && !validName(input.name)) return false
  if (input.instructions !== undefined && !validInstructions(input.instructions)) return false
  if (input.defaultModelRole !== undefined && !validRole(input.defaultModelRole)) return false
  if (input.researchEnabled !== undefined && typeof input.researchEnabled !== 'boolean') return false
  return true
}

export function validateWorkspacePatch(input) {
  if (!record(input) || Object.keys(input).some((key) => !PATCH_FIELDS.has(key))) return false
  if (input.name !== undefined && !validName(input.name)) return false
  if (input.instructions !== undefined && !validInstructions(input.instructions)) return false
  if (input.defaultModelRole !== undefined && !validRole(input.defaultModelRole)) return false
  if (input.fileIds !== undefined && !validIdList(input.fileIds)) return false
  if (input.knowledgeCollectionIds !== undefined && !validIdList(input.knowledgeCollectionIds)) return false
  if (input.toolIds !== undefined && !validIdList(input.toolIds)) return false
  if (input.researchEnabled !== undefined && typeof input.researchEnabled !== 'boolean') return false
  return true
}

async function load() {
  try {
    const parsed = JSON.parse(await readFile(STORE_PATH, 'utf8'))
    return Array.isArray(parsed.workspaces) ? parsed.workspaces : []
  } catch (error) {
    if (error?.code === 'ENOENT') return []
    throw error
  }
}

async function save(workspaces) {
  await mkdir(DATA_DIR, { recursive: true, mode: 0o700 })
  const temp = `${STORE_PATH}.tmp`
  await writeFile(temp, JSON.stringify({ version: 1, workspaces }, null, 2), { mode: 0o600 })
  await rename(temp, STORE_PATH)
}

export async function listWorkspaces() {
  return (await load()).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export async function getWorkspace(id) {
  return (await load()).find((workspace) => workspace.id === id) ?? null
}

export async function createWorkspace(input = {}) {
  return withMutation(async () => {
    const workspaces = await load()
  const timestamp = now()
  const workspace = {
    id: randomUUID(),
    name: typeof input.name === 'string' && input.name.trim() ? input.name.trim().slice(0, 120) : 'New Workspace',
    instructions: typeof input.instructions === 'string' ? input.instructions.slice(0, 20_000) : '',
    defaultModelRole: validRole(input.defaultModelRole) ? input.defaultModelRole : 'assistant',
    fileIds: [],
    knowledgeCollectionIds: [],
    toolIds: [],
    researchEnabled: Boolean(input.researchEnabled),
    createdAt: timestamp,
    updatedAt: timestamp,
  }
  workspaces.push(workspace)
    await save(workspaces)
    return workspace
  })
}

export async function updateWorkspace(id, patch = {}) {
  return withMutation(async () => {
    const workspaces = await load()
  const index = workspaces.findIndex((workspace) => workspace.id === id)
  if (index < 0) return null
  const current = workspaces[index]
  workspaces[index] = {
    ...current,
    ...(typeof patch.name === 'string' ? { name: patch.name.trim().slice(0, 120) || current.name } : {}),
    ...(typeof patch.instructions === 'string' ? { instructions: patch.instructions.slice(0, 20_000) } : {}),
    ...(validRole(patch.defaultModelRole) ? { defaultModelRole: patch.defaultModelRole } : {}),
    ...(Array.isArray(patch.fileIds) ? { fileIds: [...new Set(patch.fileIds.filter((value) => typeof value === 'string'))] } : {}),
    ...(Array.isArray(patch.knowledgeCollectionIds) ? { knowledgeCollectionIds: [...new Set(patch.knowledgeCollectionIds.filter((value) => typeof value === 'string'))] } : {}),
    ...(Array.isArray(patch.toolIds) ? { toolIds: [...new Set(patch.toolIds.filter((value) => typeof value === 'string'))] } : {}),
    ...(typeof patch.researchEnabled === 'boolean' ? { researchEnabled: patch.researchEnabled } : {}),
    updatedAt: now(),
  }
    await save(workspaces)
    return workspaces[index]
  })
}

export async function detachFileFromWorkspaces(fileId) {
  if (typeof fileId !== 'string' || !fileId) return 0
  return withMutation(async () => {
    const workspaces = await load()
  let changed = 0
  const timestamp = now()
  const next = workspaces.map((workspace) => {
    if (!Array.isArray(workspace.fileIds) || !workspace.fileIds.includes(fileId)) return workspace
    changed += 1
    return {
      ...workspace,
      fileIds: workspace.fileIds.filter((id) => id !== fileId),
      updatedAt: timestamp,
    }
  })
    if (changed) await save(next)
    return changed
  })
}

export async function deleteWorkspace(id) {
  return withMutation(async () => {
    const workspaces = await load()
  const next = workspaces.filter((workspace) => workspace.id !== id)
  if (next.length === workspaces.length) return false
    await save(next)
    return true
  })
}
