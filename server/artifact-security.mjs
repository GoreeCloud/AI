import { createHash } from 'node:crypto'
import { createReadStream } from 'node:fs'
import { mkdir, rename, stat } from 'node:fs/promises'
import { dirname } from 'node:path'

export const WARDVEIL_RUNTIME_CONTRACT_VERSION = '0.1.0'
export const EXPECTED_RESOURCE_TYPE = 'ai_artifact'
export const ARTIFACT_KINDS = new Set([
  'chat_upload',
  'knowledge_document',
  'imported_asset',
  'model_artifact',
  'tool_artifact',
  'generated_file',
])
const SCAN_RESULTS = new Set(['clean', 'suspicious', 'malicious', 'unknown', 'unsupported'])

export function artifactResourceId(artifact) {
  return `ai:${artifact.contextId}:artifact:${artifact.artifactId}`
}

export function validateArtifact(artifact) {
  if (!artifact?.contextId || !artifact?.artifactId) throw new Error('artifact_identity_required')
  if (!ARTIFACT_KINDS.has(artifact.artifactKind)) throw new Error('unsupported_artifact_kind')
}

export async function sha256File(filePath) {
  const digest = createHash('sha256')
  for await (const chunk of createReadStream(filePath)) digest.update(chunk)
  return digest.digest('hex')
}

function blocked(reason, { recordId = null, evidenceRefs = [] } = {}) {
  return {
    disposition: 'blocked_unverified',
    releaseAllowed: false,
    useAsContextAllowed: false,
    quarantineRequired: false,
    reasonCodes: [reason],
    evidenceRefs,
    scanRecordId: recordId,
  }
}

function parseInstant(value) {
  if (typeof value !== 'string' || !value) return null
  const instant = new Date(value)
  return Number.isFinite(instant.getTime()) ? instant : null
}

export function evaluateArtifactScan(artifact, digestSha256, envelope, now = new Date()) {
  validateArtifact(artifact)
  const resourceId = artifactResourceId(artifact)
  const observedNow = now instanceof Date ? now : new Date(now)
  if (!Number.isFinite(observedNow.getTime())) throw new Error('invalid_now')

  if (envelope?.resource_id !== resourceId) return blocked('resource_binding_mismatch')
  if (String(envelope?.resource_digest_sha256 ?? '').toLowerCase() !== digestSha256.toLowerCase()) return blocked('content_digest_mismatch')

  const record = envelope?.scan_record && typeof envelope.scan_record === 'object' ? envelope.scan_record : {}
  const recordId = typeof record.record_id === 'string' ? record.record_id : null
  const evidenceRefs = Array.isArray(record.evidence_refs) ? record.evidence_refs.filter((ref) => typeof ref === 'string' && ref) : []
  const evidence = { recordId, evidenceRefs }

  if (record.contract_version !== WARDVEIL_RUNTIME_CONTRACT_VERSION) return blocked('unsupported_wardveil_runtime_contract', evidence)
  if (record.record_type !== 'scan_finding') return blocked('unexpected_wardveil_record_type', evidence)
  if (!record.producer || typeof record.producer !== 'object' || record.producer.authoritative !== true || !record.producer.id) return blocked('non_authoritative_scan_record', evidence)
  if (!record.scope || typeof record.scope !== 'object') return blocked('missing_scan_scope', evidence)
  if (record.scope.resource_type !== EXPECTED_RESOURCE_TYPE || record.scope.resource_id !== resourceId) return blocked('scan_scope_mismatch', evidence)
  if (!SCAN_RESULTS.has(record.scan_result)) return blocked('unsupported_scan_result', evidence)

  const observedAt = parseInstant(record.observed_at)
  const validUntil = parseInstant(record.valid_until)
  if (!observedAt || !validUntil) return blocked('invalid_scan_evidence_time', evidence)
  if (observedAt > observedNow) return blocked('future_dated_scan_evidence', evidence)
  if (validUntil <= observedAt) return blocked('invalid_scan_validity_window', evidence)

  if (record.scan_result === 'malicious') {
    const reasonCodes = ['wardveil_scan_malicious']
    if (observedNow > validUntil) reasonCodes.push('expired_malicious_evidence_remains_blocking_for_bound_digest')
    return {
      disposition: 'block_quarantine',
      releaseAllowed: false,
      useAsContextAllowed: false,
      quarantineRequired: true,
      reasonCodes,
      evidenceRefs,
      scanRecordId: recordId,
    }
  }

  if (record.scan_result === 'suspicious') {
    return {
      disposition: 'hold_review',
      releaseAllowed: false,
      useAsContextAllowed: false,
      quarantineRequired: false,
      reasonCodes: ['wardveil_scan_suspicious'],
      evidenceRefs,
      scanRecordId: recordId,
    }
  }

  if (record.scan_result === 'unknown' || record.scan_result === 'unsupported') {
    return blocked(`wardveil_scan_${record.scan_result}`, evidence)
  }
  if (evidenceRefs.length === 0) return blocked('clean_scan_missing_evidence_refs', { recordId })
  if (observedNow > validUntil) return blocked('clean_scan_evidence_expired', evidence)

  return {
    disposition: 'allow',
    releaseAllowed: true,
    useAsContextAllowed: ['chat_upload', 'knowledge_document', 'imported_asset'].includes(artifact.artifactKind),
    quarantineRequired: false,
    reasonCodes: ['wardveil_scan_clean_current'],
    evidenceRefs,
    scanRecordId: recordId,
  }
}

export function quarantineHandoff(artifact, decision) {
  if (!decision?.quarantineRequired) return null
  return {
    action: 'quarantine',
    scope: { resource_type: EXPECTED_RESOURCE_TYPE, resource_id: artifactResourceId(artifact) },
    source_scan_record_id: decision.scanRecordId,
    evidence_refs: decision.evidenceRefs,
    requires_explicit_executor_authority: true,
    destructive_action: false,
  }
}

export async function finalizeArtifact({ artifact, stagedPath, finalPath, scanner, now = new Date() }) {
  validateArtifact(artifact)
  if (stagedPath === finalPath) return { decision: blocked('staging_and_final_path_must_differ'), releasedPath: null, stagedPathRetained: await exists(stagedPath), digestSha256: null }
  if (!(await isFile(stagedPath))) return { decision: blocked('staged_artifact_unavailable'), releasedPath: null, stagedPathRetained: false, digestSha256: null }
  if (await exists(finalPath)) return { decision: blocked('final_destination_already_exists'), releasedPath: null, stagedPathRetained: true, digestSha256: null }

  const beforeDigest = await sha256File(stagedPath)
  if (!scanner || typeof scanner.scanStagedFile !== 'function') {
    return { decision: blocked('wardveil_scan_unavailable_or_error'), releasedPath: null, stagedPathRetained: true, digestSha256: beforeDigest }
  }

  let envelope
  try {
    envelope = await scanner.scanStagedFile({ artifact, stagedPath, digestSha256: beforeDigest })
  } catch {
    return { decision: blocked('wardveil_scan_unavailable_or_error'), releasedPath: null, stagedPathRetained: true, digestSha256: beforeDigest }
  }

  const decision = evaluateArtifactScan(artifact, beforeDigest, envelope, now)
  if (!decision.releaseAllowed) return { decision, releasedPath: null, stagedPathRetained: true, digestSha256: beforeDigest }

  const afterDigest = await sha256File(stagedPath)
  if (afterDigest !== beforeDigest) {
    return { decision: blocked('staged_artifact_changed_during_verification'), releasedPath: null, stagedPathRetained: true, digestSha256: beforeDigest }
  }

  try {
    await mkdir(dirname(finalPath), { recursive: true, mode: 0o700 })
    await rename(stagedPath, finalPath)
  } catch {
    return { decision: blocked('artifact_release_failed'), releasedPath: null, stagedPathRetained: await exists(stagedPath), digestSha256: beforeDigest }
  }

  return { decision, releasedPath: finalPath, stagedPathRetained: false, digestSha256: beforeDigest }
}

async function exists(filePath) {
  try { await stat(filePath); return true } catch (error) { if (error?.code === 'ENOENT') return false; throw error }
}

async function isFile(filePath) {
  try { return (await stat(filePath)).isFile() } catch (error) { if (error?.code === 'ENOENT') return false; throw error }
}
