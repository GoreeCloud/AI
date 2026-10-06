const WORKSPACE_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const CLIENT_CHAT_ROLES = new Set(['user', 'assistant'])
const MAX_CHAT_MESSAGES = 4096
const MAX_CHAT_MESSAGE_CHARS = 250_000
const MAX_MODEL_ID_CHARS = 512

function record(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function validateClientChatRequest(body) {
  if (!record(body)) return false
  if (typeof body.model !== 'string' || !body.model.length || body.model.length > MAX_MODEL_ID_CHARS || body.model.trim() !== body.model) return false
  if (!Array.isArray(body.messages) || body.messages.length < 1 || body.messages.length > MAX_CHAT_MESSAGES) return false
  if (body.messages.at(-1)?.role !== 'user') return false
  if (!body.messages.every((message) =>
    record(message) &&
    Object.keys(message).every((key) => key === 'role' || key === 'content') &&
    CLIENT_CHAT_ROLES.has(message.role) &&
    typeof message.content === 'string' &&
    message.content.length <= MAX_CHAT_MESSAGE_CHARS
  )) return false
  return normalizeWorkspaceId(body.workspaceId) !== undefined
}

export function normalizeWorkspaceId(value) {
  if (value === undefined || value === null || value === '') return null
  if (typeof value !== 'string' || !WORKSPACE_ID.test(value)) return undefined
  return value
}

export function composeWorkspaceChatMessages(messages, workspace = null) {
  const instructions = typeof workspace?.instructions === 'string' ? workspace.instructions.trim() : ''
  if (!instructions) return messages.map((message) => ({ ...message }))
  return [
    { role: 'system', content: `Workspace instructions:\n\n${instructions}` },
    ...messages.map((message) => ({ ...message })),
  ]
}
