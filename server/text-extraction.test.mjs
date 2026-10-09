import assert from 'node:assert/strict'
import { Readable } from 'node:stream'
import { mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { after, before, test } from 'node:test'
import { artifactResourceId } from './artifact-security.mjs'

let dataDir
let storeFile
let extractTextFile
let getTextExtraction
let deleteTextExtraction

before(async () => {
  dataDir = await mkdtemp(path.join(os.tmpdir(), 'goreecloud-ai-extraction-'))
  process.env.GOREECLOUD_AI_DATA_DIR = dataDir
  ;({ storeFile } = await import(`./files.mjs?extraction=${Date.now()}`))
  ;({ extractTextFile, getTextExtraction, deleteTextExtraction } = await import(`./text-extraction.mjs?test=${Date.now()}`))
})

after(async () => {
  delete process.env.GOREECLOUD_AI_DATA_DIR
  await rm(dataDir, { recursive: true, force: true })
})

function uploadRequest(bytes, mediaType = 'text/plain') {
  const buffer = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes)
  const request = Readable.from([buffer])
  request.headers = {
    'x-file-name': encodeURIComponent('knowledge.txt'),
    'content-type': mediaType,
    'content-length': String(buffer.length),
  }
  return request
}

const cleanScanner = {
  async scanStagedFile({ artifact, digestSha256 }) {
    const now = new Date()
    return {
      resource_id: artifactResourceId(artifact),
      resource_digest_sha256: digestSha256,
      scan_record: {
        contract_version: '0.1.0',
        record_type: 'scan_finding',
        record_id: `scan-${artifact.artifactId}`,
        producer: { id: 'wardveil-test', authoritative: true },
        scope: { resource_type: 'ai_artifact', resource_id: artifactResourceId(artifact) },
        scan_result: 'clean',
        observed_at: new Date(now.getTime() - 1_000).toISOString(),
        valid_until: new Date(now.getTime() + 60_000).toISOString(),
        evidence_refs: ['evidence:test-scanner', 'evidence:test-scan'],
      },
    }
  },
}

test('extracts only Wardveil-released passive UTF-8 text and preserves digest binding', async () => {
  const record = await storeFile(uploadRequest('hello\r\nworld'), 4096, cleanScanner)
  const extraction = await extractTextFile(record.id, 4096)
  assert.equal(extraction.state, 'extracted')
  assert.equal(extraction.text, 'hello\nworld')
  assert.equal(extraction.sourceDigestSha256, record.digestSha256)
  assert.equal(extraction.sourceResourceId, record.resourceId)
  assert.match(extraction.textDigestSha256, /^[a-f0-9]{64}$/)
  assert.equal((await stat(path.join(dataDir, 'extractions', `${record.id}.json`))).mode & 0o777, 0o600)
  assert.deepEqual(await getTextExtraction(record.id), extraction)
})

test('blocks extraction for staged unverified attachments', async () => {
  const record = await storeFile(uploadRequest('not trusted'), 4096, null)
  await assert.rejects(
    () => extractTextFile(record.id, 4096),
    (error) => error?.status === 409 && error?.code === 'file_not_security_released',
  )
})

test('keeps non-text parser formats outside the initial extraction allowlist', async () => {
  const record = await storeFile(uploadRequest('%PDF-not-a-parser-contract', 'application/pdf'), 4096, cleanScanner)
  await assert.rejects(
    () => extractTextFile(record.id, 4096),
    (error) => error?.status === 415 && error?.code === 'media_type_not_supported',
  )
})

test('fails closed when released bytes no longer match accepted Wardveil digest', async () => {
  const record = await storeFile(uploadRequest('original'), 4096, cleanScanner)
  await writeFile(path.join(dataDir, 'files', record.id), 'changed')
  await assert.rejects(
    () => extractTextFile(record.id, 4096),
    (error) => error?.status === 409 && error?.code === 'source_digest_mismatch',
  )
})

test('rejects invalid JSON, invalid UTF-8, and extraction-limit overflow', async () => {
  const badJson = await storeFile(uploadRequest('{bad json', 'application/json'), 4096, cleanScanner)
  await assert.rejects(() => extractTextFile(badJson.id, 4096), (error) => error?.code === 'invalid_json')

  const invalidUtf8 = await storeFile(uploadRequest(Buffer.from([0xff, 0xfe]), 'text/plain'), 4096, cleanScanner)
  await assert.rejects(() => extractTextFile(invalidUtf8.id, 4096), (error) => error?.code === 'invalid_utf8')

  const tooLarge = await storeFile(uploadRequest('0123456789', 'text/plain'), 4096, cleanScanner)
  await assert.rejects(() => extractTextFile(tooLarge.id, 5), (error) => error?.status === 413 && error?.code === 'text_extraction_too_large')
})

test('extraction cleanup is explicit and removes the derived private copy', async () => {
  const record = await storeFile(uploadRequest('temporary'), 4096, cleanScanner)
  await extractTextFile(record.id, 4096)
  await deleteTextExtraction(record.id)
  assert.equal(await getTextExtraction(record.id), null)
  await assert.rejects(() => readFile(path.join(dataDir, 'extractions', `${record.id}.json`)), { code: 'ENOENT' })
})
