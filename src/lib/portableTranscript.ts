import type { ChatMessage } from './ollama'

export type PortableFormat = 'txt' | 'json'

export interface PortableTranscriptInput {
  title: string
  model: string
  workspace: string | null
  exportedAt: string
  messages: readonly ChatMessage[]
}

function oneLine(value: string): string {
  return value.replace(/[\u0000-\u001f\u007f-\u009f]+/g, ' ').replace(/\s+/gu, ' ').trim()
}

/** Exports the visible transcript only; this is not an Everkeep backup. */
export function buildPortableTranscript(input: PortableTranscriptInput, format: PortableFormat): string {
  if (format === 'json') {
    return JSON.stringify({
      format: 'goreecloud-ai-conversation-export',
      version: 1,
      title: input.title,
      model: input.model,
      workspace: input.workspace,
      exportedAt: input.exportedAt,
      messages: input.messages.map(({ role, content }) => ({ role, content })),
    }, null, 2) + '\n'
  }
  const lines = [
    'GoreeCloud AI conversation',
    'Title: ' + oneLine(input.title),
    'Model: ' + oneLine(input.model || 'Not selected'),
    'Workspace: ' + oneLine(input.workspace || 'None'),
    'Exported: ' + oneLine(input.exportedAt),
    '',
  ]
  for (const message of input.messages) {
    lines.push(message.role === 'assistant' ? 'GoreeCloud AI:' : 'You:', message.content, '')
  }
  return lines.join('\n')
}

export function portableFileName(title: string, format: PortableFormat): string {
  const stem = title.replace(/[^a-z0-9._-]+/gi, '-').replace(/^[.-]+|[.-]+$/g, '').slice(0, 80)
  return (stem || 'goreecloud-ai-conversation') + '.' + format
}
