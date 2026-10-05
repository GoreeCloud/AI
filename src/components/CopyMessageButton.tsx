import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Check, Copy } from 'lucide-react'

type CopyState = 'idle' | 'copied' | 'failed'

export function CopyMessageButton({ content }: { content: string }) {
  const [copyState, setCopyState] = useState<CopyState>('idle')
  const resetTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
  }, [])

  async function copyMessage() {
    if (!content) return
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(content)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }

    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
    resetTimer.current = window.setTimeout(() => setCopyState('idle'), 1800)
  }

  const label = copyState === 'copied' ? 'Message copied' : copyState === 'failed' ? 'Copy failed' : 'Copy message'

  return (
    <button
      type="button"
      className={`message-copy-button ${copyState}`}
      onClick={() => void copyMessage()}
      aria-label={label}
      title={label}
    >
      {copyState === 'copied' ? <Check size={14}/> : copyState === 'failed' ? <AlertCircle size={14}/> : <Copy size={14}/>}
      <span className="visually-hidden" role="status" aria-live="polite">
        {copyState === 'copied' ? 'Message copied.' : copyState === 'failed' ? 'Message copy failed.' : ''}
      </span>
    </button>
  )
}
