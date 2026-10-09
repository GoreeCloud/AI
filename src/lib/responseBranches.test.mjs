import test from 'node:test'
import assert from 'node:assert/strict'
import { editedMessageBranch, regenerationBranch } from './responseBranches.ts'

const history = [
  { role: 'user', content: 'First question' },
  { role: 'assistant', content: 'First answer' },
  { role: 'user', content: 'Second question' },
  { role: 'assistant', content: 'Second answer' },
]

test('editing earlier questions never mutates original messages or their suffix', () => {
  const original = structuredClone(history)
  const branch = editedMessageBranch(history, 0, 'Changed question')
  assert.deepEqual(branch, [{role: 'user', content: 'Changed question'}])
  assert.deepEqual(history, original)
  assert.notEqual(branch[0], history[0])
})

test('editing later questions includes past dialogue but not later assistant replies', () => {
  assert.deepEqual(editedMessageBranch(history, 2, 'Revised second question'), [
    history[0], history[1], {role: 'user', content: 'Revised second question'},
  ])
})

test('edits reject invalid roles, indices, blanks and over-limit text', () => {
  for (const index of [-1, 1, 9999]) assert.equal(editedMessageBranch(history, index, 'New'), null)
  assert.equal(editedMessageBranch(history, 0, '  '), null)
  assert.equal(editedMessageBranch(history, 0, 'x'.repeat(250001)), null)
})

test('regeneration excludes selected and later messages, preserving originals', () => {
  const original = structuredClone(history)
  const branch = regenerationBranch(history, 3)
  assert.deepEqual(branch, [history[0], history[1], history[2]])
  assert.notEqual(branch[0], history[0])
  assert.deepEqual(history, original)
  assert.deepEqual(regenerationBranch(history, 1), [history[0]])
})

test('regeneration declines unrelated/invalid turns and absent final user', () => {
  for (const index of [-1, 0, 2, 5000]) assert.equal(regenerationBranch(history, index), null)
  assert.equal(regenerationBranch([{role:'assistant',content:'Welcome'}], 0), null)
  assert.equal(regenerationBranch([{role:'user',content:'Hi'},{role:'assistant',content:'A'},{role:'assistant',content:'B'}], 2), null)
})

test('both helpers exclude welcome cards, including visible nonempty welcome text', () => {
  const withWelcome = [{role:'assistant',content:''}, ...history]
  assert.deepEqual(editedMessageBranch(withWelcome, 1, 'Edited'), [{role:'user',content:'Edited'}])
  assert.deepEqual(regenerationBranch(withWelcome, 2), [history[0]])
  const visibleWelcome = [{role:'assistant',content:'Welcome to GoreeCloud AI'}, ...history]
  assert.deepEqual(editedMessageBranch(visibleWelcome, 1, 'Edited'), [{role:'user',content:'Edited'}])
  assert.deepEqual(regenerationBranch(visibleWelcome, 2), [history[0]])
})
