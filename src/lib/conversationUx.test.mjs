import test from 'node:test'
import assert from 'node:assert/strict'
import { ConversationEpoch, historyMatches, buildMarkdownTranscript, exportFileName, shouldSubmitComposerKey } from './conversationUx.ts'

test('conversation changes invalidate stale asynchronous callbacks', () => {
  const epoch = new ConversationEpoch()
  const first = epoch.begin()
  assert.equal(epoch.isCurrent(first), true)
  epoch.invalidate()
  assert.equal(epoch.isCurrent(first), false)
  const second = epoch.begin()
  assert.equal(epoch.isCurrent(second), true)
  assert.equal(epoch.isCurrent(first), false)
})

test('history search matches multiple words across visible fields and accents', () => {
  assert.equal(historyMatches('resume QWEN', ['Résumé planning', 'Qwen2.5', 'Personal']), true)
  assert.equal(historyMatches('QWEN other', ['Résumé planning', 'Qwen2.5', 'Personal']), false)
  assert.equal(historyMatches(' ', ['anything']), true)
})

test('metadata is escaped but message bodies are unchanged in Markdown export', () => {
  const body = '# A user heading\nactual text'
  const markdown = buildMarkdownTranscript({
    title: 'Session\n## Forged heading',
    model: 'a*model*',
    workspace: 'Team\n## Forged',
    exportedAt: '2026-10-08T00:00:00.000Z',
    messages: [{ role: 'user', content: body }, { role: 'assistant', content: 'Response' }],
  })
  assert.ok(markdown.startsWith('# Session \\#\\# Forged heading\n'))
  assert.ok(!markdown.includes('\n## Forged\n'))
  assert.ok(markdown.includes('a\\*model\\*'))
  assert.ok(markdown.includes(body))
  assert.ok(markdown.includes('## GoreeCloud AI\n\nResponse'))
})

test('export filenames do not contain a leading dot or traversal path', () => {
  assert.equal(exportFileName('../../hi world'), 'hi-world.md')
  assert.equal(exportFileName('***'), 'goreecloud-ai-conversation.md')
})

test('IME composition and modifier keys never submit the composer', () => {
  const plain = { key: 'Enter', shiftKey: false }
  assert.equal(shouldSubmitComposerKey(plain), true)
  for (const candidate of [
    { ...plain, isComposing: true },
    { ...plain, keyCode: 229 },
    { ...plain, shiftKey: true },
    { ...plain, altKey: true },
    { ...plain, ctrlKey: true },
    { ...plain, metaKey: true },
    { ...plain, repeat: true },
    { ...plain, key: 'a' },
  ]) assert.equal(shouldSubmitComposerKey(candidate), false)
})

test('history search query limit is fail-closed', () => {
  assert.equal(historyMatches('q'.repeat(121), ['q']), false)
  assert.equal(historyMatches(Array(17).fill('a').join(' '), ['a']), false)
  assert.equal(historyMatches('resume qwen', ['Résumé', 'Qwen']), true)
})
