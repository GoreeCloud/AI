import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, chmod, symlink, link, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import http from 'node:http'
import { createLocalPolicyLoader, createLoopbackModelDiscovery } from './model-local-adapters.mjs'
import { createModelRoutePreflight } from './model-route-preflight.mjs'

const WHEN = Date.parse('2026-09-23T09:00:00Z')
const policy = {
  source: 'server-local-config', revision: 'dev:1',
  observedAt: '2026-09-23T08:59:00Z', expiresAt: '2026-09-23T09:59:00Z',
  approvedModels: [
    { name: 'gemma3:12b', family: 'gemma', roles: ['general', 'reasoning'] },
    { name: 'qwen3-coder:latest', family: 'qwen', roles: ['coding'] },
  ],
}
async function withPrivateFile(run, contents = JSON.stringify(policy)) {
  const root = await mkdtemp(join(tmpdir(), 'gc-ai-adapter-'))
  try {
    const target = join(root, 'policy.json')
    await writeFile(target, contents, { mode: 0o600 })
    await chmod(target, 0o600)
    return await run({ root, target })
  } finally {
    await rm(root, { recursive: true, force: true })
  }
}
async function withLocalServer(handler, run) {
  const server = http.createServer(handler)
  await new Promise((resolveReady, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolveReady)
  })
  try {
    const address = server.address()
    return await run(`http://127.0.0.1:${address.port}`)
  } finally {
    await new Promise((resolveClose, reject) => server.close((error) => error ? reject(error) : resolveClose()))
  }
}
const models = [{ name: 'gemma3:12b', size: 12345 }, { name: 'qwen3-coder:latest', details: {} }]

test('reads private regular server file, then composes with actual loopback discovery', async () => {
  await withPrivateFile(async ({ target }) => {
    await withLocalServer((_req, response) => {
      response.writeHead(200, { 'Content-Type': 'application/json' })
      response.end(JSON.stringify({ models }))
    }, async (baseUrl) => {
      const prepare = createModelRoutePreflight({
        loadPolicy: createLocalPolicyLoader({ policyPath: target }),
        discoverModels: createLoopbackModelDiscovery({ baseUrl }),
        now: () => WHEN,
      })
      const general = await prepare({ role: 'general' })
      const coding = await prepare({ role: 'coding' })
      assert.equal(general.model, 'gemma3:12b')
      assert.equal(coding.model, 'qwen3-coder:latest')
      assert.equal(general.inferenceAuthorized, false)
      assert.equal(general.policyTrust, 'development-unverified')
      assert.equal((await prepare({ role: 'vision' })).status, 'unavailable')
    })
  })
})

test('requires an absolute policy path and rejects final-file symlinks', async () => {
  assert.throws(() => createLocalPolicyLoader({ policyPath: './policy.json' }), TypeError)
  await withPrivateFile(async ({ root, target }) => {
    const alias = join(root, 'symlink.json')
    await symlink(target, alias)
    await assert.rejects(createLocalPolicyLoader({ policyPath: alias })(), { code: 'ELOOP' })
  })
})

test('rejects symlinked parent directories and hard-linked policy input', async () => {
  await withPrivateFile(async ({ root, target }) => {
    const aliasDir = join(root, 'alias')
    await symlink(root, aliasDir)
    await assert.rejects(createLocalPolicyLoader({ policyPath: join(aliasDir, 'policy.json') })(), /policy_parent_not_canonical/)
    const hard = join(root, 'policy-hard.json')
    await link(target, hard)
    await assert.rejects(createLocalPolicyLoader({ policyPath: target })(), /invalid_local_policy_file/)
  })
})

test('rejects group-readable policy file and directories masquerading as files', async () => {
  await withPrivateFile(async ({ root, target }) => {
    await chmod(target, 0o640)
    await assert.rejects(createLocalPolicyLoader({ policyPath: target })(), /invalid_local_policy_file/)
    const directory = join(root, 'directory.json')
    await mkdir(directory)
    await assert.rejects(createLocalPolicyLoader({ policyPath: directory })(), /invalid_local_policy_file/)
  })
})

test('rejects oversize and malformed local policies without exposing contents', async () => {
  await withPrivateFile(async ({ target }) => {
    await writeFile(target, 'x'.repeat(1025), { mode: 0o600 })
    await assert.rejects(createLocalPolicyLoader({ policyPath: target, maxBytes: 1024 })(), /invalid_local_policy_file/)
    await writeFile(target, 'not JSON', { mode: 0o600 })
    await assert.rejects(createLocalPolicyLoader({ policyPath: target, maxBytes: 1024 })(), SyntaxError)
  })
})

test('rejects local policy reads when cancelled', async () => {
  await withPrivateFile(async ({ target }) => {
    const abort = new AbortController()
    abort.abort()
    await assert.rejects(createLocalPolicyLoader({ policyPath: target })({ signal: abort.signal }), /policy_read_cancelled/)
  })
})

test('rejects non-loopback URLs, DNS names, credentials, redirects, paths, and fragments before fetching', () => {
  for (const baseUrl of [
    'http://localhost:11434', 'https://127.0.0.1:11434',
    'http://192.168.1.2:11434', 'http://127.0.0.1.evil.tld:11434',
    'http://127.0.0.1:11434/other', 'http://127.0.0.1:11434/?url=x',
    'http://user:pass@127.0.0.1:11434', 'http://127.0.0.1:11434/#fragment',
  ]) assert.throws(() => createLoopbackModelDiscovery({ baseUrl }), TypeError)
})

test('strips discovery metadata instead of inferring capabilities', async () => {
  await withLocalServer((_req, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ models }))
  }, async (baseUrl) => {
    const found = await createLoopbackModelDiscovery({ baseUrl })()
    assert.deepEqual(found, [{ name: 'gemma3:12b' }, { name: 'qwen3-coder:latest' }])
  })
})

test('rejects a redirect without reaching its destination', async () => {
  await withLocalServer((_req, response) => {
    response.writeHead(302, { Location: 'http://169.254.169.254/latest/meta-data/' })
    response.end()
  }, async (baseUrl) => {
    await assert.rejects(createLoopbackModelDiscovery({ baseUrl })())
  })
})

test('rejects oversized streamed discovery even without Content-Length', async () => {
  await withLocalServer((_req, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ models: [{ name: 'x'.repeat(1024) }] }))
  }, async (baseUrl) => {
    await assert.rejects(createLoopbackModelDiscovery({ baseUrl, maxBytes: 200 })(), /local_model_catalog_exceeds_limit/)
  })
})

test('rejects too-large advertised discovery response before streaming', async () => {
  await withLocalServer((_req, response) => {
    response.writeHead(200, { 'Content-Type': 'application/json', 'Content-Length': '1000000' })
    response.end()
  }, async (baseUrl) => {
    await assert.rejects(createLoopbackModelDiscovery({ baseUrl, maxBytes: 1000 })(), /local_model_catalog_exceeds_limit/)
  })
})

test('rejects server errors, malformed UTF-8, and invalid JSON model catalogs', async () => {
  for (const [status, payload] of [
    [503, '{"models":[]}'], [200, Buffer.from([0xff, 0xfe])],
    [200, '{"models":null}'], [200, '{"models":'],
  ]) {
    await withLocalServer((_req, response) => {
      response.writeHead(status, { 'Content-Type': 'application/json' })
      response.end(payload)
    }, async (baseUrl) => {
      await assert.rejects(createLoopbackModelDiscovery({ baseUrl })())
    })
  }
})

test('does not call fetch if the discovery request is pre-aborted', async () => {
  let calls = 0
  const abort = new AbortController()
  abort.abort()
  const discover = createLoopbackModelDiscovery({
    fetchImpl: () => { calls++; throw new Error('must not fetch') },
  })
  await assert.rejects(discover({ signal: abort.signal }), /model_discovery_cancelled/)
  assert.equal(calls, 0)
})

test('rejects unsafe size limits and non-function fetch adapters', () => {
  assert.throws(() => createLocalPolicyLoader({ policyPath: resolve('/tmp/x'), maxBytes: 1024 * 1024 }), TypeError)
  assert.throws(() => createLoopbackModelDiscovery({ maxBytes: 0 }), TypeError)
  assert.throws(() => createLoopbackModelDiscovery({ fetchImpl: null }), TypeError)
})
