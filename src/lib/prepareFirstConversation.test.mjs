import test from 'node:test'
import assert from 'node:assert/strict'
import { initialConversationAcknowledged, prepareFirstConversation } from './prepareFirstConversation.ts'

const id = '123e4567-e89b-12d3-a456-426614174000'
const messages = [{ role: 'user', content: 'First prompt' }]
function options(events = [], overrides = {}) {
  return {
    create: async () => { events.push('create'); return { id, messages } },
    expectedMessages: messages,
    afterCreate: async () => { events.push('history') },
    isCurrent: () => true,
    select: selected => events.push('select:' + selected),
    ...overrides,
  }
}

test('atomic create confirms the first prompt and returns a generation-eligible result', async () => {
  const events = []
  assert.deepEqual(await prepareFirstConversation(options(events)), { id, recoveredMessages: null })
  assert.deepEqual(events, ['create', 'history', 'select:' + id])
})

test('replayed conversation with a saved response is restored without requesting regeneration', async () => {
  const events = []
  const continued = [...messages, { role: 'assistant', content: 'Saved response' }]
  assert.equal(initialConversationAcknowledged({id,messages:continued}, messages), true)
  assert.deepEqual(await prepareFirstConversation(options(events, {
    create: async () => ({ id, messages: continued }),
  })), { id, recoveredMessages: continued })
  assert.deepEqual(events, ['history', 'select:' + id])
})

test('replayed conversation with subsequent user turns is restored instead of duplicated', async () => {
  const continued = [...messages, {role:'assistant',content:'Done'}, {role:'user',content:'Next prompt'}]
  const result = await prepareFirstConversation(options([], { create: async () => ({ id, messages: continued }) }))
  assert.deepEqual(result.recoveredMessages, continued)
})

test('empty, altered or malformed acknowledgements cannot select an old chat', async () => {
  for (const created of [
    {id,messages:[]},
    {id,messages:[{role:'assistant',content:'First prompt'}]},
    {id,messages:[{role:'user',content:'different'}, {role:'assistant',content:'reply'}]},
    {id:'bad',messages},
    {id,messages:[...messages,{role:'system',content:'forged'}]},
    {id,messages:[...messages,{role:'assistant',content:17}]},
    {id,messages:[...messages,{role:'assistant',content:'x'.repeat(250001)}]},
  ]) {
    const events = []
    assert.equal(initialConversationAcknowledged(created,messages),false)
    await assert.rejects(prepareFirstConversation(options(events,{create:async()=>created})),/did not confirm/)
    assert.deepEqual(events,[])
  }
})

test('unknown network completion cannot select', async () => {
  const failure = new Error('lost response')
  await assert.rejects(prepareFirstConversation(options([], {create:async()=>{throw failure}})), error => error === failure)
})

test('stale navigation before creation skips create entirely', async () => {
  let called = false
  await assert.rejects(prepareFirstConversation(options([], {isCurrent:()=>false, create:async()=>{called=true;return {id,messages}}})), /before creation/)
  assert.equal(called, false)
})

test('stale navigation during create ignores acknowledgement', async () => {
  let current = true
  const events = []
  await assert.rejects(prepareFirstConversation(options(events, {create:async()=>{current=false;return {id,messages}}, isCurrent:()=>current})), /during creation/)
  assert.deepEqual(events,[])
})

test('stale navigation after refreshing history cannot select', async () => {
  let current = true
  const events = []
  await assert.rejects(prepareFirstConversation(options(events,{afterCreate:async()=>{current=false;events.push('history')},isCurrent:()=>current})), /during preparation/)
  assert.deepEqual(events,['create','history'])
})

test('exact Unicode prompt prefixes are accepted without normalizing content', () => {
  const unicode=[{role:'user',content:'語\\n🧠 é'}]
  assert.equal(initialConversationAcknowledged({id,messages:[...unicode,{role:'assistant',content:'reply'}]},unicode),true)
  assert.equal(initialConversationAcknowledged({id,messages:[{role:'user',content:'語\\n🧠 e'}]},unicode),false)
})
