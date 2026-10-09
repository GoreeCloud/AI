import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

test('first user message is persisted in the conversation creation mutation', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'goreecloud-ai-first-'))
  try {
    const body = [
      "import { createConversation, getConversation } from './server/conversations.mjs'",
      "const created = await createConversation({ model: 'local', messages: [{ role: 'user', content: 'Hello' }] })",
      "const stored = await getConversation(created.id)",
      "console.log(JSON.stringify({ created, stored }))"
    ].join('; ')
    const raw = execFileSync(process.execPath, ['--input-type=module', '--eval', body], {
      cwd: process.cwd(), env: { ...process.env, GOREECLOUD_AI_DATA_DIR: dir }, encoding: 'utf8'
    })
    const { created, stored } = JSON.parse(raw)
    assert.deepEqual(created.messages, [{ role: 'user', content: 'Hello' }])
    assert.deepEqual(stored.messages, created.messages)
    const envelope = JSON.parse(readFileSync(path.join(dir, 'conversations.json'), 'utf8'))
    assert.equal(envelope.conversations.length, 1)
    assert.deepEqual(envelope.conversations[0].messages, created.messages)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})
