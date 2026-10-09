import test from 'node:test'
import assert from 'node:assert/strict'
import { validateConversationCreateInput, validateConversationPatch, validateConversationStore, validateStoredConversation } from './conversations.mjs'

const id = '123e4567-e89b-12d3-a456-426614174000'

test('accepts bounded conversation create input', () => {
  assert.equal(validateConversationCreateInput({}), true)
  assert.equal(validateConversationCreateInput({ model: 'qwen3:8b', workspaceId: id }), true)
  assert.equal(validateConversationCreateInput({ parentConversationId: id, parentMessageIndex: 3 }), true)
  assert.equal(validateConversationCreateInput({ messages: [{ role: 'user', content: 'First prompt' }] }), true)
})

test('rejects malformed conversation create input', () => {
  assert.equal(validateConversationCreateInput({ unknown: true }), false)
  assert.equal(validateConversationCreateInput({ title: '   ' }), false)
  assert.equal(validateConversationCreateInput({ workspaceId: 'invalid' }), false)
  assert.equal(validateConversationCreateInput({ parentMessageIndex: 1 }), false)
  assert.equal(validateConversationCreateInput({ model: ' x' }), false)
  assert.equal(validateConversationCreateInput({ messages: [{ role: 'system', content: 'forbidden' }] }), false)
  assert.equal(validateConversationCreateInput({ messages: [{ role: 'user', content: 'valid', extra: true }] }), false)
  assert.equal(validateConversationCreateInput({ messages: new Array(4097).fill({ role: 'user', content: 'x' }) }), false)
  assert.equal(validateConversationCreateInput({ messages: [{ role: 'user', content: 'x'.repeat(250001) }] }), false)
})

test('accepts bounded conversation patches', () => {
  assert.equal(validateConversationPatch({ title: 'Renamed' }), true)
  assert.equal(validateConversationPatch({ workspaceId: null }), true)
  assert.equal(validateConversationPatch({ messages: [{ role: 'user', content: 'Hello' }] }), true)
})

test('rejects malformed conversation patches and messages', () => {
  assert.equal(validateConversationPatch({ messages: [{ role: 'tool', content: 'nope' }] }), false)
  assert.equal(validateConversationPatch({ messages: [{ role: 'system', content: 'not allowed' }] }), false)
  assert.equal(validateConversationPatch({ messages: [{ role: 'user', content: 'ok', extra: true }] }), false)
  assert.equal(validateConversationPatch({ messages: new Array(4097).fill({ role: 'user', content: 'x' }) }), false)
  assert.equal(validateConversationPatch({ workspaceId: '------------------------------------' }), false)
  assert.equal(validateConversationPatch({ unexpected: true }), false)
})

const storedConversation = {
  id,
  title: 'Stored conversation',
  model: 'qwen3:8b',
  workspaceId: null,
  messages: [{ role: 'user', content: 'Hello' }],
  parentConversationId: null,
  parentMessageIndex: null,
  createdAt: '2026-10-05T20:00:00.000Z',
  updatedAt: '2026-10-05T20:01:00.000Z',
}

test('validates persisted conversation records and store envelopes', () => {
  assert.equal(validateStoredConversation(storedConversation), true)
  assert.equal(validateConversationStore({ version: 1, conversations: [storedConversation] }), true)
})

test('rejects malformed or duplicate persisted conversation state', () => {
  assert.equal(validateStoredConversation({ ...storedConversation, title: ' padded ' }), false)
  assert.equal(validateStoredConversation({ ...storedConversation, updatedAt: 'not-a-time' }), false)
  assert.equal(validateStoredConversation({ ...storedConversation, updatedAt: '2026-10-05T19:59:00.000Z' }), false)
  assert.equal(validateStoredConversation({ ...storedConversation, parentConversationId: id, parentMessageIndex: null }), false)
  assert.equal(validateConversationStore({ version: 2, conversations: [storedConversation] }), false)
  assert.equal(validateConversationStore({ version: 1, conversations: [storedConversation, { ...storedConversation }] }), false)
})


test('opt-in create key requires a bounded first user message', () => {
  assert.equal(validateConversationCreateInput({ messages:[{role:'user',content:'Hello'}], clientRequestId:id }),true)
  assert.equal(validateConversationCreateInput({clientRequestId:id}),false)
  assert.equal(validateConversationCreateInput({clientRequestId:id,messages:[]}),false)
  assert.equal(validateConversationCreateInput({clientRequestId:id,messages:[{role:'assistant',content:'hello'}]}),false)
  assert.equal(validateConversationCreateInput({clientRequestId:'invalid',messages:[{role:'user',content:'hello'}]}),false)
  assert.equal(validateStoredConversation({...storedConversation,clientRequestId:id}),false)
  const keyed={...storedConversation,clientRequestId:id,clientRequestSignature:'a'.repeat(64)}
  assert.equal(validateStoredConversation(keyed),true)
  assert.equal(validateStoredConversation({...keyed,clientRequestSignature:'bad'}),false)
  assert.equal(validateConversationStore({version:1,conversations:[
    keyed,{...keyed,id:'223e4567-e89b-12d3-a456-426614174000'},
  ]}),false)
})
