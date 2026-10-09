/** Prevent duplicate asynchronous UI preparation before React renders. */
export async function runExclusivePreparation<T>(lock: { current: boolean }, setBusy: (value: boolean) => void, action: () => Promise<T>): Promise<{ started: boolean; value?: T }> {
  if (lock.current) return { started: false }
  lock.current = true
  setBusy(true)
  try { return { started: true, value: await action() } }
  finally { lock.current = false; setBusy(false) }
}
