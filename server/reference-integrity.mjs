export function validateConversationReferenceState(input, state = {}) {
  const workspaceId = typeof input?.workspaceId === 'string' ? input.workspaceId : null
  if (workspaceId && state.workspaceExists !== true) return { ok: false, reason: 'workspace_not_found' }

  const parentId = typeof input?.parentConversationId === 'string' ? input.parentConversationId : null
  const parentIndex = Number.isInteger(input?.parentMessageIndex) ? input.parentMessageIndex : null
  if ((parentId === null) !== (parentIndex === null)) return { ok: false, reason: 'incomplete_parent_lineage' }
  if (!parentId) return { ok: true }

  const parent = state.parentConversation
  if (!parent || parent.id !== parentId || !Array.isArray(parent.messages)) return { ok: false, reason: 'parent_not_found' }
  if (parentIndex < 0 || parentIndex >= parent.messages.length) return { ok: false, reason: 'parent_message_not_found' }
  return { ok: true }
}

export function validateWorkspaceFileReferenceState(workspaceId, fileIds, files) {
  if (!Array.isArray(fileIds)) return { ok: true }
  if (!Array.isArray(files)) return { ok: false, reason: 'file_catalog_unavailable' }

  const byId = new Map(files.map((file) => [file?.id, file]))
  for (const fileId of fileIds) {
    const file = byId.get(fileId)
    if (!file) return { ok: false, reason: 'file_not_found', fileId }
    if (file.workspaceId !== workspaceId) return { ok: false, reason: 'file_workspace_mismatch', fileId }
  }
  return { ok: true }
}
