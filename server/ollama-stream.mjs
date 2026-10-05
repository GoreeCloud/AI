const ASSISTANT_ROLE = 'assistant'
const MAX_RUNTIME_ERROR_CHARS = 2048

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function streamError(code, message) {
  return Object.assign(new Error(message), { code })
}

function parseLine(bytes) {
  let text
  try {
    text = new TextDecoder('utf-8', { fatal: true }).decode(bytes).trim()
  } catch {
    throw streamError('OLLAMA_STREAM_ENCODING_INVALID', 'Local runtime stream contained invalid UTF-8')
  }
  if (!text) return null

  let chunk
  try {
    chunk = JSON.parse(text)
  } catch {
    throw streamError('OLLAMA_STREAM_JSON_INVALID', 'Local runtime stream contained invalid NDJSON')
  }
  if (!record(chunk)) throw streamError('OLLAMA_STREAM_CHUNK_INVALID', 'Local runtime stream chunk must be an object')

  if (chunk.error !== undefined) {
    if (typeof chunk.error !== 'string' || !chunk.error.length || chunk.error.length > MAX_RUNTIME_ERROR_CHARS) {
      throw streamError('OLLAMA_STREAM_ERROR_INVALID', 'Local runtime stream error field is invalid')
    }
    return { error: 'Local model runtime reported an error' }
  }

  if (chunk.done !== undefined && typeof chunk.done !== 'boolean') {
    throw streamError('OLLAMA_STREAM_DONE_INVALID', 'Local runtime stream done field is invalid')
  }

  let content
  if (chunk.message !== undefined) {
    if (!record(chunk.message)) throw streamError('OLLAMA_STREAM_MESSAGE_INVALID', 'Local runtime stream message is invalid')
    if (chunk.message.role !== undefined && chunk.message.role !== ASSISTANT_ROLE) {
      throw streamError('OLLAMA_STREAM_ROLE_INVALID', 'Local runtime stream role is invalid')
    }
    if (chunk.message.content !== undefined && typeof chunk.message.content !== 'string') {
      throw streamError('OLLAMA_STREAM_CONTENT_INVALID', 'Local runtime stream content is invalid')
    }
    content = chunk.message.content
  }

  if (content === undefined && chunk.done !== true) return null

  return {
    ...(content !== undefined ? { message: { role: ASSISTANT_ROLE, content } } : {}),
    ...(chunk.done === true ? { done: true } : {}),
  }
}

export function createBoundedOllamaNdjsonParser({ maxStreamBytes, maxLineBytes, onChunk }) {
  if (!Number.isSafeInteger(maxStreamBytes) || maxStreamBytes <= 0) throw new Error('maxStreamBytes must be a positive integer')
  if (!Number.isSafeInteger(maxLineBytes) || maxLineBytes <= 0) throw new Error('maxLineBytes must be a positive integer')
  if (typeof onChunk !== 'function') throw new Error('onChunk must be a function')

  let totalBytes = 0
  let buffer = Buffer.alloc(0)

  function consumeLine(line) {
    if (line.length > maxLineBytes) throw streamError('OLLAMA_STREAM_LINE_TOO_LARGE', 'Local runtime stream line exceeded the configured limit')
    const parsed = parseLine(line)
    if (parsed) onChunk(parsed)
  }

  return {
    push(value) {
      const chunk = Buffer.from(value)
      totalBytes += chunk.length
      if (totalBytes > maxStreamBytes) throw streamError('OLLAMA_STREAM_TOO_LARGE', 'Local runtime stream exceeded the configured limit')

      buffer = buffer.length ? Buffer.concat([buffer, chunk]) : chunk
      let newline
      while ((newline = buffer.indexOf(0x0a)) !== -1) {
        const line = buffer.subarray(0, newline)
        buffer = buffer.subarray(newline + 1)
        consumeLine(line)
      }

      if (buffer.length > maxLineBytes) {
        throw streamError('OLLAMA_STREAM_LINE_TOO_LARGE', 'Local runtime stream line exceeded the configured limit')
      }
    },

    finish() {
      if (buffer.length) consumeLine(buffer)
      buffer = Buffer.alloc(0)
    },

    get totalBytes() {
      return totalBytes
    },
  }
}
