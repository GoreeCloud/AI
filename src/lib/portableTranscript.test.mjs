import test from 'node:test'
import assert from 'node:assert/strict'
import { buildPortableTranscript, portableFileName } from './portableTranscript.ts'
const input = {
  title: 'Team\nFORGED LABEL',
  model: 'Qwen Local',
  workspace: 'Work\r\nInjected',
  exportedAt: '2026-10-08T20:00:00.000Z',
  messages: [{role: 'user', content: 'Line one\nLine two'}, {role: 'assistant', content: '{"answer": true}\n## text'}],
}
test('JSON exports structured role/content messages without rewriting bodies', () => {
  const json = JSON.parse(buildPortableTranscript(input, 'json'))
  assert.equal(json.format, 'goreecloud-ai-conversation-export')
  assert.equal(json.version, 1)
  assert.deepEqual(json.messages, input.messages)
  assert.equal(json.title, input.title)
  assert.equal(json.workspace, input.workspace)
})
test('plain text export keeps labels one line and message bodies verbatim', () => {
  const text = buildPortableTranscript(input, 'txt')
  assert.ok(text.includes('Title: Team FORGED LABEL\n'))
  assert.ok(text.includes('Workspace: Work Injected\n'))
  assert.ok(text.includes('You:\nLine one\nLine two\n'))
  assert.ok(text.includes('GoreeCloud AI:\n{"answer": true}\n## text'))
})
test('portable filenames are extension-safe and traversal free', () => {
  assert.equal(portableFileName('../../secret', 'json'), 'secret.json')
  assert.equal(portableFileName('***', 'txt'), 'goreecloud-ai-conversation.txt')
  assert.equal(portableFileName('.hidden', 'json'), 'hidden.json')
})
test('JSON exports preserve Unicode, special JSON characters and multiline body content', () => {
  const transcript = {...input, messages:[{role:'user', content:'日本語 🧪 "quoted" \\slash\nnew line'}]}
  assert.deepEqual(JSON.parse(buildPortableTranscript(transcript, 'json')).messages, transcript.messages)
})
test('plain text removes metadata controls without altering body controls', () => {
  const text = buildPortableTranscript({...input, title:'a\u0000b', messages:[{role:'user',content:'exact\ncontent'}]}, 'txt')
  assert.ok(text.includes('Title: a b\n'))
  assert.ok(text.includes('You:\nexact\ncontent\n'))
})
