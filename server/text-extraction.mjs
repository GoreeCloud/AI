import { createHash } from 'node:crypto'
import { mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { getFileRecord } from './files.mjs'

const DATA_DIR = process.env.GOREECLOUD_AI_DATA_DIR ?? path.resolve('data')
const FILE_DIR = path.join(DATA_DIR, 'files')
const EXTRACTION_DIR = path.join(DATA_DIR, 'extractions')
const SUPPORTED_MEDIA_TYPES = new Set(['text/plain', 'text/markdown', 'text/x-markdown', 'application/json'])

function httpError(status, message, code) {
  return Object.assign(new Error(message), { status, code })
}

function normalizedMediaType(value) {
  return String(value ?? '').split(';', 1)[0].trim().toLowerCase()
}

function sha256(bytes) {
  return createHash('sha256').update(bytes).digest('hex')
}

function validText(text) {
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index)
    if (code === 0) return false
    if (code < 32 && code !== 9 && code !== 10 && code !== 13) return false
  }
  return true
}

export function textExtractionEligibility(record) {
  if (!record) return { allowed: false, reason: 'file_not_found' }
  if (record.status !== 'available' || record.storageState !== 'released') {
    return { allowed: false, reason: 'file_not_security_released' }
  }
  if (record.security?.releaseAllowed !== true || record.security?.useAsContextAllowed !== true) {
    return { allowed: false, reason: 'wardveil_context_use_not_allowed' }
  }
  const mediaType = normalizedMediaType(record.mediaType)
  if (!SUPPORTED_MEDIA_TYPES.has(mediaType)) return { allowed: false, reason: 'media_type_not_supported' }
  return { allowed: true, mediaType }
}

export async function extractTextFile(id, maxBytes) {
  const record = await getFileRecord(id)
  if (!record) throw httpError(404, 'Attachment not found', 'file_not_found')

  const eligibility = textExtractionEligibility(record)
  if (!eligibility.allowed) {
    const status = eligibility.reason === 'media_type_not_supported' ? 415 : 409
    throw httpError(status, 'Attachment is not eligible for safe text extraction', eligibility.reason)
  }

  const limit = Number(maxBytes)
  if (!Number.isSafeInteger(limit) || limit <= 0) throw new Error('Text extraction byte limit must be a positive integer')
  if (Number(record.size) > limit) throw httpError(413, 'Attachment exceeds text extraction byte limit', 'text_extraction_too_large')

  const sourcePath = path.join(FILE_DIR, id)
  const bytes = await readFile(sourcePath)
  if (bytes.length > limit) throw httpError(413, 'Attachment exceeds text extraction byte limit', 'text_extraction_too_large')

  const sourceDigestSha256 = sha256(bytes)
  if (sourceDigestSha256 !== record.digestSha256) {
    throw httpError(409, 'Released attachment digest no longer matches accepted Wardveil evidence', 'source_digest_mismatch')
  }

  let text
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    throw httpError(415, 'Attachment is not valid UTF-8 text', 'invalid_utf8')
  }
  if (!validText(text)) throw httpError(415, 'Attachment contains unsupported control bytes', 'unsafe_text_controls')

  if (eligibility.mediaType === 'application/json') {
    try {
      text = JSON.stringify(JSON.parse(text), null, 2)
    } catch {
      throw httpError(415, 'Attachment is not valid JSON', 'invalid_json')
    }
  } else {
    text = text.replace(/\r\n?/g, '\n')
  }

  const textBytes = Buffer.from(text, 'utf8')
  const extraction = {
    version: 1,
    fileId: record.id,
    sourceResourceId: record.resourceId,
    sourceDigestSha256,
    mediaType: eligibility.mediaType,
    textDigestSha256: sha256(textBytes),
    sourceBytes: bytes.length,
    textBytes: textBytes.length,
    characters: text.length,
    state: 'extracted',
    createdAt: new Date().toISOString(),
    text,
  }

  await mkdir(EXTRACTION_DIR, { recursive: true, mode: 0o700 })
  const target = path.join(EXTRACTION_DIR, `${id}.json`)
  const temp = `${target}.${process.pid}.tmp`
  await writeFile(temp, JSON.stringify(extraction), { mode: 0o600 })
  await rename(temp, target)
  return extraction
}

export async function getTextExtraction(id) {
  const record = await getFileRecord(id)
  if (!record) return null
  const target = path.join(EXTRACTION_DIR, `${id}.json`)
  let parsed
  try {
    parsed = JSON.parse(await readFile(target, 'utf8'))
  } catch (error) {
    if (error?.code === 'ENOENT') return null
    throw error
  }
  if (parsed?.version !== 1 || parsed?.fileId !== id || parsed?.sourceDigestSha256 !== record.digestSha256 || parsed?.state !== 'extracted') {
    throw httpError(409, 'Stored extraction is not bound to the current attachment record', 'extraction_binding_mismatch')
  }
  return parsed
}

export async function deleteTextExtraction(id) {
  await unlink(path.join(EXTRACTION_DIR, `${id}.json`)).catch((error) => {
    if (error?.code !== 'ENOENT') throw error
  })
}
