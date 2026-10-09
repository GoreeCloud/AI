import test from 'node:test'
import assert from 'node:assert/strict'
import { runExclusivePreparation } from './exclusivePreparation.ts'

test('a rapid second action cannot enter while the first awaits persistence', async () => {
  const lock = { current: false }
  const transitions = []
  let release
  const first = runExclusivePreparation(lock, v => transitions.push(v), () => new Promise(resolve => { release = resolve }))
  assert.equal(lock.current, true)
  assert.deepEqual(await runExclusivePreparation(lock, v => transitions.push(v), async () => 'duplicate'), { started: false })
  assert.deepEqual(transitions, [true])
  release('first persisted')
  assert.deepEqual(await first, { started: true, value: 'first persisted' })
  assert.deepEqual(transitions, [true, false])
  assert.equal(lock.current, false)
})

test('a failed request releases its lock and retains the original error', async () => {
  const lock = { current: false }
  const error = new Error('create failed')
  await assert.rejects(runExclusivePreparation(lock, () => {}, async () => { throw error }), thrown => thrown === error)
  assert.equal(lock.current, false)
  assert.deepEqual(await runExclusivePreparation(lock, () => {}, async () => 7), { started: true, value: 7 })
})

test('nested attempts cannot acquire the already-held action lock', async () => {
  const lock = { current: false }
  let calls = 0
  await runExclusivePreparation(lock, () => {}, async () => {
    calls++
    const nested = await runExclusivePreparation(lock, () => {}, async () => { calls++ })
    assert.equal(nested.started, false)
  })
  assert.equal(calls, 1)
})
