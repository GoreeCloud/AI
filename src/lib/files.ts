export type FileTrustStatus = 'available' | 'held' | 'blocked' | 'unverified'

export interface FileSecurityState {
  disposition: string
  releaseAllowed: boolean
  useAsContextAllowed: boolean
  quarantineRequired: boolean
  reasonCodes: string[]
  evidenceRefs: string[]
  scanRecordId: string | null
}

export interface StoredFile {
  id: string
  name: string
  mediaType: string
  size: number
  workspaceId: string | null
  status: FileTrustStatus
  storageState: 'released' | 'staged'
  resourceId: string
  digestSha256: string | null
  security: FileSecurityState
  createdAt: string
}

export async function uploadFile(file: File, workspaceId?: string | null): Promise<StoredFile> {
  const response = await fetch('/api/files', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-File-Name': encodeURIComponent(file.name),
      ...(workspaceId ? { 'X-Workspace-Id': workspaceId } : {}),
    },
    body: file,
  })
  if (!response.ok) throw new Error(`File upload failed (${response.status})`)
  return response.json() as Promise<StoredFile>
}

export async function listFiles(): Promise<StoredFile[]> {
  const response = await fetch('/api/files', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`File list failed (${response.status})`)
  const data = await response.json() as { files: StoredFile[] }
  return data.files
}

export async function removeFile(id: string): Promise<void> {
  const response = await fetch(`/api/files/${id}`, { method: 'DELETE', credentials: 'same-origin' })
  if (!response.ok) throw new Error(`File deletion failed (${response.status})`)
}
