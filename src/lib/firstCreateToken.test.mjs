import test from 'node:test'
import assert from 'node:assert/strict'
import { getFirstCreateToken, clearFirstCreateToken } from './firstCreateToken.ts'

test('retry of identical first prompt within one navigation epoch preserves request identity', () => {
  const ref = { current: null }
  let next = 0
  const make = () => 'token-' + (++next)
  const first = getFirstCreateToken(ref, 'epoch:7/prompt:A', make)
  const retry = getFirstCreateToken(ref, 'epoch:7/prompt:A', make)
  assert.equal(first, retry)
  assert.equal(next, 1)
})
test('different draft, workspace or epoch yields a new request identity', () => {
  const ref = { current: null }
  let next = 0
  const make = () => 'token-' + (++next)
  const first = getFirstCreateToken(ref, 'epoch:7/prompt:A', make)
  const edit = getFirstCreateToken(ref, 'epoch:7/prompt:B', make)
  const navigation = getFirstCreateToken(ref, 'epoch:8/prompt:B', make)
  assert.notEqual(first, edit)
  assert.notEqual(edit, navigation)
  assert.equal(next, 3)
})
test('a stale completion cannot erase the newer pending token', () => {
  const ref = { current: null }
  const first = getFirstCreateToken(ref, 'first', () => 'first-id')
  getFirstCreateToken(ref, 'second', () => 'second-id')
  clearFirstCreateToken(ref, first)
  assert.equal(ref.current.requestId, 'second-id')
  clearFirstCreateToken(ref, 'second-id')
  assert.equal(ref.current, null)
})
