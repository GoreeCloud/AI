import test from 'node:test'
import assert from 'node:assert/strict'
import { editableDialogSourceIsCurrent, shouldCloseTextDialog } from './dialogOwnership.ts'

const messages = [
  { role: 'user', content: 'First original prompt' },
  { role: 'assistant', content: 'An answer' },
  { role: 'user', content: 'Second original prompt' },
]

test('an edit targets only the originating conversation and unchanged prompt', () => {
  const origin = { conversationId: 'thread-a', index: 2, originalContent: 'Second original prompt' }
  assert.equal(editableDialogSourceIsCurrent(origin, 'thread-a', messages), true)
  assert.equal(editableDialogSourceIsCurrent(origin, 'thread-b', messages), false)
  assert.equal(editableDialogSourceIsCurrent(origin, null, messages), false)
  assert.equal(editableDialogSourceIsCurrent(origin, 'thread-a', [...messages.slice(0, 2), {role:'user',content:'Different'}]), false)
  assert.equal(editableDialogSourceIsCurrent(origin, 'thread-a', messages.slice(0, 2)), false)
})

test('user role, index and unsaved-conversation identities are validated', () => {
  assert.equal(editableDialogSourceIsCurrent({conversationId: null, index:0, originalContent:'First original prompt'}, null, messages), true)
  assert.equal(editableDialogSourceIsCurrent({conversationId:'t', index:1, originalContent:'An answer'}, 't', messages), false)
  assert.equal(editableDialogSourceIsCurrent({conversationId:'t', index:-1, originalContent:'x'}, 't', messages), false)
  assert.equal(editableDialogSourceIsCurrent({conversationId:'t', index:Infinity, originalContent:'x'}, 't', messages), false)
})

test('Escape closes only when idle and composition is inactive', () => {
  assert.equal(shouldCloseTextDialog({key:'Escape'}, false), true)
  for (const event of [
    {key:'Escape', isComposing:true},
    {key:'Escape', keyCode:229},
    {key:'Escape', altKey:true},
    {key:'Escape', ctrlKey:true},
    {key:'Escape', metaKey:true},
    {key:'Enter'},
  ]) assert.equal(shouldCloseTextDialog(event, false), false)
  assert.equal(shouldCloseTextDialog({key:'Escape'}, true), false)
})
