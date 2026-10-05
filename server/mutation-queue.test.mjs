import test from 'node:test'
import assert from 'node:assert/strict'
import { createMutationQueue } from './mutation-queue.mjs'

test('serializes overlapping mutations in submission order', async () => {
  const withMutation = createMutationQueue()
  const events = []
  let releaseFirst
  const firstGate = new Promise((resolve) => { releaseFirst = resolve })

  const first = withMutation(async () => {
    events.push('first:start')
    await firstGate
    events.push('first:end')
    return 1
  })
  const second = withMutation(async () => {
    events.push('second:start')
    events.push('second:end')
    return 2
  })

  await Promise.resolve()
  assert.deepEqual(events, ['first:start'])
  releaseFirst()
  assert.deepEqual(await Promise.all([first, second]), [1, 2])
  assert.deepEqual(events, ['first:start', 'first:end', 'second:start', 'second:end'])
})

test('releases the queue after a failed mutation', async () => {
  const withMutation = createMutationQueue()
  const failed = withMutation(async () => { throw new Error('expected') })
  const next = withMutation(async () => 'continued')
  await assert.rejects(failed, /expected/)
  assert.equal(await next, 'continued')
})

test('rejects non-function mutation work', async () => {
  const withMutation = createMutationQueue()
  await assert.rejects(() => withMutation(null), /Mutation work must be a function/)
})
