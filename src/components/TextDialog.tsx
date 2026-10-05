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
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pendingRef = useRef(false)
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (!open) return
    setValue(initialValue)
    pendingRef.current = false
    setPending(false)
    setError(null)
    queueMicrotask(() => inputRef.current?.focus())
  }, [open, initialValue])

  if (!open) return null

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next = value.trim()
    if (!next || pendingRef.current) return
    pendingRef.current = true
    setPending(true)
    setError(null)
    try { await onConfirm(next) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The change could not be saved.') }
    finally {
      pendingRef.current = false
      setPending(false)
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (!pendingRef.current && event.target === event.currentTarget) onCancel() }}>
      <form className="dialog-card" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby="dialog-description" aria-busy={pending} onKeyDown={(event) => { if (event.key === 'Escape' && !pendingRef.current) { event.preventDefault(); onCancel() } }} onSubmit={submit}>
        <div className="dialog-heading">
          <div><strong id="dialog-title">{title}</strong><span id="dialog-description">{label}</span></div>
          <button type="button" className="icon-button" onClick={onCancel} aria-label="Close dialog" disabled={pending}><X size={18}/></button>
        </div>
        {multiline ? (
          <textarea ref={(node) => { inputRef.current = node }} value={value} onChange={(event) => setValue(event.target.value)} rows={7}/>
        ) : (
          <input ref={(node) => { inputRef.current = node }} value={value} onChange={(event) => setValue(event.target.value)} />
        )}
        {error && <p className="dialog-error" role="alert">{error}</p>}
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={pending}>Cancel</button>
          <button type="submit" className="primary-button" disabled={!value.trim() || pending}>{pending ? 'Saving…' : confirmLabel}</button>
        </div>
      </form>
    </div>
  )
}
