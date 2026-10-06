import type { OllamaModel } from './ollama'

export type ModelRoleId = 'assistant' | 'reasoner' | 'engineer' | 'utility' | 'embeddings' | 'vision' | 'second-opinion'

export interface ModelRoleDefinition {
  id: ModelRoleId
  name: string
  purpose: string
  candidateHints: string[]
  conversational: boolean
  optional?: boolean
}

export interface ResolvedModelRole extends ModelRoleDefinition {
  model?: OllamaModel
}

export const modelRoles: ModelRoleDefinition[] = [
  { id: 'assistant', name: 'GoreeCloud Assistant', purpose: 'General-purpose conversation and assistance', candidateHints: ['qwen3.5', 'qwen3_5', 'qwen3-5'], conversational: true },
  { id: 'reasoner', name: 'GoreeCloud Reasoner', purpose: 'Complex reasoning, architecture, and research', candidateHints: ['gpt-oss', 'gptoss'], conversational: true },
  { id: 'engineer', name: 'GoreeCloud Engineer', purpose: 'Infrastructure engineering, coding, and configuration', candidateHints: ['qwen3-coder', 'qwen3coder'], conversational: true },
  { id: 'utility', name: 'GoreeCloud Utility', purpose: 'Lightweight and recurring AI processing', candidateHints: ['qwen3:4b', 'qwen3-4b', 'qwen3_4b'], conversational: true },
  { id: 'embeddings', name: 'GoreeCloud Embeddings', purpose: 'Semantic retrieval and RAG indexing', candidateHints: ['qwen3-embedding', 'qwen3embedding'], conversational: false },
  { id: 'vision', name: 'GoreeCloud Vision', purpose: 'Specialized vision and multimodal analysis', candidateHints: ['gemma4', 'gemma-4'], conversational: true, optional: true },
  { id: 'second-opinion', name: 'GoreeCloud Second Opinion', purpose: 'Independent reasoning and validation', candidateHints: ['deepseek-r1', 'deepseekr1'], conversational: true, optional: true },
]

function normalized(value: string) {
  return value.toLowerCase().replace(/\s+/g, '')
}

export function resolveModelRoles(models: OllamaModel[]): ResolvedModelRole[] {
  return modelRoles.map((role) => ({
    ...role,
    model: models.find((model) => role.candidateHints.some((hint) => normalized(model.name).includes(normalized(hint)))),
  }))
}

export function roleForModel(modelName: string, models: OllamaModel[]): ResolvedModelRole | undefined {
  return resolveModelRoles(models).find((role) => role.model?.name === modelName)
}
