import { FormEvent, useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

interface TextDialogProps {
  open: boolean
  title: string
  label: string
  initialValue: string
  multiline?: boolean
  confirmLabel?: string
  onCancel: () => void
  onConfirm: (value: string) => void | Promise<void>
}

export function TextDialog({ open, title, label, initialValue, multiline = false, confirmLabel = 'Save', onCancel, onConfirm }: TextDialogProps) {
  const [value, setValue] = useState(initialValue)
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!open) return
    setValue(initialValue)
    queueMicrotask(() => inputRef.current?.focus())
  }, [open, initialValue])

  if (!open) return null

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next = value.trim()
    if (!next) return
    await onConfirm(next)
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onCancel() }}>
      <form className="dialog-card" role="dialog" aria-modal="true" aria-labelledby="dialog-title" onSubmit={submit}>
        <div className="dialog-heading">
          <div><strong id="dialog-title">{title}</strong><span>{label}</span></div>
          <button type="button" className="icon-button" onClick={onCancel} aria-label="Close dialog"><X size={18}/></button>
        </div>
        {multiline ? (
          <textarea ref={(node) => { inputRef.current = node }} value={value} onChange={(event) => setValue(event.target.value)} rows={7}/>
        ) : (
          <input ref={(node) => { inputRef.current = node }} value={value} onChange={(event) => setValue(event.target.value)} />
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel}>Cancel</button>
          <button type="submit" className="primary-button" disabled={!value.trim()}>{confirmLabel}</button>
        </div>
      </form>
    </div>
  )
}
