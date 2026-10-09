import test from 'node:test'
import assert from 'node:assert/strict'
import { summarizeLocalConversation } from './localConversationOutline.ts'

test('summarizes loaded message turns without mutating messages', () => {
  const msgs = [{ role: 'user', content: 'First question' }, { role: 'assistant', content: 'Answer' }, { role: 'user', content: 'Next question' }]
  const before = JSON.stringify(msgs)
  assert.deepEqual(summarizeLocalConversation(msgs), {
    userTurns: 2, assistantTurns: 1, hiddenPrompts: 0,
    prompts: [{ messageIndex: 0, turnNumber: 1, preview: 'First question' }, { messageIndex: 2, turnNumber: 2, preview: 'Next question' }],
  })
  assert.equal(JSON.stringify(msgs), before)
})
test('does not list streamed empty assistant messages or startup greeting', () => {
  const welcome = { role: 'assistant', content: 'Welcome' }
  const result = summarizeLocalConversation([welcome, { role: 'user', content: 'hi' }, { role: 'assistant', content: '' }], welcome)
  assert.equal(result.userTurns, 1)
  assert.equal(result.assistantTurns, 0)
  assert.deepEqual(result.prompts.map(p => p.messageIndex), [1])
})
test('caps outline to last 24 prompts and retains original message indices', () => {
  const msgs = Array.from({ length: 30 }, (_, i) => ({ role: 'user', content: 'Prompt ' + i }))
  const result = summarizeLocalConversation(msgs)
  assert.equal(result.userTurns, 30)
  assert.equal(result.hiddenPrompts, 6)
  assert.equal(result.prompts[0].messageIndex, 6)
  assert.equal(result.prompts[23].messageIndex, 29)
  assert.equal(result.prompts[23].turnNumber, 30)
})
test('normalizes control characters and bounds previews without splitting surrogate pairs', () => {
  const result = summarizeLocalConversation([{ role: 'user', content: 'Hi\u0000there\n' + '🙂'.repeat(200) }])
  assert.equal(result.prompts[0].preview.includes('\u0000'), false)
  assert.equal(Array.from(result.prompts[0].preview).length, 96)
  assert.equal(result.prompts[0].preview.endsWith('…'), true)
})
test('empty and other-role messages cannot create user outline entries', () => {
  const result = summarizeLocalConversation([{ role: 'user', content: '   ' }, { role: 'system', content: 'not a user' }, { role: 'assistant', content: 'yes' }])
  assert.equal(result.userTurns, 0)
  assert.equal(result.assistantTurns, 1)
  assert.deepEqual(result.prompts, [])
})
