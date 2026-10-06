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
const entry = fileURLToPath(new URL('../scripts/validate-approved-model-runtime.mjs', import.meta.url))
const iso = delta => new Date(Date.now() + delta).toISOString()
const policy = () => ({
  source: 'server-local-config', revision: 'dev:runtime-1',
  observedAt: iso(-30_000), expiresAt: iso(300_000),
  approvedModels: [
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['coding'] },
    { name: 'gemma3:12b', family: 'gemma', roles: ['general'] },
  ],
})

async function withPolicy(action, content = JSON.stringify(policy())) {
  const dir = await mkdtemp(join(tmpdir(), 'gc-approved-runtime-'))
  const path = join(dir, 'policy.json')
  try {
    await writeFile(path, content, { mode: 0o600 })
    return await action(path)
  } finally { await rm(dir, { recursive: true, force: true }) }
}

async function withApplication(action, handler) {
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
        VALIDATE_APPROVED_MODEL_RUNTIME: 'local-development-only',
        VALIDATE_MODEL_ROLE: 'coding',
        VALIDATE_MODEL_PREFERRED: 'qwen3-coder:latest',
        VALIDATE_APPROVED_MODEL_RUNTIME_TIMEOUT_MS: '3000',
        ...extra,
      },
      timeout: 8000,
      maxBuffer: 65536,
    })
    return { exit: 0, output: JSON.parse(stdout), stderr }
  } catch (error) {
    return { exit: error.code, output: JSON.parse(error.stdout), stderr: error.stderr }
  }
}

function normalHandler(observed = []) {
  return async (req, res) => {
    observed.push({ method: req.method, url: req.url, authorization: req.headers.authorization })
    if (req.url === '/api/health') {
      res.setHeader('Content-Type', 'application/json')
      return res.end(JSON.stringify({ status: 'ok', service: 'goreecloud-ai', wardveilArtifactScanner: 'unconfigured' }))
    }
    if (req.url === '/api/ollama/models') {
      res.setHeader('Content-Type', 'application/json')
      return res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }, { name: 'gemma3:12b' }] }))
    }
    if (req.url === '/api/ollama/chat') {
      let body = ''
      for await (const chunk of req) body += chunk
      const parsed = JSON.parse(body)
      assert.equal(parsed.model, 'qwen3-coder:latest')
      assert.equal(parsed.messages.length, 1)
      res.setHeader('Content-Type', 'application/x-ndjson')
      res.write(JSON.stringify({ message: { role: 'assistant', content: 'PRIVATE GENERATED CONTENT' }, done: false }) + '\n')
      return res.end(JSON.stringify({ message: { role: 'assistant', content: 'ok' }, done: true }) + '\n')
    }
    res.statusCode = 404
    res.end()
  }
}

test('requires explicit opt-in', async () => {
  const result = await invoke({
    VALIDATE_APPROVED_MODEL_RUNTIME: '',
    VALIDATE_MODEL_POLICY_PATH: '/no/such/policy',
  })
  assert.equal(result.exit, 2)
  assert.deepEqual(result.output, { status: 'invalid', reason: 'explicit_local_development_opt_in_required' })
  assert.equal(result.stderr, '')
})

test('rejects missing policy, role, preferred model or invalid timeout before network I/O', async () => {
  for (const extra of [
    { VALIDATE_MODEL_POLICY_PATH: '' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_ROLE: '' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_MODEL_PREFERRED: '' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_APPROVED_MODEL_RUNTIME_TIMEOUT_MS: '0' },
    { VALIDATE_MODEL_POLICY_PATH: '/none', VALIDATE_APPROVED_MODEL_RUNTIME_TIMEOUT_MS: '120001' },
  ]) {
    const result = await invoke(extra)
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'invalid_local_runtime_validation_configuration')
  }
})

test('rejects non-loopback application targets without exposing the URL', async () => {
  await withPolicy(async path => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      GOREECLOUD_AI_URL: 'http://192.0.2.55:8787',
    })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'invalid_local_application_url')
    assert.ok(!JSON.stringify(result).includes('192.0.2.55'))
  })
})

test('validates one approved streamed model request and emits sanitized evidence', async () => {
  const observed = []
  await withPolicy(async path => withApplication(async url => {
    const secret = 'DEVELOPMENT-TOKEN-DO-NOT-PRINT'
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      GOREECLOUD_AI_URL: url,
      GOREECLOUD_AI_API_TOKEN: secret,
    })
    assert.equal(result.exit, 0)
    assert.equal(result.stderr, '')
    assert.equal(result.output.status, 'validated')
    assert.equal(result.output.role, 'coding')
    assert.equal(result.output.model, 'qwen3-coder:latest')
    assert.equal(result.output.policyRevision, 'dev:runtime-1')
    assert.equal(result.output.runtimeValidated, true)
    assert.equal(result.output.validationScope, 'one-approved-streamed-request-only')
    assert.equal(result.output.productionInferenceAuthorized, false)
    assert.equal(result.output.productionAccepted, false)
    assert.equal(result.output.stableQualified, false)
    assert.ok(result.output.contentChunks >= 1)
    assert.ok(result.output.streamEvents >= 2)
    assert.ok(!JSON.stringify(result).includes('PRIVATE GENERATED CONTENT'))
    assert.ok(!JSON.stringify(result).includes(secret))
    assert.ok(!JSON.stringify(result).includes(path))
    assert.deepEqual(observed.map(x => [x.method, x.url]), [
      ['GET', '/api/health'],
      ['GET', '/api/ollama/models'],
      ['POST', '/api/ollama/chat'],
    ])
    assert.equal(observed[0].authorization, undefined)
    assert.equal(observed[1].authorization, `Bearer ${secret}`)
    assert.equal(observed[2].authorization, `Bearer ${secret}`)
  }, normalHandler(observed)))
})

test('unapproved preferred model never reaches chat', async () => {
  const observed = []
  await withPolicy(async path => withApplication(async url => {
    const result = await invoke({
      VALIDATE_MODEL_POLICY_PATH: path,
      GOREECLOUD_AI_URL: url,
      VALIDATE_MODEL_PREFERRED: 'gemma3:12b',
    })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'preferred_model_not_approved_and_installed_for_role')
    assert.deepEqual(observed.map(x => x.url), ['/api/health', '/api/ollama/models'])
  }, normalHandler(observed)))
})

test('malformed private policy fails closed without echoing private bytes', async () => {
  const secret = 'PRIVATE-POLICY-CONTENT-DO-NOT-PRINT'
  await withPolicy(async path => withApplication(async url => {
    const result = await invoke({ VALIDATE_MODEL_POLICY_PATH: path, GOREECLOUD_AI_URL: url })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'server_model_policy_unavailable')
    assert.ok(!JSON.stringify(result).includes(secret))
    assert.ok(!JSON.stringify(result).includes(path))
  }, normalHandler([])), secret)
})

test('missing terminal done event fails without printing generated content', async () => {
  await withPolicy(async path => withApplication(async url => {
    const result = await invoke({ VALIDATE_MODEL_POLICY_PATH: path, GOREECLOUD_AI_URL: url })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'stream_missing_terminal_event')
    assert.ok(!JSON.stringify(result).includes('SHOULD-NOT-LEAK'))
  }, async (req, res) => {
    if (req.url === '/api/health') return res.end(JSON.stringify({ status: 'ok', service: 'goreecloud-ai', wardveilArtifactScanner: 'unconfigured' }))
    if (req.url === '/api/ollama/models') return res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }] }))
    if (req.url === '/api/ollama/chat') {
      res.setHeader('Content-Type', 'application/x-ndjson')
      return res.end(JSON.stringify({ message: { content: 'SHOULD-NOT-LEAK' }, done: false }) + '\n')
    }
    res.statusCode = 404; res.end()
  }))
})

test('invalid stream event fails closed and does not expose upstream body', async () => {
  await withPolicy(async path => withApplication(async url => {
    const result = await invoke({ VALIDATE_MODEL_POLICY_PATH: path, GOREECLOUD_AI_URL: url })
    assert.equal(result.exit, 2)
    assert.equal(result.output.reason, 'invalid_stream_event')
    assert.ok(!JSON.stringify(result).includes('UPSTREAM-SECRET'))
  }, async (req, res) => {
    if (req.url === '/api/health') return res.end(JSON.stringify({ status: 'ok', service: 'goreecloud-ai', wardveilArtifactScanner: 'unconfigured' }))
    if (req.url === '/api/ollama/models') return res.end(JSON.stringify({ models: [{ name: 'qwen3-coder:latest' }] }))
    if (req.url === '/api/ollama/chat') {
      res.setHeader('Content-Type', 'application/x-ndjson')
      return res.end('{"error":"UPSTREAM-SECRET"}\n')
    }
    res.statusCode = 404; res.end()
  }))
})
