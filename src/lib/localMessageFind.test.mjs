import test from 'node:test'
import assert from 'node:assert/strict'
import { findLocalMessages, nextLocalMatchCursor, findKeyboardAction } from './localMessageFind.ts'
const messages = [
  {role: 'user', content: 'A résumé about project planning'},
  {role: 'assistant', content: 'The local plan uses Qwen for coding.'},
  {role: 'assistant', content: 'Résumé planning with QWEN.'},
  {role: 'user', content: 'No matches here'},
]
test('search is accent/case insensitive and supports all terms in a message', () => {
  assert.deepEqual(findLocalMessages(messages, 'RESUME planning'), [0, 2])
  assert.deepEqual(findLocalMessages(messages, 'qwen local'), [1])
  assert.deepEqual(findLocalMessages(messages, 'qwen resume'), [2])
})
test('empty and whitespace searches never match everything', () => {
  assert.deepEqual(findLocalMessages(messages, ''), [])
  assert.deepEqual(findLocalMessages(messages, '    '), [])
  assert.deepEqual(findLocalMessages([], 'qwen'), [])
})
test('does not mutate source messages or escape into unrelated loaded data', () => {
  const before = JSON.stringify(messages)
  assert.deepEqual(findLocalMessages(messages.slice(0, 1), 'Qwen'), [])
  assert.equal(JSON.stringify(messages), before)
})
test('bounded text query handles long strings safely', () => {
  assert.deepEqual(findLocalMessages(messages, 'Z'.repeat(50000)), [])
})
test('matches never include unrelated conversations passed separately', () => {
  const privateMessages = [{role: 'user', content: 'secret project'}, {role: 'assistant', content: 'Qwen coding'}]
  assert.deepEqual(findLocalMessages(messages, 'secret project'), [])
  assert.deepEqual(findLocalMessages(privateMessages, 'secret project'), [0])
})
test('unicode and punctuation are treated as literal text, not executable regex', () => {
  assert.deepEqual(findLocalMessages([{role: 'user', content: 'How is 1 + 1?'}], '1 + 1?'), [0])
  assert.deepEqual(findLocalMessages([{role: 'user', content: 'A [bracket]'}], '[bracket]'), [0])
})
test('match cursor selects first or last result on initial navigation', () => {
  assert.equal(nextLocalMatchCursor(3, -1, 1), 0)
  assert.equal(nextLocalMatchCursor(3, -1, -1), 2)
})
test('match cursor wraps at both ends and fails closed for empty results', () => {
  assert.equal(nextLocalMatchCursor(3, 2, 1), 0)
  assert.equal(nextLocalMatchCursor(3, 0, -1), 2)
  assert.equal(nextLocalMatchCursor(0, -1, 1), -1)
  assert.equal(nextLocalMatchCursor(Number.NaN, 0, 1), -1)
})

test('finder keys navigate only when composition is inactive', () => {
  assert.equal(findKeyboardAction({ key: 'Enter' }), 'next')
  assert.equal(findKeyboardAction({ key: 'Enter', shiftKey: true }), 'previous')
  assert.equal(findKeyboardAction({ key: 'Escape' }), 'close')
})
test('IME-owned Escape and Enter never become finder shortcuts', () => {
  for (const key of ['Enter', 'Escape']) {
    assert.equal(findKeyboardAction({ key, isComposing: true }), null)
    assert.equal(findKeyboardAction({ key, keyCode: 229 }), null)
  }
})
test('finder ignores browser shortcuts, repeated keys, and ordinary text', () => {
  for (const candidate of [
    { key: 'Enter', ctrlKey: true },
    { key: 'Enter', metaKey: true },
    { key: 'Enter', altKey: true },
    { key: 'Escape', repeat: true },
    { key: 'x' },
  ]) assert.equal(findKeyboardAction(candidate), null)
})
