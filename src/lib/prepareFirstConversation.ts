/**
 * Make first-message persistence the selection commit boundary.
 * A created, unsaved conversation must never become the selected UI context.
 */
export async function prepareFirstConversation(options: {
  create: () => Promise<{ id: string }>
  persist: (id: string) => Promise<void>
  isCurrent: () => boolean
  select: (id: string) => void
}): Promise<string> {
  const created = await options.create()
  if (!options.isCurrent()) throw new Error('Conversation selection changed during creation.')
  await options.persist(created.id)
  if (!options.isCurrent()) throw new Error('Conversation selection changed during preparation.')
  options.select(created.id)
  return created.id
}
