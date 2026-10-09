/**
 * Unsaved drafts are scoped to the selected conversation in this browser tab.
 * No disk, localStorage, server call, telemetry, or cross-profile persistence.
 */
/** Avoid clearing a newer conversation when an older deletion resolves. */
export function shouldLeaveDeletedConversation(deletedId: string, selectedId: string | null, selectionEpochAtStart: number, selectionEpochNow: number): boolean {
  return deletedId === selectedId && selectionEpochAtStart === selectionEpochNow
}

export class SessionConversationDrafts {
  private readonly items = new Map<string, string>()
  private key(id: string | null): string { return id === null ? 'unsaved:' : 'conversation:' + id }

  remember(id: string | null, draft: string): void {
    const key = this.key(id)
    if (draft.length) this.items.set(key, draft)
    else this.items.delete(key)
  }

  restore(id: string | null): string {
    return this.items.get(this.key(id)) ?? ''
  }

  clear(id: string | null): void { this.items.delete(this.key(id)) }
}
