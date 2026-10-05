import test from 'node:test'
import assert from 'node:assert/strict'
import { validateWorkspaceCreateInput, validateWorkspacePatch } from './workspaces.mjs'

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
  assert.equal(validateWorkspacePatch({ unexpected: [] }), false)
})
