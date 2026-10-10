import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../App.tsx', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../styles.css', import.meta.url), 'utf8')

test('keyboard skip links precede the sidebar and have unique local targets', () => {
  const links = [
    ['conversation-messages', 'Skip to conversation messages'],
    ['message-composer', 'Skip to message composer']
  ]
  for (const [id, text] of links) {
    assert.equal(app.split(`href="#${id}"`).length - 1, 1)
    assert.match(app, new RegExp(`<a className="skip-nav-link[^"]*" href="#${id}">${text}</a>`))
    assert.equal(app.split(`id="${id}"`).length - 1, 1)
  }
  assert.ok(app.indexOf('href="#conversation-messages"') < app.indexOf('<aside className={'))
  assert.ok(app.indexOf('href="#message-composer"') < app.indexOf('<aside className={'))
})

test('conversation target is a named, programmatically focusable region', () => {
  assert.match(app, /<section id="conversation-messages"[^>]*tabIndex=\{-1\}[^>]*aria-label="Conversation messages"/)
})

test('composer target is the enabled-or-disabled native textarea', () => {
  assert.match(app, /<textarea id="message-composer"[^>]*aria-label="Message GoreeCloud AI"/)
})

test('skip links remain focus-revealed and visually identifiable in both themes', () => {
  assert.match(styles, /\.skip-nav-link\s*\{[^}]*position:\s*fixed;[^}]*background:\s*var\(--surface-0\);/)
  assert.match(styles, /\.skip-nav-link:focus\s*\{[^}]*transform:\s*translateY\(0\);/)
  assert.match(styles, /\.skip-nav-link:focus-visible\s*\{[^}]*outline:/)
})
