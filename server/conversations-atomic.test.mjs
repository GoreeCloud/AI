import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

test('initial messages persist in the single conversation creation mutation', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'goreecloud-ai-first-turn-'))
  try {
    const snippet = `
      import { createConversation, getConversation, listConversations } from './server/conversations.mjs'
      const first = [{ role: 'user', content: 'My first prompt' }]
      const created = await createConversation({ model: 'qwen3:8b', title: 'My first prompt', messages: first })
      const stored = await getConversation(created.id)
      const summary = (await listConversations()).find(row => row.id === created.id)
      process.stdout.write(JSON.stringify({ created, stored, summary }))
    `
    const result = JSON.parse(execFileSync(process.execPath, ['--input-type=module', '-e', snippet], {
      cwd: process.cwd(), env: { ...process.env, GOREECLOUD_AI_DATA_DIR: dir }, encoding: 'utf8',
    }))
    assert.deepEqual(result.created.messages, [{ role: 'user', content: 'My first prompt' }])
    assert.deepEqual(result.stored.messages, result.created.messages)
    assert.equal(result.summary.messageCount, 1)
    const envelope = JSON.parse(readFileSync(path.join(dir, 'conversations.json'), 'utf8'))
    assert.equal(envelope.version, 1)
    assert.equal(envelope.conversations.length, 1)
    assert.deepEqual(envelope.conversations[0].messages, result.created.messages)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
})
