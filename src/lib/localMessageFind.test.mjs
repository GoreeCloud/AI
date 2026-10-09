import test from 'node:test'
import assert from 'node:assert/strict'
import { findLocalMessages, nextLocalMatchCursor, findKeyboardAction, shouldOpenConversationFindShortcut, shouldOpenHistorySearchShortcut } from './localMessageFind.ts'
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

test('Ctrl or Command Shift F starts active conversation find', () => {
  assert.equal(shouldOpenConversationFindShortcut({ key: 'f', ctrlKey: true, shiftKey: true }), true)
  assert.equal(shouldOpenConversationFindShortcut({ key: 'F', metaKey: true, shiftKey: true }), true)
})

test('normal browser Find and composing or modified keys stay native', () => {
  for (const event of [
    { key: 'f', ctrlKey: true },
    { key: 'f', metaKey: true },
    { key: 'f', shiftKey: true },
    { key: 'f', ctrlKey: true, shiftKey: true, altKey: true },
    { key: 'f', ctrlKey: true, metaKey: true, shiftKey: true },
    { key: 'f', ctrlKey: true, shiftKey: true, isComposing: true },
    { key: 'f', ctrlKey: true, shiftKey: true, keyCode: 229 },
    { key: 'f', ctrlKey: true, shiftKey: true, repeat: true },
    { key: 'k', ctrlKey: true, shiftKey: true },
  ]) assert.equal(shouldOpenConversationFindShortcut(event), false)
})

test('message find rejects overlong queries without truncation', () => {
  const rows = [{role: 'user', content: 'planning'}]
  assert.deepEqual(findLocalMessages(rows, 'planning'), [0])
  assert.deepEqual(findLocalMessages(rows, 'planning' + ' '.repeat(113)), [])
})
test('message find rejects seventeenth search term instead of dropping it', () => {
  const rows = [{role: 'user', content: 'plan'}]
  assert.deepEqual(findLocalMessages(rows, Array(16).fill('plan').join(' ')), [0])
  assert.deepEqual(findLocalMessages(rows, Array(17).fill('plan').join(' ')), [])
})
test('history shortcut respects modal, browser and composition key ownership', () => {
  assert.equal(shouldOpenHistorySearchShortcut({ key: 'k', ctrlKey: true }), true)
  assert.equal(shouldOpenHistorySearchShortcut({ key: 'K', metaKey: true }), true)
  for (const event of [
    {key:'k'}, {key:'k', ctrlKey:true, shiftKey:true},
    {key:'k', ctrlKey:true, altKey:true},
    {key:'k', ctrlKey:true, metaKey:true},
    {key:'k', ctrlKey:true, repeat:true},
    {key:'k', ctrlKey:true, isComposing:true},
    {key:'k', ctrlKey:true, keyCode:229},
    {key:'f', ctrlKey:true}
  ]) assert.equal(shouldOpenHistorySearchShortcut(event), false)
})

test('finder can scope matches to the user's prompts or AI responses', () => {
  assert.deepEqual(findLocalMessages(messages, 'planning', 'all'), [0, 2])
  assert.deepEqual(findLocalMessages(messages, 'planning', 'user'), [0])
  assert.deepEqual(findLocalMessages(messages, 'planning', 'assistant'), [2])
  assert.deepEqual(findLocalMessages(messages, 'local', 'user'), [])
})
test('finder never includes system records and rejects unknown role scopes', () => {
  const rows = [{role: 'system', content: 'private planning'}, {role: 'user', content: 'planning'}]
  assert.deepEqual(findLocalMessages(rows, 'planning'), [1])
  assert.deepEqual(findLocalMessages(rows, 'planning', 'unexpected'), [])
  assert.deepEqual(findLocalMessages(rows, 'planning', 'assistant'), [])
})
test('role scope does not relax query bounds or alter message data', () => {
  const before = JSON.stringify(messages)
  assert.deepEqual(findLocalMessages(messages, 'planning' + ' '.repeat(113), 'user'), [])
  assert.deepEqual(findLocalMessages(messages, Array(17).fill('planning').join(' '), 'assistant'), [])
  assert.equal(JSON.stringify(messages), before)
})
