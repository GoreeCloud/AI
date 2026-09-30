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
const entry = fileURLToPath(new URL('../scripts/validate-model-routing.mjs', import.meta.url))
const policy = {
  source: 'server-local-config',
  revision: 'dev:operator-1',
  observedAt: new Date(Date.now() - 30000).toISOString(),
  expiresAt: new Date(Date.now() + 300000).toISOString(),
  approvedModels: [
    { name: 'gemma3:12b', family: 'gemma', roles: ['general', 'writing'] },
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['coding'] },
  ],
}

async function invoke(extra = {}) {
  const settings = {
    ...process.env,
    VALIDATE_MODEL_ROUTING: 'local-development-only',
    VALIDATE_MODEL_ROLE: 'coding',
    VALIDATE_MODEL_TIMEOUT_MS: '3000',
    ...extra,
  }
  try {
    const { stdout, stderr } = await exec(process.execPath, [entry], {
      env: settings, timeout: 8000, maxBuffer: 65536,
    })
    return { exit: 0, output: JSON.parse(stdout), stderr }
  } catch (error) {
    return { exit: error.code, output: JSON.parse(error.stdout), stderr: error.stderr }
  }
}

async function withPolicy(fn, content) {
  const dir = await mkdtemp(join(tmpdir(), 'ai-model-cli-'))
  const path = join(dir, 'policy.json')
  try {
    await writeFile(path, content ?? JSON.stringify(policy), { mode: 0o600 })
    return await fn(path)
  } finally {
    await rm(dir, { recursive: true, force: true })
  }
}

async function withRuntime(fn, handler = (_req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' })
  res.end(JSON.stringify({ models: [
    { name: 'gemma3:12b' },
    { name: 'qwen3-coder:latest' },
  ] }))
}) {
  const server = http.createServer(handler)
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  try {
    return await fn('http://127.0.0.1:' + server.address().port)
  } finally {
    await new Promise((resolve, reject) =>
      server.close(error => error ? reject(error) : resolve()))
  }
}

test('refuses execution without explicit development opt-in', async () => {
  const result = await invoke({
    VALIDATE_MODEL_ROUTING: '',
    VALIDATE_MODEL_POLICY_PATH: '/no/such/path',
  })
  assert.equal(result.exit, 2)
  assert.deepEqual(result.output, {
    status: 'invalid', reason: 'explicit_local_development_opt_in_required',
  })
  assert.equal(result.stderr, '')
})

test('requires a configured absolute policy file path and role', async () => {
  const absent = await invoke({ VALIDATE_MODEL_POLICY_PATH: '' })
  const relative = await invoke({ VALIDATE_MODEL_POLICY_PATH: './policy.json' })
  const missingRole = await invoke({ VALIDATE_MODEL_POLICY_PATH: '/no/such/path', VALIDATE_MODEL_ROLE: '' })
  for (const result of [absent, relative, missingRole]) {
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'invalid_local_diagnostic_configuration')
  }
})

test('selects only approved installed model via the read-only loopback endpoint', async () => {
  await withPolicy(async path => withRuntime(async url => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      VALIDATE_MODEL_RUNTIME_URL: url,
    })
    assert.equal(result.exit, 0)
    assert.deepEqual(result.output, {
      status: 'selected', role: 'coding', model: 'qwen3-coder:latest',
      family: 'qwen', selection: 'automatic', policyRevision: 'dev:operator-1',
      policyTrust: 'development-unverified', processingZone: 'local-only-intended',
      inferenceAuthorized: false,
    })
    assert.equal(result.stderr, '')
  }))
})

test('never issues inference, chat, embeddings or an unrelated runtime call', async () => {
  const paths = []
  await withPolicy(async path => withRuntime(async url => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      VALIDATE_MODEL_RUNTIME_URL: url,
    })
    assert.equal(result.exit, 0)
    assert.deepEqual(paths, ['/api/tags'])
  }, (req, res) => {
    paths.push(req.url)
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }] }))
  }))
})

test('does not override approvals for an explicitly selected incompatible model', async () => {
  await withPolicy(async path => withRuntime(async url => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path, VALIDATE_MODEL_RUNTIME_URL: url,
      VALIDATE_MODEL_PREFERRED: 'gemma3:12b',
    })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'preferred_model_not_approved_and_installed_for_role')
    assert.equal(result.output.model, undefined)
  }))
})

test('rejects missing or malformed local policies without contacting discovery', async () => {
  let reads = 0
  await withPolicy(async path => withRuntime(async url => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      VALIDATE_MODEL_RUNTIME_URL: url,
    })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'server_model_policy_unavailable')
    assert.equal(reads, 0)
    assert.equal(result.stderr, '')
  }, (_req, res) => { reads++; res.end('{}') }), 'this is not JSON')
})

test('rejects invalid roles before accessing local policy or runtime', async () => {
  const result = await invoke({
    VALIDATE_MODEL_POLICY_PATH: '/no/such/policy',
    VALIDATE_MODEL_ROLE: 'administrator',
  })
  assert.equal(result.exit, 2)
  assert.equal(result.output.reason, 'invalid_routing_request')
})

test('rejects external runtime targets without exposing their URLs', async () => {
  await withPolicy(async path => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      VALIDATE_MODEL_RUNTIME_URL: 'http://192.0.2.123:11434',
    })
    assert.equal(result.exit, 2)
    assert.deepEqual(result.output, {
      status: 'unavailable', reason: 'local_diagnostic_configuration_unavailable',
    })
    assert.ok(!JSON.stringify(result).includes('192.0.2.123'))
  })
})

test('handles invalid timeout input before touching policy or runtime', async () => {
  for (const timeout of ['0', '30001', '50ms', 'Infinity', '-1']) {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: '/no/such/policy',
      VALIDATE_MODEL_TIMEOUT_MS: timeout,
    })
    assert.equal(result.output.reason, 'invalid_local_diagnostic_configuration')
  }
})

test('does not print private policy content on refusal', async () => {
  const secret = 'DO-NOT-LEAK-LOCAL-POLICY-SECRET'
  await withPolicy(async path => {
    const result = await invoke({ VALIDATE_MODEL_POLICY_PATH: path })
    assert.equal(result.exit, 2)
    assert.equal(result.stderr, '')
    assert.ok(!JSON.stringify(result).includes(secret))
    assert.ok(!JSON.stringify(result).includes(path))
  }, secret)
})
