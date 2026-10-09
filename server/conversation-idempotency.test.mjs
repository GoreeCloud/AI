import test from 'node:test'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

test('replayed request ID returns its original stored chat, conflicting payload rejects without mutation', () => {
  const dir = mkdtempSync(path.join(tmpdir(), 'goreecloud-ai-idempotent-'))
  try {
    const snippet = `
      import { createConversation, listConversations, updateConversation, getConversation } from './server/conversations.mjs'
      const input = { model:'local', title:'First prompt', messages:[{role:'user',content:'Hello'}],
        clientRequestId:'123e4567-e89b-42d3-a456-426614174000' }
      const first = await createConversation(input)
      const again = await createConversation(input)
      const concurrent = await Promise.all(Array.from({ length: 8 }, () => createConversation(input)))
      await updateConversation(first.id,{messages:[...input.messages,{role:'assistant',content:'Answer'}]})
      const later = await createConversation(input)
      let conflict
      try { await createConversation({...input,messages:[{role:'user',content:'Different'}]}) }
      catch(error) { conflict = {status:error.status,code:error.code} }
      const legacyA=await createConversation({})
      const legacyB=await createConversation({})
      const listed=await listConversations()
      const fetched=await getConversation(first.id)
      console.log(JSON.stringify({first,again,concurrent,later,conflict,legacyA,legacyB,listed,fetched}))
    `
    const result=JSON.parse(execFileSync(process.execPath,['--input-type=module','--eval',snippet], {
      cwd:process.cwd(),env:{...process.env,GOREECLOUD_AI_DATA_DIR:dir},encoding:'utf8',
    }))
    assert.equal(result.first.id,result.again.id)
    assert.equal(result.first.id,result.later.id)
    assert.equal(result.concurrent.length,8)
    assert.ok(result.concurrent.every(row=>row.id===result.first.id))
    assert.equal(result.later.messages.length,2)
    assert.deepEqual(result.conflict,{status:409,code:'create_request_conflict'})
    assert.notEqual(result.legacyA.id,result.legacyB.id)
    assert.equal(result.listed.length,3)
    for (const record of [result.first,result.again,...result.concurrent,result.later,result.fetched,...result.listed]) {
      assert.equal(Object.hasOwn(record,'clientRequestId'),false)
      assert.equal(Object.hasOwn(record,'clientRequestSignature'),false)
    }
  } finally { rmSync(dir,{recursive:true,force:true}) }
})
