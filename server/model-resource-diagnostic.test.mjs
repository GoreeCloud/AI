import test from 'node:test'
import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { mkdtemp, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import http from 'node:http'

const exec = promisify(execFile)
const entry = fileURLToPath(new URL('../scripts/validate-model-resource.mjs', import.meta.url))
const iso = delta => new Date(Date.now() + delta).toISOString()
const policy = () => ({
  source: 'server-local-config', revision: 'dev:1',
  observedAt: iso(-30000), expiresAt: iso(300000),
  approvedModels: [
    { name: 'gemma3:12b', family: 'gemma', roles: ['general'] },
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['coding'] },
  ],
})
const profile = () => ({
  source: 'operator-reviewed-development', revision: 'dev:profile1',
  model: 'qwen3-coder:latest', supportedRoles: ['coding'], inputModalities: ['text'],
  contextWindowTokens: 8192, estimatedResidentMemoryMiB: 1,
  supportsToolCalling: false, observedAt: iso(-30000), expiresAt: iso(300000),
})
async function withFiles(action, policyContent, profileContent) {
  const dir = await mkdtemp(join(tmpdir(), 'gc-resource-cli-'))
  const policyPath = join(dir, 'policy.json')
  const profilePath = join(dir, 'profile.json')
  try {
    await writeFile(policyPath, policyContent ?? JSON.stringify(policy()), { mode: 0o600 })
    await writeFile(profilePath, profileContent ?? JSON.stringify(profile()), { mode: 0o600 })
    return await action({ policyPath, profilePath })
  } finally { await rm(dir, { recursive: true, force: true }) }
}
async function withLocalTags(action, handler = (req, res) => {
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }, { name: 'gemma3:12b' }] }))
}) {
  const server = http.createServer(handler)
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  try { return await action('http://127.0.0.1:' + server.address().port) }
  finally { await new Promise((resolve, reject) => server.close(e => e ? reject(e) : resolve())) }
}
async function invoke(extra = {}) {
  try {
    const { stdout, stderr } = await exec(process.execPath, [entry], {
      env: {
        ...process.env,
        VALIDATE_MODEL_RESOURCE: 'local-development-only',
        VALIDATE_MODEL_ROLE: 'coding',
        VALIDATE_RESOURCE_SAFETY_RESERVE_MIB: '0',
        ...extra,
      }, timeout: 8000, maxBuffer: 65536,
    })
    return { exit: 0, output: JSON.parse(stdout), stderr }
  } catch (e) {
    return { exit: e.code, output: JSON.parse(e.stdout), stderr: e.stderr }
  }
}
const valid = async (extra = {}, handler) => withFiles(({ policyPath, profilePath }) =>
  withLocalTags(url => invoke({ VALIDATE_MODEL_POLICY_PATH: policyPath,
    VALIDATE_MODEL_PROFILE_PATH: profilePath, VALIDATE_MODEL_RUNTIME_URL: url, ...extra }), handler))

test('requires deliberate development opt-in and refuses positional arguments', async () => {
  const denied = await invoke({ VALIDATE_MODEL_RESOURCE: '', VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PROFILE_PATH: '/none' })
  assert.equal(denied.exit, 2)
  assert.equal(denied.output.reason, 'explicit_local_development_opt_in_required')
})
test('fails before I/O if profile path or numeric configuration is invalid', async () => {
  for (const extra of [
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PROFILE_PATH: './relative' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PROFILE_PATH: '/none', VALIDATE_RESOURCE_INPUT_TOKENS: '0' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PROFILE_PATH: '/none', VALIDATE_RESOURCE_TIMEOUT_MS: 'Infinity' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PROFILE_PATH: '/none', VALIDATE_RESOURCE_MAX_PARALLEL: '1025' },
  ]) {
    const r = await invoke(extra)
    assert.equal(r.exit, 2)
    assert.equal(r.output.reason, 'invalid_local_resource_configuration')
  }
})
test('operator-only end-to-end composition checks local tags and returns non-authorizing estimate', async () => {
  const paths = []
  const r = await valid({}, (req, res) => {
    paths.push([req.method, req.url])
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }] }))
  })
  assert.equal(r.exit, 0)
  assert.deepEqual(paths, [['GET', '/api/tags']])
  assert.deepEqual(r.output, {
    status: 'candidate', model: 'qwen3-coder:latest', role: 'coding',
    profileRevision: 'dev:profile1', fit: 'operator-declared-estimate-only',
    profileTrust: 'development-unverified', capacityTrust: 'development-unverified',
    runtimeValidated: false, inferenceAuthorized: false, toolExecutionAuthorized: false,
  })
  assert.equal(r.stderr, '')
})
test('fails closed on cross-model profile mismatch', async () => {
  await withFiles(({ policyPath, profilePath }) => withLocalTags(async url => {
    const r = await invoke({ VALIDATE_MODEL_POLICY_PATH: policyPath,
      VALIDATE_MODEL_PROFILE_PATH: profilePath, VALIDATE_MODEL_RUNTIME_URL: url })
    assert.equal(r.output.reason, 'invalid_or_unmatched_development_profile')
    assert.equal(r.exit, 2)
  }), undefined, JSON.stringify({ ...profile(), model: 'gemma3:12b' }))
})
test('denies context overrun and declared parallel capacity exhaustion', async () => {
  assert.equal((await valid({ VALIDATE_RESOURCE_INPUT_TOKENS: '8000' })).output.reason, 'declared_context_window_exceeded')
  assert.equal((await valid({ VALIDATE_RESOURCE_ACTIVE_REQUESTS: '1' })).output.reason, 'declared_parallel_capacity_exhausted')
})
test('does not bypass role approval through manual model preference', async () => {
  const r = await valid({ VALIDATE_MODEL_PREFERRED: 'gemma3:12b' })
  assert.equal(r.output.reason, 'preferred_model_not_approved_and_installed_for_role')
  assert.equal(r.output.model, undefined)
})
test('refuses remote runtime destinations, without printing configured URLs', async () => {
  await withFiles(async ({ policyPath, profilePath }) => {
    const r = await invoke({ VALIDATE_MODEL_POLICY_PATH: policyPath,
      VALIDATE_MODEL_PROFILE_PATH: profilePath,
      VALIDATE_MODEL_RUNTIME_URL: 'http://192.0.2.25:11434' })
    assert.equal(r.output.reason, 'local_resource_diagnostic_unavailable')
    assert.ok(!JSON.stringify(r).includes('192.0.2.25'))
  })
})
test('malformed profile never exposes its bytes or configured file path', async () => {
  const secret = 'PRIVATE-PROFILE-DATA-DO-NOT-EMIT'
  await withFiles(async ({ policyPath, profilePath }) => withLocalTags(async url => {
    const r = await invoke({ VALIDATE_MODEL_POLICY_PATH: policyPath,
      VALIDATE_MODEL_PROFILE_PATH: profilePath, VALIDATE_MODEL_RUNTIME_URL: url })
    assert.equal(r.output.reason, 'local_development_profile_unavailable')
    assert.equal(r.stderr, '')
    assert.ok(!JSON.stringify(r).includes(secret))
    assert.ok(!JSON.stringify(r).includes(profilePath))
  }), undefined, secret)
})
test('unapproved model never reaches resource assessment', async () => {
  let hits = 0
  await withFiles(async ({ policyPath, profilePath }) => withLocalTags(async url => {
    const r = await invoke({ VALIDATE_MODEL_POLICY_PATH: policyPath,
      VALIDATE_MODEL_PROFILE_PATH: profilePath, VALIDATE_MODEL_RUNTIME_URL: url,
      VALIDATE_MODEL_ROLE: 'embedding' })
    assert.equal(r.output.status, 'unavailable')
    assert.equal(r.output.reason, 'no_approved_installed_model_for_role')
    assert.equal(hits, 1)
  }, (_req, res) => {
    hits += 1
    res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }] }))
  }))
})
