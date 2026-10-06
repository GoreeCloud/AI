import { isValidElement, type ReactNode, useEffect, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function nodeText(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(nodeText).join('')
  if (isValidElement<{ children?: ReactNode }>(node)) return nodeText(node.props.children)
  return ''
}

function codeLanguage(node: ReactNode): string | null {
  if (Array.isArray(node)) {
    for (const child of node) {
      const language = codeLanguage(child)
      if (language) return language
    }
    return null
  }
  if (!isValidElement<{ className?: string }>(node)) return null
  const match = node.props.className?.match(/(?:^|\s)language-([\w.+-]+)/)
  return match?.[1] ?? null
}

function CodeBlock({ children }: { children: ReactNode }) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle')
  const resetTimer = useRef<number | null>(null)

  useEffect(() => () => {
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
  }, [])

  async function copyCode() {
    const text = nodeText(children).replace(/\n$/, '')
    if (!text) return
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(text)
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current)
    resetTimer.current = window.setTimeout(() => setCopyState('idle'), 1800)
  }

  const label = copyState === 'copied' ? 'Code copied' : copyState === 'failed' ? 'Copy failed' : 'Copy code'
  const language = codeLanguage(children)
  return (
    <div className={`code-block-shell ${copyState}`}>
      <span className="code-language">{language || 'Code'}</span>
      <button type="button" className="code-copy-button" onClick={() => void copyCode()} aria-label={label} title={label}>
        {copyState === 'copied' ? <Check size={14}/> : <Copy size={14}/>}
      </button>
      <span className="visually-hidden" role="status" aria-live="polite">{copyState === 'copied' ? 'Code copied.' : copyState === 'failed' ? 'Code copy failed.' : ''}</span>
      <pre>{children}</pre>
    </div>
  )
}

export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...props }) {
            return <a href={href} target="_blank" rel="noreferrer" {...props}>{children}</a>
          },
          pre({ children }) {
            return <CodeBlock>{children}</CodeBlock>
          },
          code({ className, children, ...props }) {
            const block = Boolean(className) || String(children).includes('\n')
            return block ? <code className={className} {...props}>{children}</code> : <code className="inline-code" {...props}>{children}</code>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
