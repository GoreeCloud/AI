import test from 'node:test'
import assert from 'node:assert/strict'
import { createRuntimeFetch } from './runtime-fetch.mjs'

test('builds bounded runtime requests and refuses redirects', async () => {
  let captured
  const runtimeFetch = createRuntimeFetch({
    baseUrl: 'http://127.0.0.1:11434/',
    timeoutMs: 1000,
    fetchImpl: async (url, init) => {
      captured = { url, init }
      return new Response('{}', { status: 200 })
    },
  })

  const response = await runtimeFetch('/api/tags', {
    headers: { accept: 'application/json' },
    redirect: 'follow',
  })

  assert.equal(response.status, 200)
  assert.equal(captured.url, 'http://127.0.0.1:11434/api/tags')
  assert.equal(captured.init.redirect, 'error')
  assert.ok(captured.init.signal instanceof AbortSignal)
})

test('combines caller cancellation with the runtime deadline', async () => {
  let capturedSignal
  const controller = new AbortController()
  const runtimeFetch = createRuntimeFetch({
    baseUrl: 'http://127.0.0.1:11434',
    timeoutMs: 1000,
    fetchImpl: async (_url, init) => {
      capturedSignal = init.signal
      return new Response('{}', { status: 200 })
    },
  })

  await runtimeFetch('/api/chat', { signal: controller.signal })
  controller.abort()
  assert.equal(capturedSignal.aborted, true)
})

test('rejects invalid runtime fetch configuration and paths', () => {
  assert.throws(() => createRuntimeFetch({ baseUrl: '', timeoutMs: 1000 }), /baseUrl is required/)
  assert.throws(() => createRuntimeFetch({ baseUrl: 'http://127.0.0.1:11434', timeoutMs: 0 }), /positive integer/)
  const runtimeFetch = createRuntimeFetch({ baseUrl: 'http://127.0.0.1:11434', timeoutMs: 1000 })
  assert.throws(() => runtimeFetch('api/tags'), /absolute-path relative/)
})
