import test from 'node:test'
import assert from 'node:assert/strict'
import { validateConversationReferenceState, validateWorkspaceFileReferenceState } from './reference-integrity.mjs'

const workspaceId = '123e4567-e89b-12d3-a456-426614174000'
const parentId = '223e4567-e89b-12d3-a456-426614174000'
const fileId = '323e4567-e89b-12d3-a456-426614174000'

test('accepts resolved conversation references', () => {
  assert.deepEqual(validateConversationReferenceState({}, {}), { ok: true })
  assert.deepEqual(validateConversationReferenceState(
    { workspaceId, parentConversationId: parentId, parentMessageIndex: 1 },
    { workspaceExists: true, parentConversation: { id: parentId, messages: [{ role: 'user' }, { role: 'assistant' }] } },
  ), { ok: true })
})

test('rejects unresolved or incomplete conversation references', () => {
  assert.equal(validateConversationReferenceState({ workspaceId }, { workspaceExists: false }).reason, 'workspace_not_found')
  assert.equal(validateConversationReferenceState({ parentConversationId: parentId }, {}).reason, 'incomplete_parent_lineage')
  assert.equal(validateConversationReferenceState({ parentMessageIndex: 0 }, {}).reason, 'incomplete_parent_lineage')
  assert.equal(validateConversationReferenceState(
    { parentConversationId: parentId, parentMessageIndex: 0 },
    { parentConversation: null },
  ).reason, 'parent_not_found')
  assert.equal(validateConversationReferenceState(
    { parentConversationId: parentId, parentMessageIndex: 2 },
    { parentConversation: { id: parentId, messages: [{ role: 'user' }] } },
  ).reason, 'parent_message_not_found')
})

test('accepts only server-owned Workspace file references', () => {
  const files = [{ id: fileId, workspaceId }]
  assert.deepEqual(validateWorkspaceFileReferenceState(workspaceId, [fileId], files), { ok: true })
  assert.deepEqual(validateWorkspaceFileReferenceState(workspaceId, [], files), { ok: true })
})

test('rejects missing and cross-Workspace file references', () => {
  assert.equal(validateWorkspaceFileReferenceState(workspaceId, [fileId], []).reason, 'file_not_found')
  assert.equal(validateWorkspaceFileReferenceState(workspaceId, [fileId], [{ id: fileId, workspaceId: null }]).reason, 'file_workspace_mismatch')
  assert.equal(validateWorkspaceFileReferenceState(workspaceId, [fileId], null).reason, 'file_catalog_unavailable')
})
