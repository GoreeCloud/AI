import test from 'node:test'
import assert from 'node:assert/strict'
import { validateConversationCreateInput, validateConversationPatch } from './conversations.mjs'

const id = '123e4567-e89b-12d3-a456-426614174000'

test('accepts bounded conversation create input', () => {
  assert.equal(validateConversationCreateInput({}), true)
  assert.equal(validateConversationCreateInput({ model: 'qwen3:8b', workspaceId: id }), true)
  assert.equal(validateConversationCreateInput({ parentConversationId: id, parentMessageIndex: 3 }), true)
})

test('rejects malformed conversation create input', () => {
  assert.equal(validateConversationCreateInput({ unknown: true }), false)
  assert.equal(validateConversationCreateInput({ title: '   ' }), false)
  assert.equal(validateConversationCreateInput({ workspaceId: 'invalid' }), false)
  assert.equal(validateConversationCreateInput({ parentMessageIndex: 1 }), false)
  assert.equal(validateConversationCreateInput({ model: ' x' }), false)
})

test('accepts bounded conversation patches', () => {
  assert.equal(validateConversationPatch({ title: 'Renamed' }), true)
  assert.equal(validateConversationPatch({ workspaceId: null }), true)
  assert.equal(validateConversationPatch({ messages: [{ role: 'user', content: 'Hello' }] }), true)
})

test('rejects malformed conversation patches and messages', () => {
  assert.equal(validateConversationPatch({ messages: [{ role: 'tool', content: 'nope' }] }), false)
  assert.equal(validateConversationPatch({ messages: [{ role: 'user', content: 'ok', extra: true }] }), false)
  assert.equal(validateConversationPatch({ messages: new Array(4097).fill({ role: 'user', content: 'x' }) }), false)
  assert.equal(validateConversationPatch({ workspaceId: '------------------------------------' }), false)
  assert.equal(validateConversationPatch({ unexpected: true }), false)
})
