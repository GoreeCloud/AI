import test from 'node:test'
import assert from 'node:assert/strict'
import { createBoundedOllamaNdjsonParser } from './ollama-stream.mjs'

test('parses split NDJSON chunks and emits only bounded public fields', () => {
  const emitted = []
  const parser = createBoundedOllamaNdjsonParser({
    maxStreamBytes: 4096,
    maxLineBytes: 1024,
    onChunk: (chunk) => emitted.push(chunk),
  })

  parser.push(Buffer.from('{"model":"private","message":{"role":"assistant","content":"hel","thinking":"hidden"}}\n{"mess'))
  parser.push(Buffer.from('age":{"role":"assistant","content":"lo"},"done":false}\n{"done":true,"total_duration":999}\n'))
  parser.finish()

  assert.deepEqual(emitted, [
    { message: { role: 'assistant', content: 'hel' } },
    { message: { role: 'assistant', content: 'lo' } },
    { done: true },
  ])
})

test('accepts a final NDJSON line without a trailing newline', () => {
  const emitted = []
  const parser = createBoundedOllamaNdjsonParser({
    maxStreamBytes: 1024,
    maxLineBytes: 512,
    onChunk: (chunk) => emitted.push(chunk),
  })

  parser.push(Buffer.from('{"message":{"role":"assistant","content":"done"}}'))
  parser.finish()
  assert.deepEqual(emitted, [{ message: { role: 'assistant', content: 'done' } }])
})

test('rejects an incomplete stream when terminal completion is required', () => {
  const parser = createBoundedOllamaNdjsonParser({
    maxStreamBytes: 1024,
    maxLineBytes: 512,
    requireTerminalChunk: true,
    onChunk: () => {},
  })
  parser.push(Buffer.from('{"message":{"role":"assistant","content":"partial"}}\n'))
  assert.throws(() => parser.finish(), /terminal chunk/)
})

test('maps bounded upstream runtime errors to a non-sensitive public error', () => {
  const emitted = []
  const parser = createBoundedOllamaNdjsonParser({
    maxStreamBytes: 1024,
    maxLineBytes: 512,
    onChunk: (chunk) => emitted.push(chunk),
  })

  parser.push(Buffer.from('{"error":"internal runtime path /secret/model"}\n'))
  parser.finish()
  assert.deepEqual(emitted, [{ error: 'Local model runtime reported an error' }])
})

test('rejects invalid roles, invalid JSON and invalid UTF-8', () => {
  const options = { maxStreamBytes: 1024, maxLineBytes: 512, onChunk: () => {} }

  assert.throws(() => {
    const parser = createBoundedOllamaNdjsonParser(options)
    parser.push(Buffer.from('{"message":{"role":"user","content":"no"}}\n'))
  }, /role is invalid/)

  assert.throws(() => {
    const parser = createBoundedOllamaNdjsonParser(options)
    parser.push(Buffer.from('{broken}\n'))
  }, /invalid NDJSON/)

  assert.throws(() => {
    const parser = createBoundedOllamaNdjsonParser(options)
    parser.push(Buffer.from([0xff, 0x0a]))
  }, /invalid UTF-8/)
})

test('rejects oversized lines and total streams', () => {
  assert.throws(() => {
    const parser = createBoundedOllamaNdjsonParser({ maxStreamBytes: 100, maxLineBytes: 8, onChunk: () => {} })
    parser.push(Buffer.from('123456789'))
  }, /line exceeded/)

  assert.throws(() => {
    const parser = createBoundedOllamaNdjsonParser({ maxStreamBytes: 8, maxLineBytes: 8, onChunk: () => {} })
    parser.push(Buffer.from('123456789'))
  }, /stream exceeded/)
})
