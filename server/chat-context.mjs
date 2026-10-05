const WORKSPACE_ID = /^[0-9a-f-]{36}$/i

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
