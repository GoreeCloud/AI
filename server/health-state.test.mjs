import test from 'node:test'
import assert from 'node:assert/strict'
import { buildPublicHealthState } from './health-state.mjs'

test('public health state reports capability state without runtime endpoint disclosure', () => {
  const health = buildPublicHealthState({ artifactScannerConfigured: false })

  assert.deepEqual(health, {
    status: 'ok',
    service: 'goreecloud-ai',
    localModelRuntime: 'configured',
    wardveilArtifactScanner: 'unconfigured',
  })
  assert.equal('ollama' in health, false)
  assert.equal(JSON.stringify(health).includes('127.0.0.1'), false)
  assert.equal(JSON.stringify(health).includes('11434'), false)
})

test('public health state can report configured Wardveil transport without adding endpoint data', () => {
  const health = buildPublicHealthState({ artifactScannerConfigured: true })
  assert.equal(health.wardveilArtifactScanner, 'configured')
  assert.deepEqual(Object.keys(health).sort(), ['localModelRuntime', 'service', 'status', 'wardveilArtifactScanner'].sort())
})
