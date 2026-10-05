import test from 'node:test'
import assert from 'node:assert/strict'
import { sanitizePublicModelCatalog } from './model-catalog.mjs'

test('publishes only unique bounded model names', () => {
  const models = sanitizePublicModelCatalog({
    models: [
      { name: ' gemma3:12b ', size: 123, details: { private: true } },
      { name: 'gemma3:12b', digest: 'duplicate' },
      { name: 'qwen3-coder:latest', model: 'internal-name' },
      { name: '' },
      { name: 'x'.repeat(513) },
      null,
    ],
  })
  assert.deepEqual(models, [
    { name: 'gemma3:12b' },
    { name: 'qwen3-coder:latest' },
  ])
})

test('caps the public model inventory at 256 records', () => {
  const models = sanitizePublicModelCatalog({
    models: Array.from({ length: 300 }, (_, index) => ({ name: `model-${index}` })),
  })
  assert.equal(models.length, 256)
  assert.equal(models.at(-1)?.name, 'model-255')
})

test('rejects invalid catalog envelopes', () => {
  for (const value of [null, [], {}, { models: null }]) {
    assert.throws(() => sanitizePublicModelCatalog(value), /invalid_local_model_catalog/)
  }
})
