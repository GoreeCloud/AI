import assert from 'node:assert/strict'
import { Readable } from 'node:stream'
import { mkdir, mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { after, before, test } from 'node:test'
import {
  artifactResourceId,
  evaluateArtifactScan,
  finalizeArtifact,
  quarantineHandoff,
  sha256File,
} from './artifact-security.mjs'

const NOW = new Date('2026-08-27T17:00:00.000Z')
const artifact = (kind = 'chat_upload') => ({ contextId: 'context-1', artifactId: 'artifact-1', artifactKind: kind, mediaType: 'application/octet-stream' })

function envelope(item, digest, { result = 'clean', evidence = true, observedAt, validUntil } = {}) {
  return {
    resource_id: artifactResourceId(item),
    resource_digest_sha256: digest,
    scan_record: {
      contract_version: '0.1.0',
      record_type: 'scan_finding',
      record_id: 'scan-1',
      producer: { id: 'wardveil-scan', authoritative: true },
      scope: { resource_type: 'ai_artifact', resource_id: artifactResourceId(item) },
      scan_result: result,
      observed_at: (observedAt ?? new Date(NOW.getTime() - 60_000)).toISOString(),
      valid_until: (validUntil ?? new Date(NOW.getTime() + 240_000)).toISOString(),
      evidence_refs: evidence ? ['evidence:scanner-health', 'evidence:scan'] : [],
    },
  }
}

class FakeScanner {
  constructor({ result = 'clean', mutate = false, fail = false } = {}) {
    this.result = result
    this.mutate = mutate
    this.fail = fail
  }

  async scanStagedFile({ artifact: item, stagedPath, digestSha256 }) {
    if (this.fail) throw new Error('scanner unavailable')
    if (this.mutate) await writeFile(stagedPath, Buffer.concat([await readFile(stagedPath), Buffer.from('changed')]))
    return envelope(item, digestSha256, { result: this.result })
  }
}

test('hashes files using SHA-256', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'goreecloud-ai-hash-'))
  try {
    const file = path.join(dir, 'abc.bin')
    await writeFile(file, 'abc')
    assert.equal(await sha256File(file), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
})

test('releases only current authoritative clean evidence and allows safe context kinds', async () => {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'goreecloud-ai-clean-'))
  try {
    const staged = path.join(dir, 'staging', 'upload')
    const released = path.join(dir, 'files', 'upload')
    await mkdir(path.dirname(staged), { recursive: true, mode: 0o700 })
    await writeFile(staged, 'clean')
    const result = await finalizeArtifact({ artifact: artifact(), stagedPath: staged, finalPath: released, scanner: new FakeScanner(), now: NOW })
    assert.equal(result.decision.disposition, 'allow')
    assert.equal(result.decision.releaseAllowed, true)
    assert.equal(result.decision.useAsContextAllowed, true)
    assert.equal(result.releasedPath, released)
    assert.equal((await readFile(released, 'utf8')), 'clean')
    assert.equal((await stat(path.dirname(released))).mode & 0o777, 0o700)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
})

test('malicious evidence remains blocked and produces only a quarantine handoff', () => {
  const item = artifact('tool_artifact')
  const digest = 'd'.repeat(64)
  const decision = evaluateArtifactScan(item, digest, envelope(item, digest, { result: 'malicious' }), NOW)
  assert.equal(decision.disposition, 'block_quarantine')
  assert.equal(decision.releaseAllowed, false)
  const handoff = quarantineHandoff(item, decision)
  assert.equal(handoff.requires_explicit_executor_authority, true)
  assert.equal(handoff.destructive_action, false)
})

test('expired clean evidence fails closed', () => {
  const item = artifact()
  const digest = 'e'.repeat(64)
  const decision = evaluateArtifactScan(item, digest, envelope(item, digest, { validUntil: new Date(NOW.getTime() - 1_000) }), NOW)
  assert.equal(decision.disposition, 'blocked_unverified')
  assert.ok(decision.reasonCodes.includes('clean_scan_evidence_expired'))
})

test('missing scanner and changed bytes retain private staging', async () => {
  for (const scanner of [null, new FakeScanner({ mutate: true })]) {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'goreecloud-ai-staged-'))
    try {
      const staged = path.join(dir, 'staging', 'upload')
      const released = path.join(dir, 'files', 'upload')
      await mkdir(path.dirname(staged), { recursive: true, mode: 0o700 })
      await writeFile(staged, 'payload')
      const result = await finalizeArtifact({ artifact: artifact(), stagedPath: staged, finalPath: released, scanner, now: NOW })
      assert.equal(result.decision.releaseAllowed, false)
      assert.equal(result.stagedPathRetained, true)
      await stat(staged)
      await assert.rejects(() => stat(released), { code: 'ENOENT' })
    } finally {
      await rm(dir, { recursive: true, force: true })
    }
  }
})

let dataDir
let storeFile
let deleteFile
let getFileStorageUsage
let listFiles
let createWorkspace
let updateWorkspace
let getWorkspace
let detachFileFromWorkspaces

before(async () => {
  dataDir = await mkdtemp(path.join(os.tmpdir(), 'goreecloud-ai-files-'))
  process.env.GOREECLOUD_AI_DATA_DIR = dataDir
  ;({ storeFile, deleteFile, getFileStorageUsage, listFiles } = await import(`./files.mjs?test=${Date.now()}`))
  ;({ createWorkspace, updateWorkspace, getWorkspace, detachFileFromWorkspaces } = await import(`./workspaces.mjs?test=${Date.now()}`))
})

after(async () => {
  delete process.env.GOREECLOUD_AI_DATA_DIR
  await rm(dataDir, { recursive: true, force: true })
})

function uploadRequest(bytes, headers = {}) {
  const request = Readable.from([Buffer.from(bytes)])
  request.headers = {
    'x-file-name': encodeURIComponent('report.txt'),
    'content-type': 'text/plain',
    'content-length': String(Buffer.byteLength(bytes)),
    ...headers,
  }
  return request
}

test('native upload storage remains staged and unverified without a Wardveil transport', async () => {
  const record = await storeFile(uploadRequest('unverified'), 1024, null)
  assert.equal(record.status, 'unverified')
  assert.equal(record.storageState, 'staged')
  assert.equal(record.security.releaseAllowed, false)
  assert.ok(record.security.reasonCodes.includes('wardveil_scan_unavailable_or_error'))
  assert.equal((await readFile(path.join(dataDir, 'staging', 'files', record.id), 'utf8')), 'unverified')
  await assert.rejects(() => stat(path.join(dataDir, 'files', record.id)), { code: 'ENOENT' })
  assert.equal((await stat(path.join(dataDir, 'staging', 'files'))).mode & 0o777, 0o700)
})

test('native upload storage releases bytes only after a clean Wardveil decision', async () => {
  const scanner = {
    async scanStagedFile({ artifact: item, digestSha256 }) {
      const now = new Date()
      return {
        resource_id: artifactResourceId(item),
        resource_digest_sha256: digestSha256,
        scan_record: {
          contract_version: '0.1.0',
          record_type: 'scan_finding',
          record_id: 'scan-live-test',
          producer: { id: 'wardveil-test', authoritative: true },
          scope: { resource_type: 'ai_artifact', resource_id: artifactResourceId(item) },
          scan_result: 'clean',
          observed_at: new Date(now.getTime() - 1_000).toISOString(),
          valid_until: new Date(now.getTime() + 60_000).toISOString(),
          evidence_refs: ['evidence:test-scanner', 'evidence:test-scan'],
        },
      }
    },
  }
  const record = await storeFile(uploadRequest('verified'), 1024, scanner)
  assert.equal(record.status, 'available')
  assert.equal(record.storageState, 'released')
  assert.equal(record.security.releaseAllowed, true)
  assert.equal(record.security.useAsContextAllowed, true)
  assert.equal((await readFile(path.join(dataDir, 'files', record.id), 'utf8')), 'verified')
  await assert.rejects(() => stat(path.join(dataDir, 'staging', 'files', record.id)), { code: 'ENOENT' })
})

test('attachment quotas fail before creating additional stored state', async () => {
  const before = await getFileStorageUsage()
  await assert.rejects(
    () => storeFile(uploadRequest('count-blocked'), 1024, null, { maxFileCount: before.fileCount, maxTotalBytes: before.totalBytes + 1024 }),
    (error) => error?.status === 507 && /file-count quota/.test(error.message),
  )
  assert.deepEqual(await getFileStorageUsage(), before)

  await assert.rejects(
    () => storeFile(uploadRequest('bytes-blocked'), 1024, null, { maxFileCount: before.fileCount + 10, maxTotalBytes: before.totalBytes + 2 }),
    (error) => error?.status === 507 && /storage-byte quota/.test(error.message),
  )
  assert.deepEqual(await getFileStorageUsage(), before)
})

test('file deletion can reconcile Workspace file references', async () => {
  const [record] = await listFiles()
  assert.ok(record)
  const workspace = await createWorkspace({ name: 'Files' })
  await updateWorkspace(workspace.id, { fileIds: [record.id, record.id] })
  assert.deepEqual((await getWorkspace(workspace.id)).fileIds, [record.id])

  assert.equal(await deleteFile(record.id), true)
  assert.equal(await detachFileFromWorkspaces(record.id), 1)
  assert.deepEqual((await getWorkspace(workspace.id)).fileIds, [])
  assert.equal((await listFiles()).some((file) => file.id === record.id), false)
  await assert.rejects(() => stat(path.join(dataDir, 'files', record.id)), { code: 'ENOENT' })
  await assert.rejects(() => stat(path.join(dataDir, 'staging', 'files', record.id)), { code: 'ENOENT' })
})
