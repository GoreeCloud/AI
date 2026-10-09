import type { ChatMessage } from './ollama'

/** Invalidates asynchronous UI work when the selected conversation changes. */
export class ConversationEpoch {
  private epoch = 0
  value(): number { return this.epoch }
  begin(): number { return ++this.epoch }
  invalidate(): void { this.epoch += 1 }
  isCurrent(value: number): boolean { return value === this.epoch }
}

function normalizeSearch(value: string): string {
  return value.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase()
}

/** All query words must match visible summary fields; no message-body indexing. */
export function historyMatches(query: string, fields: readonly string[]): boolean {
  if (query.length > 120) return false
  const terms = normalizeSearch(query).trim().split(/\s+/u).filter(Boolean)
  if (terms.length > 16) return false
  if (!terms.length) return true
  const text = fields.map(normalizeSearch).join(' ')
  return terms.every((term) => text.includes(term))
}

function inlineLabel(value: string): string {
  return value.replace(/[\u0000-\u001f\u007f-\u009f]+/g, ' ').replace(/\s+/gu, ' ').trim()
    .replace(/([\\\x60*_{}\[\]()#+.!|>~-])/g, '\\$1')
}

export interface MarkdownTranscriptInput {
  title: string
  model: string
  workspace: string | null
  exportedAt: string
  messages: readonly ChatMessage[]
}

/** User-controlled local Markdown export, not backup or authorization evidence. */
export function buildMarkdownTranscript(input: MarkdownTranscriptInput): string {
  const lines = [
    '# ' + (inlineLabel(input.title) || 'GoreeCloud AI conversation'),
    '',
    '- Exported: ' + inlineLabel(input.exportedAt),
    '- Model: ' + inlineLabel(input.model || 'Not selected'),
    '- Workspace: ' + inlineLabel(input.workspace || 'None'),
    '',
  ]
  for (const message of input.messages) {
    lines.push('## ' + (message.role === 'assistant' ? 'GoreeCloud AI' : 'You'), '', message.content, '')
  }
  return lines.join('\n')
}

export function exportFileName(title: string): string {
  const stem = title.replace(/[^a-z0-9._-]+/gi, '-').replace(/^[.-]+|[.-]+$/g, '').slice(0, 80)
  return (stem || 'goreecloud-ai-conversation') + '.md'
}

/** A text composition candidate must not be interpreted as Enter-to-send. */
export function shouldSubmitComposerKey(event: {
  key: string
  shiftKey: boolean
  altKey?: boolean
  ctrlKey?: boolean
  metaKey?: boolean
  isComposing?: boolean
  keyCode?: number
  repeat?: boolean
}): boolean {
  return event.key === 'Enter' && !event.shiftKey && !event.altKey
    && !event.ctrlKey && !event.metaKey && !event.isComposing
    && event.keyCode !== 229 && !event.repeat
}
