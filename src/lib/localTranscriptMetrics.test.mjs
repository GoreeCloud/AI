import test from 'node:test'
import assert from 'node:assert/strict'
import { summarizeLocalTranscript } from './localTranscriptMetrics.ts'

test('reports code-point length per role without mutating messages', () => {
  const messages = [{role: 'user', content: 'Hi 🙂'}, {role: 'assistant', content: 'OK'}, {role: 'user', content: 'é'}]
  const snapshot = JSON.stringify(messages)
  assert.deepEqual(summarizeLocalTranscript(messages), {
    userCharacters: 5, assistantCharacters: 2, totalCharacters: 7,
  })
  assert.equal(JSON.stringify(messages), snapshot)
})
test('excludes welcome identity, empty streams and unexpected roles', () => {
  const welcome = {role: 'assistant', content: 'Welcome'}
  assert.deepEqual(summarizeLocalTranscript([
    welcome, {role: 'assistant', content: ''}, {role: 'system', content: 'secret'}, {role: 'user', content: 'Ask'},
  ], welcome), {userCharacters: 3, assistantCharacters: 0, totalCharacters: 3})
})
test('counts only supplied loaded messages and does not treat length as model tokens', () => {
  assert.deepEqual(summarizeLocalTranscript([{role: 'assistant', content: '🌍🌏'}]), {
    userCharacters: 0, assistantCharacters: 2, totalCharacters: 2,
  })
  assert.deepEqual(summarizeLocalTranscript([]), {userCharacters: 0, assistantCharacters: 0, totalCharacters: 0})
})
