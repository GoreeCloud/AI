import { useEffect, useRef } from 'react'
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

  useEffect(() => {
    if (!open) return
    queueMicrotask(() => confirmRef.current?.focus())
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel() }}>
      <div className="dialog-card" role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-description">
        <div className="dialog-heading">
          <div><strong id="confirm-dialog-title">{title}</strong><span id="confirm-dialog-description">{description}</span></div>
          <button type="button" className="icon-button" onClick={onCancel} aria-label="Close dialog"><X size={18}/></button>
        </div>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>Cancel</button>
          <button ref={confirmRef} type="button" className="danger-button" onClick={() => void onConfirm()}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
