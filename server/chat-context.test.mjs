import test from 'node:test'
import assert from 'node:assert/strict'
import { composeWorkspaceChatMessages, normalizeWorkspaceId } from './chat-context.mjs'

test('normalizes absent and valid workspace identifiers', () => {
  assert.equal(normalizeWorkspaceId(undefined), null)
  assert.equal(normalizeWorkspaceId(null), null)
  assert.equal(normalizeWorkspaceId(''), null)
  assert.equal(normalizeWorkspaceId('123e4567-e89b-12d3-a456-426614174000'), '123e4567-e89b-12d3-a456-426614174000')
})

test('rejects malformed workspace identifiers', () => {
  assert.equal(normalizeWorkspaceId('not-a-workspace'), undefined)
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
