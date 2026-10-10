import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../App.tsx', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../styles.css', import.meta.url), 'utf8')

test('saved conversations are a named, keyboard-reachable navigation region', () => {
  assert.equal(app.split('role="region" aria-label="Saved conversations"').length - 1, 1)
  assert.ok(app.includes('className="sidebar-section" role="region" aria-label="Saved conversations"'))
})

test('only the selected conversation exposes its current state', () => {
  assert.ok(app.includes("aria-current={item.id === conversationId ? 'true' : undefined}"))
  assert.ok(app.includes('onClick={() => void openConversation(item.id)}'))
})

test('search counts derive from filtered and full history and announce politely', () => {
  assert.ok(app.includes('historyQuery.trim() && <span className="history-count" role="status" aria-live="polite">'))
  assert.ok(app.includes('{visibleHistory.length} of {history.length} saved conversations match'))
  assert.ok(app.includes("historyQuery.trim() ? 'Matches' : 'Recent'"))
  assert.ok(styles.includes('.history-count {'))
})

test('saved-history errors are announced while preserving the retry action', () => {
  assert.ok(app.includes('className="history-empty history-error" role="alert"'))
  assert.ok(app.includes('onClick={() => void refreshHistory()}'))
})
