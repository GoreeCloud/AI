import test from 'node:test'
import assert from 'node:assert/strict'
import { validateStoredWorkspace, validateWorkspaceCreateInput, validateWorkspacePatch, validateWorkspaceStore } from './workspaces.mjs'

test('accepts bounded workspace create input', () => {
  assert.equal(validateWorkspaceCreateInput({}), true)
  assert.equal(validateWorkspaceCreateInput({
    name: 'Research',
    instructions: 'Prefer concise answers.',
    defaultModelRole: 'reasoner',
    researchEnabled: false,
  }), true)
})

test('rejects unknown, malformed, or oversized workspace create input', () => {
  assert.equal(validateWorkspaceCreateInput({ unknown: true }), false)
  assert.equal(validateWorkspaceCreateInput({ name: '   ' }), false)
  assert.equal(validateWorkspaceCreateInput({ instructions: 'x'.repeat(20_001) }), false)
  assert.equal(validateWorkspaceCreateInput({ defaultModelRole: 'root' }), false)
  assert.equal(validateWorkspaceCreateInput({ researchEnabled: 'yes' }), false)
})

test('accepts bounded workspace patches', () => {
  assert.equal(validateWorkspacePatch({ name: 'Updated' }), true)
  assert.equal(validateWorkspacePatch({ defaultModelRole: 'engineer' }), true)
  assert.equal(validateWorkspacePatch({
    fileIds: ['123e4567-e89b-12d3-a456-426614174000'],
    knowledgeCollectionIds: [],
    toolIds: ['local-tool'],
    researchEnabled: false,
  }), true)
})

test('rejects malformed workspace patch collections and roles', () => {
  assert.equal(validateWorkspacePatch({ defaultModelRole: 'arbitrary-model' }), false)
  assert.equal(validateWorkspacePatch({ fileIds: [''] }), false)
  assert.equal(validateWorkspacePatch({ toolIds: [' leading-space'] }), false)
  assert.equal(validateWorkspacePatch({ knowledgeCollectionIds: new Array(1001).fill('id') }), false)
  assert.equal(validateWorkspacePatch({ fileIds: ['duplicate', 'duplicate'] }), false)
  assert.equal(validateWorkspacePatch({ unexpected: [] }), false)
})

const workspaceId = '123e4567-e89b-12d3-a456-426614174000'
const storedWorkspace = {
  id: workspaceId,
  name: 'Stored Workspace',
  instructions: 'Prefer concise answers.',
  defaultModelRole: 'assistant',
  fileIds: ['223e4567-e89b-12d3-a456-426614174000'],
  knowledgeCollectionIds: [],
  toolIds: ['local-tool'],
  researchEnabled: false,
  createdAt: '2026-10-05T20:00:00.000Z',
  updatedAt: '2026-10-05T20:01:00.000Z',
}

test('validates persisted Workspace records and store envelopes', () => {
  assert.equal(validateStoredWorkspace(storedWorkspace), true)
  assert.equal(validateWorkspaceStore({ version: 1, workspaces: [storedWorkspace] }), true)
})

test('rejects malformed or duplicate persisted Workspace state', () => {
  assert.equal(validateStoredWorkspace({ ...storedWorkspace, name: ' padded ' }), false)
  assert.equal(validateStoredWorkspace({ ...storedWorkspace, fileIds: ['not-a-uuid'] }), false)
  assert.equal(validateStoredWorkspace({ ...storedWorkspace, updatedAt: '2026-10-05T19:59:00.000Z' }), false)
  assert.equal(validateStoredWorkspace({ ...storedWorkspace, researchEnabled: 'no' }), false)
  assert.equal(validateWorkspaceStore({ version: 2, workspaces: [storedWorkspace] }), false)
  assert.equal(validateWorkspaceStore({ version: 1, workspaces: [storedWorkspace, { ...storedWorkspace }] }), false)
})
