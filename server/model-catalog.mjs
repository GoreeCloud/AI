const MAX_PUBLIC_MODELS = 256
const MAX_MODEL_NAME_CHARS = 512

export function sanitizePublicModelCatalog(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !Array.isArray(value.models)) {
    throw new Error('invalid_local_model_catalog')
  }

  const models = []
  const seen = new Set()
  for (const entry of value.models) {
    if (models.length >= MAX_PUBLIC_MODELS) break
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) continue
    if (typeof entry.name !== 'string') continue
    const name = entry.name.trim()
    if (!name || name.length > MAX_MODEL_NAME_CHARS || seen.has(name)) continue
    seen.add(name)
    models.push({ name })
  }
  return models
}
