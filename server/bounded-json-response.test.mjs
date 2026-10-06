import test from 'node:test'
import assert from 'node:assert/strict'
import { readBoundedJsonResponse } from './bounded-json-response.mjs'

test('parses bounded UTF-8 JSON responses', async () => {
  const response = new Response(JSON.stringify({ models: [{ name: 'gemma3' }] }))
  assert.deepEqual(await readBoundedJsonResponse(response, 1024), { models: [{ name: 'gemma3' }] })
})

test('rejects oversized declared and streamed responses', async () => {
  const declared = new Response('{}', { headers: { 'content-length': '2048' } })
  await assert.rejects(() => readBoundedJsonResponse(declared, 1024), /exceeded the configured limit/)

  const streamed = new Response('x'.repeat(1025))
  await assert.rejects(() => readBoundedJsonResponse(streamed, 1024), /exceeded the configured limit/)
})

test('rejects invalid UTF-8 and invalid JSON', async () => {
  await assert.rejects(
    () => readBoundedJsonResponse(new Response(new Uint8Array([0xff])), 1024),
    /invalid UTF-8/,
  )
  await assert.rejects(
    () => readBoundedJsonResponse(new Response('{'), 1024),
    /invalid JSON/,
  )
})
