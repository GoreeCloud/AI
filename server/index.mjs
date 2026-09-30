import http from 'node:http'
import { createConversation, deleteConversation, getConversation, listConversations, updateConversation } from './conversations.mjs'
import { createWorkspace, deleteWorkspace, detachFileFromWorkspaces, getWorkspace, listWorkspaces, updateWorkspace } from './workspaces.mjs'
import { deleteFile, getFileRecord, getFileStorageUsage, listFiles, storeFile } from './files.mjs'
import { deleteTextExtraction, extractTextFile, getTextExtraction } from './text-extraction.mjs'
import { assessKnowledgeAuthorizationInput } from './knowledge-authorization.mjs'
import { assessKnowledgeEligibility, getKnowledgeEligibility } from './knowledge-eligibility.mjs'

const PORT = positiveNumberEnv('PORT', 8787)
const OLLAMA_URL = (process.env.OLLAMA_URL ?? 'http://127.0.0.1:11434').replace(/\/$/, '')
const API_TOKEN = process.env.GOREECLOUD_AI_API_TOKEN?.trim()
const MAX_BODY_BYTES = positiveNumberEnv('MAX_BODY_BYTES', 1_000_000)
const MAX_FILE_BYTES = positiveNumberEnv('MAX_FILE_BYTES', 25 * 1024 * 1024)
const MAX_FILE_COUNT = positiveNumberEnv('MAX_FILE_COUNT', 1_000)
const MAX_TOTAL_FILE_BYTES = positiveNumberEnv('MAX_TOTAL_FILE_BYTES', 1024 * 1024 * 1024)
const MAX_TEXT_EXTRACTION_BYTES = positiveNumberEnv('MAX_TEXT_EXTRACTION_BYTES', 2 * 1024 * 1024)
const REQUEST_TIMEOUT_MS = positiveNumberEnv('REQUEST_TIMEOUT_MS', 120_000)

// A deployed Wardveil transport adapter is intentionally not fabricated here.
// Until one is configured, attachment intake remains private, staged, and fail-closed.
const ARTIFACT_SCANNER = null

function positiveNumberEnv(name, fallback) {
  const raw = process.env[name]
  if (!raw) return fallback
  const value = Number(raw)
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${name} must be a positive integer`)
  return value
}

function json(res, status, payload) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' })
  res.end(JSON.stringify(payload))
}

function authorized(req) {
  if (!API_TOKEN) return true
  return req.headers.authorization === `Bearer ${API_TOKEN}`
}

async function readJson(req) {
  const chunks = []
  let size = 0
  for await (const chunk of req) {
    size += chunk.length
    if (size > MAX_BODY_BYTES) throw Object.assign(new Error('Request body too large'), { status: 413 })
    chunks.push(chunk)
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}') }
  catch { throw Object.assign(new Error('Invalid JSON request body'), { status: 400 }) }
}

function validMessages(messages) {
  return Array.isArray(messages) && messages.every((message) => message && ['system', 'user', 'assistant'].includes(message.role) && typeof message.content === 'string')
}

function validateChat(body) {
  return body && typeof body === 'object' && typeof body.model === 'string' && body.model.trim() && validMessages(body.messages) && body.messages.length > 0
}

async function ollamaFetch(path, init = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try { return await fetch(`${OLLAMA_URL}${path}`, { ...init, signal: init.signal ?? controller.signal }) }
  finally { clearTimeout(timeout) }
}

async function handleModels(res) {
  const upstream = await ollamaFetch('/api/tags', { headers: { Accept: 'application/json' } })
  if (!upstream.ok) return json(res, 502, { error: 'Ollama model discovery failed', upstreamStatus: upstream.status })
  const data = await upstream.json()
  json(res, 200, { models: Array.isArray(data.models) ? data.models : [] })
}

async function handleChat(req, res) {
  const body = await readJson(req)
  if (!validateChat(body)) return json(res, 400, { error: 'model and valid messages are required' })
  const controller = new AbortController()
  req.on('close', () => controller.abort())
  const upstream = await ollamaFetch('/api/chat', {
    method: 'POST', signal: controller.signal,
    headers: { 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
    body: JSON.stringify({ model: body.model.trim(), messages: body.messages, stream: true }),
  })
  if (!upstream.ok || !upstream.body) return json(res, 502, { error: 'Ollama chat request failed', upstreamStatus: upstream.status })
  res.writeHead(200, { 'Content-Type': 'application/x-ndjson; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' })
  const reader = upstream.body.getReader()
  try {
    while (true) { const { value, done } = await reader.read(); if (done) break; res.write(Buffer.from(value)) }
  } finally { reader.releaseLock(); res.end() }
}

async function handleConversations(req, res, pathname) {
  if (pathname === '/api/conversations') {
    if (req.method === 'GET') return json(res, 200, { conversations: await listConversations() })
    if (req.method === 'POST') return json(res, 201, await createConversation(await readJson(req)))
  }
  const match = pathname.match(/^\/api\/conversations\/([0-9a-f-]+)$/i)
  if (!match) return false
  const id = match[1]
  if (req.method === 'GET') {
    const conversation = await getConversation(id)
    return conversation ? json(res, 200, conversation) : json(res, 404, { error: 'Conversation not found' })
  }
  if (req.method === 'PATCH') {
    const patch = await readJson(req)
    if (patch.messages !== undefined && !validMessages(patch.messages)) return json(res, 400, { error: 'Invalid messages' })
    const conversation = await updateConversation(id, patch)
    return conversation ? json(res, 200, conversation) : json(res, 404, { error: 'Conversation not found' })
  }
  if (req.method === 'DELETE') return (await deleteConversation(id)) ? json(res, 200, { deleted: true }) : json(res, 404, { error: 'Conversation not found' })
  return false
}

async function handleWorkspaces(req, res, pathname) {
  if (pathname === '/api/workspaces') {
    if (req.method === 'GET') return json(res, 200, { workspaces: await listWorkspaces() })
    if (req.method === 'POST') return json(res, 201, await createWorkspace(await readJson(req)))
  }
  const match = pathname.match(/^\/api\/workspaces\/([0-9a-f-]+)$/i)
  if (!match) return false
  const id = match[1]
  if (req.method === 'GET') {
    const workspace = await getWorkspace(id)
    return workspace ? json(res, 200, workspace) : json(res, 404, { error: 'Workspace not found' })
  }
  if (req.method === 'PATCH') {
    const workspace = await updateWorkspace(id, await readJson(req))
    return workspace ? json(res, 200, workspace) : json(res, 404, { error: 'Workspace not found' })
  }
  if (req.method === 'DELETE') return (await deleteWorkspace(id)) ? json(res, 200, { deleted: true }) : json(res, 404, { error: 'Workspace not found' })
  return false
}

async function handleFiles(req, res, pathname) {
  if (pathname === '/api/files') {
    if (req.method === 'GET') {
      const [files, usage] = await Promise.all([listFiles(), getFileStorageUsage()])
      return json(res, 200, {
        files,
        storage: {
          ...usage,
          maxFileBytes: MAX_FILE_BYTES,
          maxFileCount: MAX_FILE_COUNT,
          maxTotalBytes: MAX_TOTAL_FILE_BYTES,
          maxTextExtractionBytes: MAX_TEXT_EXTRACTION_BYTES,
        },
      })
    }
    if (req.method === 'POST') {
      const file = await storeFile(req, MAX_FILE_BYTES, ARTIFACT_SCANNER, {
        maxFileCount: MAX_FILE_COUNT,
        maxTotalBytes: MAX_TOTAL_FILE_BYTES,
      })
      return json(res, file.status === 'available' ? 201 : 202, file)
    }
  }
  const match = pathname.match(/^\/api\/files\/([0-9a-f-]+)(?:\/(extraction|knowledge-eligibility|knowledge-authorization-assessment))?$/i)
  if (!match) return false
  const id = match[1]
  const resource = match[2]

  if (resource === 'extraction') {
    if (req.method === 'POST') return json(res, 201, await extractTextFile(id, MAX_TEXT_EXTRACTION_BYTES))
    if (req.method === 'GET') {
      const extraction = await getTextExtraction(id)
      return extraction ? json(res, 200, extraction) : json(res, 404, { error: 'Text extraction not found' })
    }
    return false
  }

  if (resource === 'knowledge-eligibility') {
    if (req.method === 'GET') {
      const assessment = await getKnowledgeEligibility(id)
      return assessment ? json(res, 200, assessment) : json(res, 404, { error: 'File not found' })
    }
    return false
  }

  if (resource === 'knowledge-authorization-assessment') {
    if (req.method !== 'POST') return false
    const record = await getFileRecord(id)
    if (!record) return json(res, 404, { error: 'File not found' })
    const authorization = assessKnowledgeAuthorizationInput(record, await readJson(req))
    const extraction = await getTextExtraction(id)
    return json(res, 200, assessKnowledgeEligibility(record, extraction, authorization))
  }

  if (req.method === 'GET') {
    const record = await getFileRecord(id)
    return record ? json(res, 200, record) : json(res, 404, { error: 'File not found' })
  }
  if (req.method === 'DELETE') {
    const record = await getFileRecord(id)
    if (!record) return json(res, 404, { error: 'File not found' })
    await deleteTextExtraction(id)
    const deleted = await deleteFile(id)
    if (!deleted) return json(res, 404, { error: 'File not found' })
    const workspaceReferencesRemoved = await detachFileFromWorkspaces(id)
    return json(res, 200, { deleted: true, workspaceReferencesRemoved })
  }
  return false
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url ?? '/', 'http://localhost')
    if (url.pathname === '/api/health' && req.method === 'GET') return json(res, 200, { status: 'ok', service: 'goreecloud-ai', ollama: OLLAMA_URL, wardveilArtifactScanner: ARTIFACT_SCANNER ? 'configured' : 'unconfigured' })
    if (!authorized(req)) return json(res, 401, { error: 'Unauthorized' })
    if (url.pathname === '/api/ollama/models' && req.method === 'GET') return await handleModels(res)
    if (url.pathname === '/api/ollama/chat' && req.method === 'POST') return await handleChat(req, res)
    if (url.pathname.startsWith('/api/conversations')) {
      const handled = await handleConversations(req, res, url.pathname)
      if (handled !== false) return handled
    }
    if (url.pathname.startsWith('/api/workspaces')) {
      const handled = await handleWorkspaces(req, res, url.pathname)
      if (handled !== false) return handled
    }
    if (url.pathname.startsWith('/api/files')) {
      const handled = await handleFiles(req, res, url.pathname)
      if (handled !== false) return handled
    }
    json(res, 404, { error: 'Not found' })
  } catch (error) {
    const status = Number(error?.status ?? (error?.name === 'AbortError' ? 504 : 500))
    json(res, status, {
      error: status === 500 ? 'Internal server error' : (error?.code ?? error.message),
      ...(status !== 500 && error?.code ? { message: error.message } : {}),
    })
  }
})

server.listen(PORT, '127.0.0.1', () => console.log(`GoreeCloud AI backend listening on http://127.0.0.1:${PORT}`))
