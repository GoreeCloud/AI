import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Check, Copy } from 'lucide-react'
import { writeTranscriptOnRequest } from '../lib/transcriptClipboard'

type CopyState = 'idle' | 'copied' | 'unavailable' | 'failed'

/** Clipboard is written only by an explicit click; no automatic copy or persistence. */
export function CopyTranscriptButton({ format, getText, disabled }: {
  format: 'md' | 'txt' | 'json'
  getText: () => string
  disabled: boolean
}) {
  const [status, setStatus] = useState<CopyState>('idle')
  const attemptRef = useRef(0)

  useEffect(() => {
    attemptRef.current += 1
    setStatus('idle')
  }, [format, disabled])

  async function copy() {
    const attempt = ++attemptRef.current
    const writer = navigator.clipboard?.writeText?.bind(navigator.clipboard)
    const result = await writeTranscriptOnRequest(getText, writer)
    if (attempt !== attemptRef.current) return
    setStatus(result === 'copied' ? 'copied' : result === 'unavailable' ? 'unavailable' : 'failed')
  }

  const label = status === 'copied' ? 'Transcript copied' : status === 'unavailable'
    ? 'Clipboard unavailable in this browser' : status === 'failed' ? 'Transcript copy failed'
      : 'Copy selected transcript format to clipboard'
  return <button type="button" className="icon-button" disabled={disabled} onClick={() => void copy()} aria-label={label} title={label}>
    {status === 'copied' ? <Check size={18}/> : status === 'failed' || status === 'unavailable' ? <AlertCircle size={18}/> : <Copy size={18}/>}
    <span className="visually-hidden" role="status" aria-live="polite">{status === 'copied' ? 'Transcript copied to clipboard.' : status === 'unavailable' ? 'Clipboard is unavailable.' : status === 'failed' ? 'Transcript could not be copied.' : ''}</span>
  </button>
}
