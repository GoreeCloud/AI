import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: string
  confirmLabel?: string
  onCancel: () => void
  onConfirm: () => void | Promise<void>
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Confirm', onCancel, onConfirm }: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement | null>(null)
  const pendingRef = useRef(false)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!open) return
    pendingRef.current = false
    setPending(false)
    queueMicrotask(() => confirmRef.current?.focus())
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !pendingRef.current) onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onCancel])

  if (!open) return null

  async function confirm() {
    if (pendingRef.current) return
    pendingRef.current = true
    setPending(true)
    try { await onConfirm() }
    finally {
      pendingRef.current = false
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (!pending && event.target === event.currentTarget) onCancel() }}>
      <div className="dialog-card" role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-description" aria-busy={pending}>
        <div className="dialog-heading">
          <div><strong id="confirm-dialog-title">{title}</strong><span id="confirm-dialog-description">{description}</span></div>
          <button type="button" className="icon-button" onClick={onCancel} aria-label="Close dialog" disabled={pending}><X size={18}/></button>
        </div>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={pending}>Cancel</button>
          <button ref={confirmRef} type="button" className="danger-button" onClick={() => void confirm()} disabled={pending}>{pending ? 'Working…' : confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
