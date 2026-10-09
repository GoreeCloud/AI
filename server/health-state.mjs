export function buildPublicHealthState({ artifactScannerConfigured = false } = {}) {
  return {
    status: 'ok',
    service: 'goreecloud-ai',
    localModelRuntime: 'configured',
    wardveilArtifactScanner: artifactScannerConfigured ? 'configured' : 'unconfigured',
  }
}
