import test from 'node:test'
import assert from 'node:assert/strict'
import { appendPreviousPrompt, composerDraftError, MAX_COMPOSER_CHARS } from './composerDraft.ts'

test('reuse inserts a previous prompt into an empty local draft without sending', () => {
  assert.deepEqual(appendPreviousPrompt('', 'How do I start?'), {draft: 'How do I start?', error: null})
})
test('reuse retains existing draft and preserves verbatim multiline text', () => {
  const previous = 'First line\nsecond line'
  assert.deepEqual(appendPreviousPrompt('My current note', previous), {
    draft: 'My current note\n\nFirst line\nsecond line', error: null,
  })
})
test('empty previous prompt does not erase a draft', () => {
  assert.deepEqual(appendPreviousPrompt('Keep me', '  '), {draft: 'Keep me', error: 'The selected prompt is empty.'})
})
test('reuse fails closed before adding a too-large message to an existing draft', () => {
  const draft = 'x'.repeat(MAX_COMPOSER_CHARS - 1)
  const result = appendPreviousPrompt(draft, 'y')
  assert.equal(result.draft, draft)
  assert.match(result.error, /250,000-character/)
})
test('reuse accepts the exact backend per-message boundary without truncating', () => {
  const content = 'x'.repeat(MAX_COMPOSER_CHARS)
  assert.equal(appendPreviousPrompt('', content).draft.length, MAX_COMPOSER_CHARS)
  assert.equal(composerDraftError(content), null)
})
test('composer validation matches backend UTF-16 code-unit limits', () => {
  assert.equal(composerDraftError(' '), 'Enter a message before sending.')
  assert.equal(composerDraftError('a'.repeat(MAX_COMPOSER_CHARS + 1))?.includes('250,000-character'), true)
  assert.equal(composerDraftError('🙂'.repeat(MAX_COMPOSER_CHARS / 2)), null)
  assert.equal(composerDraftError('🙂'.repeat(MAX_COMPOSER_CHARS / 2 + 1))?.includes('250,000-character'), true)
})
