import type { ModelRoleId } from './modelRoles'

export interface Workspace {
  id: string
  name: string
  instructions: string
  defaultModelRole: ModelRoleId
  fileIds: string[]
  knowledgeCollectionIds: string[]
  toolIds: string[]
  researchEnabled: boolean
  createdAt: string
  updatedAt: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) throw new Error(`Workspace request failed (${response.status})`)
  return response.json() as Promise<T>
}

export async function listWorkspaces(): Promise<Workspace[]> {
  const data = await request<{ workspaces: Workspace[] }>('/api/workspaces')
  return data.workspaces
}

export function getWorkspace(id: string): Promise<Workspace> {
  return request(`/api/workspaces/${id}`)
}

export function createWorkspace(input: Partial<Pick<Workspace, 'name' | 'instructions' | 'defaultModelRole' | 'researchEnabled'>> = {}): Promise<Workspace> {
  return request('/api/workspaces', { method: 'POST', body: JSON.stringify(input) })
}

export function saveWorkspace(id: string, patch: Partial<Omit<Workspace, 'id' | 'createdAt' | 'updatedAt'>>): Promise<Workspace> {
  return request(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
}

export async function removeWorkspace(id: string): Promise<void> {
  await request(`/api/workspaces/${id}`, { method: 'DELETE' })
}
