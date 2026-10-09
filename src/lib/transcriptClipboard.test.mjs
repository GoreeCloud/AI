import test from 'node:test'
import assert from 'node:assert/strict'
import { writeTranscriptOnRequest } from './transcriptClipboard.ts'

test('only an explicit call creates content and writes to clipboard adapter', async () => {
  let calls = 0
  let actual = ''
  const create = () => { calls++; return '# Transcript' }
  const writer = async content => { actual = content }
  assert.equal(calls, 0)
  assert.equal(await writeTranscriptOnRequest(create, writer), 'copied')
  assert.equal(calls, 1)
  assert.equal(actual, '# Transcript')
})
test('unavailable clipboard fails without reading transcript content', async () => {
  let accessed = false
  assert.equal(await writeTranscriptOnRequest(() => { accessed = true; return 'private' }, undefined), 'unavailable')
  assert.equal(accessed, false)
})
test('empty transcript does not write to clipboard', async () => {
  let wrote = false
  assert.equal(await writeTranscriptOnRequest(() => '', async () => { wrote = true }), 'empty')
  assert.equal(wrote, false)
})
test('clipboard rejection and serialization errors are reported without throwing', async () => {
  assert.equal(await writeTranscriptOnRequest(() => 'private', async () => { throw new Error('denied') }), 'failed')
  assert.equal(await writeTranscriptOnRequest(() => { throw new Error('bad source') }, async () => {}), 'failed')
})
