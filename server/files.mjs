import { mkdir, readFile, rename, writeFile, unlink } from 'node:fs/promises'
import { createWriteStream } from 'node:fs'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import { artifactResourceId, finalizeArtifact, quarantineHandoff } from './artifact-security.mjs'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const FILE_DIR = path.join(DATA_DIR, 'files')
const STAGING_DIR = path.join(DATA_DIR, 'staging', 'files')
const INDEX_PATH = path.join(DATA_DIR, 'files.json')

let mutationTail = Promise.resolve()

async function withFileMutation(work) {
  const previous = mutationTail
  let release
  mutationTail = new Promise((resolve) => { release = resolve })
  await previous
  try { return await work() }
  finally { release() }
}

async function loadIndex() {
  try {
    const parsed = JSON.parse(await readFile(INDEX_PATH, 'utf8'))
    return Array.isArray(parsed.files) ? parsed.files : []
  } catch (error) {
    if (error?.code === 'ENOENT') return []
    throw error
  }
}

async function saveIndex(files) {
  await mkdir(DATA_DIR, { recursive: true, mode: 0o700 })
  const temp = `${INDEX_PATH}.tmp`
  await writeFile(temp, JSON.stringify({ version: 2, files }, null, 2), { mode: 0o600 })
  await rename(temp, INDEX_PATH)
}

function positiveLimit(value, fallback = Number.POSITIVE_INFINITY) {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : fallback
}

function quotaError(message) {
  return Object.assign(new Error(message), { status: 507 })
}

function contentLength(req) {
  const raw = req.headers['content-length']
  if (typeof raw !== 'string' || !raw) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) && value >= 0 ? value : null
}

export async function listFiles() {
  return (await loadIndex()).sort((a, b) => b.createdAt.localeCompare(a.createdAt))
}

export async function getFileRecord(id) {
  return (await loadIndex()).find((file) => file.id === id) ?? null
}

export async function getFileStorageUsage() {
  const files = await loadIndex()
  return {
    fileCount: files.length,
    totalBytes: files.reduce((total, file) => total + (Number.isFinite(Number(file.size)) ? Number(file.size) : 0), 0),
  }
}

export async function storeFile(req, maxBytes, scanner = null, limits = {}) {
  return withFileMutation(async () => {
    const filesBefore = await loadIndex()
    const maxFileCount = positiveLimit(limits.maxFileCount)
    const maxTotalBytes = positiveLimit(limits.maxTotalBytes)
    const currentBytes = filesBefore.reduce((total, file) => total + (Number.isFinite(Number(file.size)) ? Number(file.size) : 0), 0)
    const declaredLength = contentLength(req)

    if (filesBefore.length >= maxFileCount) throw quotaError('Attachment file-count quota exceeded')
    if (declaredLength !== null && currentBytes + declaredLength > maxTotalBytes) throw quotaError('Attachment storage-byte quota exceeded')

    const id = randomUUID()
    const name = decodeURIComponent(String(req.headers['x-file-name'] ?? 'attachment')).replace(/[\\/\0]/g, '_').slice(0, 240) || 'attachment'
    const mediaType = String(req.headers['content-type'] ?? 'application/octet-stream').slice(0, 160)
    const workspaceId = typeof req.headers['x-workspace-id'] === 'string' ? req.headers['x-workspace-id'] : null
    const contextId = workspaceId ? `workspace:${workspaceId}` : 'unassigned'
    const artifact = { contextId, artifactId: id, artifactKind: 'chat_upload', mediaType }

    await mkdir(STAGING_DIR, { recursive: true, mode: 0o700 })
    const stagedPath = path.join(STAGING_DIR, id)
    const finalPath = path.join(FILE_DIR, id)
    const stream = createWriteStream(stagedPath, { flags: 'wx', mode: 0o600 })
    let size = 0

    try {
      for await (const chunk of req) {
        size += chunk.length
        if (size > maxBytes) throw Object.assign(new Error('Attachment too large'), { status: 413 })
        if (currentBytes + size > maxTotalBytes) throw quotaError('Attachment storage-byte quota exceeded')
        if (!stream.write(chunk)) await new Promise((resolve) => stream.once('drain', resolve))
      }
      await new Promise((resolve, reject) => stream.end((error) => error ? reject(error) : resolve()))
    } catch (error) {
      stream.destroy()
      await unlink(stagedPath).catch(() => {})
      throw error
    }

    const release = await finalizeArtifact({ artifact, stagedPath, finalPath, scanner })
    const status = release.decision.releaseAllowed
      ? 'available'
      : release.decision.disposition === 'hold_review'
        ? 'held'
        : release.decision.disposition === 'block_quarantine'
          ? 'blocked'
          : 'unverified'
    const record = {
      id,
      name,
      mediaType,
      size,
      workspaceId,
      status,
      storageState: release.releasedPath ? 'released' : 'staged',
      resourceId: artifactResourceId(artifact),
      digestSha256: release.digestSha256,
      security: {
        disposition: release.decision.disposition,
        releaseAllowed: release.decision.releaseAllowed,
        useAsContextAllowed: release.decision.useAsContextAllowed,
        quarantineRequired: release.decision.quarantineRequired,
        reasonCodes: release.decision.reasonCodes,
        evidenceRefs: release.decision.evidenceRefs,
        scanRecordId: release.decision.scanRecordId,
        quarantineHandoff: quarantineHandoff(artifact, release.decision),
      },
      createdAt: new Date().toISOString(),
    }
    const files = await loadIndex()
    files.push(record)
    await saveIndex(files)
    return record
  })
}

export async function deleteFile(id) {
  return withFileMutation(async () => {
    const files = await loadIndex()
    const record = files.find((file) => file.id === id)
    if (!record) return false
    for (const candidate of [path.join(FILE_DIR, id), path.join(STAGING_DIR, id)]) {
      await unlink(candidate).catch((error) => { if (error?.code !== 'ENOENT') throw error })
    }
    await saveIndex(files.filter((file) => file.id !== id))
    return true
  })
}
