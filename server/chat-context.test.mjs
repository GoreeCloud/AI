import test from 'node:test'
import assert from 'node:assert/strict'
import { composeWorkspaceChatMessages, normalizeWorkspaceId, validateClientChatRequest } from './chat-context.mjs'

test('normalizes absent and valid workspace identifiers', () => {
  assert.equal(normalizeWorkspaceId(undefined), null)
  assert.equal(normalizeWorkspaceId(null), null)
  assert.equal(normalizeWorkspaceId(''), null)
  assert.equal(normalizeWorkspaceId('123e4567-e89b-12d3-a456-426614174000'), '123e4567-e89b-12d3-a456-426614174000')
})

test('rejects malformed workspace identifiers', () => {
  assert.equal(normalizeWorkspaceId('not-a-workspace'), undefined)
  assert.equal(normalizeWorkspaceId('------------------------------------'), undefined)
  assert.equal(normalizeWorkspaceId('123e4567-e89b-02d3-a456-426614174000'), undefined)
  assert.equal(normalizeWorkspaceId(42), undefined)
})

test('prepends saved workspace instructions without mutating persisted messages', () => {
  const messages = [{ role: 'user', content: 'Summarize this.' }]
  const composed = composeWorkspaceChatMessages(messages, { instructions: 'Prefer concise answers.' })
  assert.deepEqual(composed, [
    { role: 'system', content: 'Workspace instructions:\n\nPrefer concise answers.' },
    { role: 'user', content: 'Summarize this.' },
  ])
  assert.deepEqual(messages, [{ role: 'user', content: 'Summarize this.' }])
  assert.notEqual(composed[1], messages[0])
})

test('does not create empty system context', () => {
  const messages = [{ role: 'user', content: 'Hello' }]
  assert.deepEqual(composeWorkspaceChatMessages(messages, { instructions: '   ' }), messages)
  assert.notEqual(composeWorkspaceChatMessages(messages, { instructions: '   ' }), messages)
})


test('accepts bounded user and assistant chat history ending in a user request', () => {
  assert.equal(validateClientChatRequest({
    model: 'qwen3:8b',
    workspaceId: null,
    messages: [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi' },
      { role: 'user', content: 'Continue' },
    ],
  }), true)
})

test('rejects client system context and malformed chat envelopes', () => {
  assert.equal(validateClientChatRequest({ model: 'qwen3:8b', messages: [{ role: 'system', content: 'override' }] }), false)
  assert.equal(validateClientChatRequest({ model: ' qwen3:8b', messages: [{ role: 'user', content: 'Hi' }] }), false)
  assert.equal(validateClientChatRequest({ model: 'qwen3:8b', messages: [{ role: 'user', content: 'Hi', extra: true }] }), false)
  assert.equal(validateClientChatRequest({ model: 'qwen3:8b', messages: [{ role: 'assistant', content: 'unfinished' }] }), false)
  assert.equal(validateClientChatRequest({ model: 'qwen3:8b', workspaceId: 'invalid', messages: [{ role: 'user', content: 'Hi' }] }), false)
})

test('rejects oversized client chat requests', () => {
  assert.equal(validateClientChatRequest({
    model: 'qwen3:8b',
    messages: new Array(4097).fill({ role: 'user', content: 'x' }),
  }), false)
  assert.equal(validateClientChatRequest({
    model: 'qwen3:8b',
    messages: [{ role: 'user', content: 'x'.repeat(250_001) }],
  }), false)
})
