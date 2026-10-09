import test from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import path from 'node:path'

async function reserveTestPort() {
  return await new Promise((resolve, reject) => {
    const socket = createServer()
    socket.once('error', reject)
    socket.listen(0, '127.0.0.1', () => {
      const address = socket.address()
      const port = address.port
      socket.close(error => error ? reject(error) : resolve(port))
    })
  })
}

async function startBackend(port, dir, token) {
  const child = spawn(process.execPath, ['server/index.mjs'], {
    cwd: process.cwd(),
    env: { ...process.env, PORT: String(port), GOREECLOUD_AI_DATA_DIR: dir, GOREECLOUD_AI_API_TOKEN: token },
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  let diagnostic = ''
  await new Promise((resolve, reject) => {
    let settled = false
    const finish = (error) => {
      if (settled) return
      settled = true
      clearTimeout(timeout)
      child.stdout.off('data', onData)
      child.off('error', onError)
      child.off('exit', onExit)
      error ? reject(error) : resolve()
    }
    const onData = chunk => {
      diagnostic += String(chunk).slice(0, 1024)
      if (diagnostic.includes('GoreeCloud AI backend listening on')) finish()
    }
    const onError = error => finish(error)
    const onExit = code => finish(new Error('Backend exited before listening: ' + code + ' ' + diagnostic))
    const timeout = setTimeout(() => finish(new Error('Backend did not become ready')), 10000)
    child.stdout.on('data', onData)
    child.on('error', onError)
    child.on('exit', onExit)
  })
  return child
}

async function stopBackend(child) {
  if (!child || child.exitCode !== null) return
  child.kill('SIGTERM')
  await new Promise(resolve => {
    const timeout = setTimeout(() => { child.kill('SIGKILL'); resolve() }, 3000)
    child.once('exit', () => { clearTimeout(timeout); resolve() })
  })
}

test('HTTP create replay is authorized, conflict-safe, private and survives restart', async () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'goreecloud-ai-http-retry-'))
  const port = await reserveTestPort()
  const token = 'isolated-regression-test-token'
  const endpoint = 'http://127.0.0.1:' + port + '/api/conversations'
  const clientRequestId = '123e4567-e89b-42d3-a456-426614174000'
  const input = {
    model: 'local', title: 'First prompt',
    messages: [{ role: 'user', content: 'Hello' }], clientRequestId,
  }
  let child
  const request = (url, method, body, auth = true) => fetch(url, {
    method,
    headers: {
      ...(auth ? { Authorization: 'Bearer ' + token } : {}),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  try {
    child = await startBackend(port, dir, token)
    assert.equal((await request(endpoint, 'GET', null, false)).status, 401)
    assert.equal((await request(endpoint, 'POST', input, false)).status, 401)
    assert.equal((await request(endpoint, 'POST', { ...input, clientRequestId: 'bad' })).status, 400)

    const firstResponse = await request(endpoint, 'POST', input)
    assert.equal(firstResponse.status, 201)
    assert.equal(firstResponse.headers.get('cache-control'), 'no-store')
    const first = await firstResponse.json()
    assert.deepEqual(first.messages, input.messages)
    assert.equal('clientRequestId' in first, false)
    assert.equal('clientRequestSignature' in first, false)

    const duplicates = await Promise.all(Array.from({ length: 6 }, () => request(endpoint, 'POST', input)))
    const replayed = await Promise.all(duplicates.map(async response => {
      assert.equal(response.status, 201)
      return response.json()
    }))
    assert.ok(replayed.every(item => item.id === first.id))
    const conflicting = await request(endpoint, 'POST', {
      ...input, messages: [{ role: 'user', content: 'Changed' }],
    })
    assert.equal(conflicting.status, 409)
    assert.equal((await conflicting.json()).error, 'create_request_conflict')

    const updatedMessages = [...input.messages, { role: 'assistant', content: 'Saved answer' }]
    assert.equal((await request(endpoint + '/' + first.id, 'PATCH', { messages: updatedMessages })).status, 200)
    await stopBackend(child)
    child = null

    child = await startBackend(port, dir, token)
    const afterRestart = await request(endpoint, 'POST', input)
    assert.equal(afterRestart.status, 201)
    const restored = await afterRestart.json()
    assert.equal(restored.id, first.id)
    assert.deepEqual(restored.messages, updatedMessages)
    assert.equal('clientRequestId' in restored, false)
    assert.equal('clientRequestSignature' in restored, false)
    const listResponse = await request(endpoint, 'GET')
    assert.equal(listResponse.status, 200)
    const list = (await listResponse.json()).conversations
    assert.equal(list.length, 1)
    assert.equal(list[0].id, first.id)
    assert.equal(list[0].messageCount, 2)
    assert.equal('clientRequestId' in list[0], false)
    assert.equal('clientRequestSignature' in list[0], false)
  } finally {
    await stopBackend(child)
    rmSync(dir, { recursive: true, force: true })
  }
})
