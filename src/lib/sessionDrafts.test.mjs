import test from 'node:test'
import assert from 'node:assert/strict'
import { SessionConversationDrafts, shouldLeaveDeletedConversation } from './sessionDrafts.ts'

test('unsent drafts remain scoped to the selected conversation', () => {
  const drafts = new SessionConversationDrafts()
  drafts.remember('a', 'Private for A')
  drafts.remember('b', 'Private for B')
  assert.equal(drafts.restore('a'), 'Private for A')
  assert.equal(drafts.restore('b'), 'Private for B')
  assert.equal(drafts.restore('c'), '')
})
test('new conversation draft is isolated from all saved conversations', () => {
  const drafts = new SessionConversationDrafts()
  drafts.remember(null, 'Unsaved new chat')
  drafts.remember('unsaved:', 'Saved conversation with similar-looking ID')
  assert.equal(drafts.restore(null), 'Unsaved new chat')
  assert.equal(drafts.restore('unsaved:'), 'Saved conversation with similar-looking ID')
})
test('empty drafts are cleared rather than retained', () => {
  const drafts = new SessionConversationDrafts()
  drafts.remember('conversation', 'draft')
  drafts.remember('conversation', '')
  assert.equal(drafts.restore('conversation'), '')
})
test('sending clears only the corresponding draft', () => {
  const drafts = new SessionConversationDrafts()
  drafts.remember('first', 'a')
  drafts.remember('second', 'b')
  drafts.clear('first')
  assert.equal(drafts.restore('first'), '')
  assert.equal(drafts.restore('second'), 'b')
})

test('deleting one conversation clears its tab-only draft without clearing others', () => {
  const drafts = new SessionConversationDrafts()
  drafts.remember('delete-me', 'sensitive unsent text')
  drafts.remember('keep-me', 'another private unsent note')
  drafts.clear('delete-me')
  assert.equal(drafts.restore('delete-me'), '')
  assert.equal(drafts.restore('keep-me'), 'another private unsent note')
})
test('a delayed deletion must not interrupt a newer conversation selection', () => {
  assert.equal(shouldLeaveDeletedConversation('deleted', 'deleted', 5, 5), true)
  assert.equal(shouldLeaveDeletedConversation('deleted', 'another', 5, 5), false)
  assert.equal(shouldLeaveDeletedConversation('deleted', 'deleted', 5, 6), false)
  assert.equal(shouldLeaveDeletedConversation('deleted', null, 5, 5), false)
})
