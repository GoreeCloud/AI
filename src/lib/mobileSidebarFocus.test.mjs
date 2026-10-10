import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const app = readFileSync(new URL('../App.tsx', import.meta.url), 'utf8')
const styles = readFileSync(new URL('../styles.css', import.meta.url), 'utf8')
const mobile = styles.split('@media (max-width: 900px) {')[1]?.split('\n}\n')[0]

test('closed mobile navigation is visually and keyboard hidden', () => {
  assert.ok(mobile, 'expected the 900px mobile navigation media query')
  assert.match(mobile, /\.sidebar\s*\{[^}]*visibility:\s*hidden/)
  assert.match(mobile, /\.sidebar\.is-open\s*\{[^}]*visibility:\s*visible/)
  assert.doesNotMatch(styles.slice(0, styles.indexOf('@media (max-width: 900px)')), /\.sidebar\s*\{[^}]*visibility:\s*hidden/)
})

test('mobile toggle exposes navigation relationship and expansion state', () => {
  assert.match(app, /<aside id="ai-primary-navigation" className=\{/)
  assert.match(app, /aria-label="Open navigation" aria-controls="ai-primary-navigation" aria-expanded=\{sidebarOpen\}/)
  assert.match(app, /ref=\{mobileNavigationTriggerRef\}/)
})

test('explicit dismissal and Escape restore focus to the mobile menu trigger', () => {
  assert.match(app, /function closeMobileNavigation\(focusTarget:/)
  assert.match(app, /const shouldMoveFocus = sidebarOpen && window\.matchMedia\('\(max-width: 900px\)'\)\.matches/)
  assert.match(app, /focusTarget === 'trigger' \? mobileNavigationTriggerRef\.current/)
  assert.match(app, /requestAnimationFrame\(\(\) => \{/)
  assert.match(app, /target\?\.focus\(\{ preventScroll: true \}\)/)
  assert.match(app, /if \(sidebarOpen\) closeMobileNavigation\(\)/)
  assert.match(app, /aria-label="Close navigation" onClick=\{\(\) => closeMobileNavigation\(\)\}/)
})

test('choosing a mobile conversation or New chat transfers focus into main content', () => {
  assert.match(app, /closeMobileNavigation\('composer'\)/)
  assert.match(app, /closeMobileNavigation\('conversation'\)/)
  assert.match(app, /focusTarget === 'composer' \? composerRef\.current : conversationRef\.current/)
})

test('Escape dismisses open navigation before stopping generation', () => {
  const start = app.indexOf('function handleShortcut(event: KeyboardEvent)')
  const end = app.indexOf("window.addEventListener('keydown', handleShortcut)", start)
  assert.ok(start >= 0 && end > start)
  const handler = app.slice(start, end)
  const find = handler.indexOf('if (conversationFindOpen)')
  const panel = handler.indexOf('if (sidebarOpen || contextOpen)')
  const generation = handler.indexOf('if (isGenerating)')
  assert.ok(find >= 0 && panel > find && generation > panel)
  assert.match(handler.slice(panel, generation), /setContextOpen\(false\)\s*return/)
  assert.match(handler.slice(generation), /stopGeneration\(\)\s*return/)
  assert.match(handler, /event\.isComposing \|\| event\.keyCode === 229/)
})
