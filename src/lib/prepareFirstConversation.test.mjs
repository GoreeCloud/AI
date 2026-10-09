import test from 'node:test'
import assert from 'node:assert/strict'
import { prepareFirstConversation } from './prepareFirstConversation.ts'

test('selects the created conversation only after its first messages persist', async () => {
  const steps = []
  const id = await prepareFirstConversation({
    create: async () => { steps.push('create'); return { id:'new-conversation' } },
    persist: async (id) => { steps.push('persist:'+id) },
    isCurrent: () => true,
    select: (id) => { steps.push('select:'+id) },
  })
  assert.equal(id,'new-conversation')
  assert.deepEqual(steps,['create','persist:new-conversation','select:new-conversation'])
})

test('a first-message save failure never switches selected conversation', async () => {
  const steps=[]
  const failure = new Error('disk is unavailable')
  await assert.rejects(prepareFirstConversation({
    create: async () => ({ id:'new-conversation' }),
    persist: async () => { steps.push('persist'); throw failure },
    isCurrent: () => true,
    select: () => { steps.push('selected') },
  }), error => error === failure)
  assert.deepEqual(steps, ['persist'])
})

test('navigation superseded during creation prevents stale first save or selection', async () => {
  let current = true
  const steps=[]
  await assert.rejects(prepareFirstConversation({
    create: async () => { current = false; return { id:'old-created' } },
    persist: async () => { steps.push('persist') },
    isCurrent: () => current,
    select: () => { steps.push('select') },
  }), /selection changed during creation/)
  assert.deepEqual(steps, [])
})

test('navigation superseded during persistence prevents selecting the saved child', async () => {
  let current = true
  const steps=[]
  await assert.rejects(prepareFirstConversation({
    create: async () => ({ id:'old-created' }),
    persist: async () => { steps.push('persist'); current = false },
    isCurrent: () => current,
    select: () => { steps.push('select') },
  }), /selection changed during preparation/)
  assert.deepEqual(steps, ['persist'])
})

test('creation failure is propagated without attempting persistence or selection', async () => {
  const failure = new Error('create unavailable')
  await assert.rejects(prepareFirstConversation({
    create: async () => { throw failure },
    persist: async () => { assert.fail('must not persist') },
    isCurrent: () => true,
    select: () => { assert.fail('must not select') },
  }), error => error === failure)
})
