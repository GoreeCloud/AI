const apiBaseUrl = (process.env.GOREECLOUD_AI_URL ?? 'http://127.0.0.1:8787').replace(/\/$/, '')
const apiToken = process.env.GOREECLOUD_AI_API_TOKEN?.trim()
const validateModel = process.env.VALIDATE_OLLAMA_MODEL?.trim()
const requireWardveilScanner = process.env.VALIDATE_REQUIRE_WARDVEIL_SCANNER === 'true'
const timeoutMs = positiveNumber(process.env.VALIDATION_TIMEOUT_MS, 30_000)

const headers = apiToken ? { Authorization: `Bearer ${apiToken}` } : {}

console.log('GoreeCloud AI runtime validation')
console.log(`GoreeCloud AI API: ${apiBaseUrl}`)

const health = await step('Application health', async () => {
  const response = await json(`${apiBaseUrl}/api/health`)
  assert(response?.status === 'ok', 'application health did not report ok')
  assert(response?.service === 'goreecloud-ai', `unexpected service identity: ${response?.service ?? 'missing'}`)
  assert(['configured', 'unconfigured'].includes(response?.wardveilArtifactScanner), 'Wardveil artifact scanner state is missing')
  if (requireWardveilScanner) assert(response.wardveilArtifactScanner === 'configured', 'Wardveil artifact scanner is required but unconfigured')
  return response
})

console.log(`  Wardveil artifact scanner: ${health.wardveilArtifactScanner}`)

const models = await step('Ollama discovery through GoreeCloud AI', async () => {
  const response = await json(`${apiBaseUrl}/api/ollama/models`, { headers })
  assert(Array.isArray(response?.models), 'model discovery payload is invalid')
  return response.models
})

console.log(`  discovered models: ${models.length}`)

if (!validateModel) {
  console.log('\nRuntime discovery validation passed.')
  console.log('Set VALIDATE_OLLAMA_MODEL to exercise one streamed chat request through the GoreeCloud AI backend.')
  process.exit(0)
}

assert(models.some((model) => model?.name === validateModel || model?.model === validateModel), `VALIDATE_OLLAMA_MODEL is not present in the discovered model set: ${validateModel}`)

await step('Streamed chat through GoreeCloud AI', async () => withTimeout(async (signal) => {
  const response = await fetch(`${apiBaseUrl}/api/ollama/chat`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
    body: JSON.stringify({
      model: validateModel,
      messages: [{ role: 'user', content: 'Respond briefly to confirm local runtime validation.' }],
    }),
    signal,
  })
  assert(response.ok, `${response.status} ${response.statusText} from streamed chat`)
  assert(response.body, 'streamed chat response body is missing')

  const decoder = new TextDecoder()
  const reader = response.body.getReader()
  let buffer = ''
  let chunks = 0
  let sawDone = false
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        const event = JSON.parse(line)
        if (typeof event?.message?.content === 'string' && event.message.content.length > 0) chunks += 1
        if (event?.done === true) sawDone = true
      }
    }
    buffer += decoder.decode()
    if (buffer.trim()) {
      const event = JSON.parse(buffer)
      if (typeof event?.message?.content === 'string' && event.message.content.length > 0) chunks += 1
      if (event?.done === true) sawDone = true
    }
  } finally {
    reader.releaseLock()
  }

  assert(chunks > 0, 'streamed chat produced no assistant content chunks')
  assert(sawDone, 'streamed chat did not produce a terminal done event')
  return `${chunks} content chunks`
}))

console.log('\nLive Ollama application-path validation passed.')
console.log('This validates the configured runtime path only; it does not establish Wardveil, Privacy Shield, Everkeep, Identity, Mesh, or Stable production acceptance.')

async function step(label, task) {
  process.stdout.write(`- ${label} ... `)
  try {
    const result = await task()
    console.log(`ok${result === undefined ? '' : ` (${format(result)})`}`)
    return result
  } catch (error) {
    console.log('failed')
    console.error(error instanceof Error ? error.message : error)
    process.exit(1)
  }
}

async function json(url, init = {}) {
  return withTimeout(async (signal) => {
    const response = await fetch(url, { ...init, signal })
    const text = await response.text()
    if (!response.ok) throw new Error(`${response.status} ${response.statusText} from ${url}${text ? `: ${text.slice(0, 500)}` : ''}`)
    return text ? JSON.parse(text) : null
  })
}

async function withTimeout(task) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(new Error(`validation request exceeded ${timeoutMs}ms`)), timeoutMs)
  try {
    return await task(controller.signal)
  } finally {
    clearTimeout(timeout)
  }
}

function positiveNumber(value, fallback) {
  const numeric = Number(value)
  return Number.isSafeInteger(numeric) && numeric > 0 ? numeric : fallback
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function format(value) {
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return `${value.length} items`
  return 'validated'
}
