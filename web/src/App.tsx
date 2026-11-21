import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

type Tab = 'Chat' | 'Images' | 'Documents' | 'Agents' | 'MCP'
type Message = { role: 'user' | 'assistant'; content: string }
type SavedDoc = { id: string; title: string; body?: string; updated_at: string }
type DocumentRevision = { id: string; document_id: string; title: string;
  created_at: string; body_characters?: number; body?: string }
type SavedConversation = { id: string; title: string; messages?: Message[]; message_count?: number }
type SearchHit = { id: string; title: string; excerpt: string }
type ConsentReceipt = { id: string; created_at: string; kind: string; approval: string }
type ImageCatalogEntry = { id: string; name: string; supports_reference: boolean; supports_streaming: boolean }

function apiOrigin(value: string): string {
  const url = new URL(value)
  const loopback = url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname)
  if (!loopback && url.protocol !== 'https:')
    throw Error('Use HTTPS for remote servers, or HTTP on local loopback only.')
  if (url.username || url.password || url.hash || url.search || url.pathname !== '/')
    throw Error('Enter the server origin without credentials, path or query.')
  return url.origin
}

export default function App() {
  const [tab, setTab] = useState<Tab>('Chat')
  const [endpoint, setEndpoint] = useState('http://127.0.0.1:8000')
  const [token, setToken] = useState('')
  const [provider, setProvider] = useState('auto')
  const [model, setModel] = useState('openrouter/auto')
  const [fallback, setFallback] = useState(false)
  const [cloudConsent, setCloudConsent] = useState(false)
  const [streaming, setStreaming] = useState(true)
  const streamAbort = useRef<AbortController | null>(null)
  const [savedChats, setSavedChats] = useState<SavedConversation[]>([])
  const [chatQuery, setChatQuery] = useState('')
  const [chatResults, setChatResults] = useState<SavedConversation[] | null>(null)
  const [searchText, setSearchText] = useState('')
  const [searchHits, setSearchHits] = useState<SearchHit[]>([])
  const [researchAnswer, setResearchAnswer] = useState('')
  const [researchSources, setResearchSources] = useState<Array<{ id: string; title: string }>>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [imagePrompt, setImagePrompt] = useState('')
  const [imageModel, setImageModel] = useState('bytedance-seed/seedream-4.5')
  const [imageModels, setImageModels] = useState<ImageCatalogEntry[]>([])
  const [reference, setReference] = useState<string | null>(null)
  const [paidApproved, setPaidApproved] = useState(false)
  const [image, setImage] = useState('')
  const [imageCost, setImageCost] = useState<number | null>(null)
  const [imageMime, setImageMime] = useState('image/png')
  const [docs, setDocs] = useState<SavedDoc[]>([])
  const [docId, setDocId] = useState('')
  const [docTitle, setDocTitle] = useState('')
  const [docBody, setDocBody] = useState('')
  const [recordRevision, setRecordRevision] = useState(false)
  const [documentRevisions, setDocumentRevisions] = useState<DocumentRevision[]>([])
  const [previewRevision, setPreviewRevision] = useState<DocumentRevision | null>(null)
  const [goal, setGoal] = useState('')
  const [plan, setPlan] = useState('')
  const [tools, setTools] = useState<string[]>([])
  const [toolName, setToolName] = useState('')
  const [toolArguments, setToolArguments] = useState('{}')
  const [toolApproval, setToolApproval] = useState(false)
  const [toolResult, setToolResult] = useState('')
  const [busy, setBusy] = useState(false)
  const [alert, setAlert] = useState('')
  const [notice, setNotice] = useState('')
  const [consentReceipts, setConsentReceipts] = useState<ConsentReceipt[]>([])
  const [receiptsLoaded, setReceiptsLoaded] = useState(false)
  const [privacyInfo, setPrivacyInfo] = useState<{
    auth_mode: string; document_storage: string; conversation_retention_days: number;
    consent_receipt_retention_days: number; provider_key_cap_required: boolean;
    cloud_requests: { remaining: number; limit: number }
  } | null>(null)

  async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    if (!token.trim()) throw Error('Set an owner token first.')
    const result = await fetch(apiOrigin(endpoint) + path, {
      method,
      headers: { 'Authorization': 'Bearer ' + token,
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store', referrerPolicy: 'no-referrer'
    })
    if (!result.ok) {
      const details: unknown = await result.json().catch(() => ({}))
      const detail = typeof details === 'object' && details !== null && 'detail' in details
        ? String(details.detail) : ''
      throw Error(detail || 'Request failed: ' + result.status)
    }
    if (result.status === 204) return undefined as T
    return await result.json() as T
  }

  async function action(task: () => Promise<void>) {
    if (busy) return
    setBusy(true); setAlert(''); setNotice('')
    try { await task() }
    catch (e) {
      if (e instanceof Error && e.name === 'AbortError') setNotice('Stream cancelled by user.')
      else setAlert(e instanceof Error ? e.message : 'Unexpected failure')
    }
    finally { setBusy(false) }
  }

  function send(e: FormEvent) {
    e.preventDefault()
    if (!prompt.trim() || busy) return
    const next: Message[] = [...messages, { role: 'user', content: prompt.trim() }]
    setMessages(next); setPrompt('')
    void action(async () => {
      const payload = { messages: next, provider, model,
        allow_local_fallback: fallback, allow_cloud_processing: cloudConsent }
      if (!streaming) {
        const reply = await api<{ content: string; provider: string; model: string }>(
          '/api/v1/chat', 'POST', payload)
        setMessages([...next, { role: 'assistant', content: reply.content }])
        setNotice('Response via ' + reply.provider + ' · ' + reply.model)
        return
      }
      const controller = new AbortController()
      streamAbort.current = controller
      try {
        const response = await fetch(apiOrigin(endpoint) + '/api/v1/chat/stream', {
          method: 'POST',
          headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
          referrerPolicy: 'no-referrer', cache: 'no-store'
        })
        if (!response.ok) {
          const details = await response.json().catch(() => ({})) as { detail?: string }
          throw Error(details.detail || 'Streaming request failed (' + response.status + ')')
        }
        if (!response.body) throw Error('Streaming unavailable in this browser')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let pending = ''
        let output = ''
        let complete = false
        while (true) {
          const part = await reader.read()
          if (part.done) break
          pending += decoder.decode(part.value, { stream: true })
          if (pending.length > 250000) throw Error('Stream event exceeded buffer limit')
          const records = pending.split('\n\n')
          pending = records.pop() || ''
          for (const record of records) {
            if (!record.startsWith('data: ')) continue
            const event = JSON.parse(record.slice(6)) as
              { type: string; content?: string; message?: string; provider?: string; model?: string }
            if (event.type === 'error') throw Error(event.message || 'Upstream stream error')
            if (event.type === 'delta' && event.content) {
              output += event.content
              if (output.length > 120000) throw Error('Response text limit reached')
              setMessages([...next, { role: 'assistant', content: output }])
            }
            if (event.type === 'done') {
              complete = true
              setNotice('Stream complete · ' + event.provider + ' · ' + event.model)
            }
          }
        }
        if (!complete) throw Error('Model stream stopped before completion')
      } finally { streamAbort.current = null }
    })
  }

  function generateImage(e: FormEvent) {
    e.preventDefault()
    const selected = imageModels.find(item => item.id === imageModel)
    if (reference && selected && !selected.supports_reference) {
      setAlert('This image model does not advertise reference-image support.')
      return
    }
    void action(async () => {
      const reply = await api<{ image: string; cost: number | null; media_type: string }>(
        '/api/v1/images', 'POST',
        { prompt: imagePrompt, model: imageModel, reference_data_url: reference,
          approve_paid_generation: paidApproved })
      setImage(reply.image); setImageCost(reply.cost); setImageMime(reply.media_type)
      setPaidApproved(false)
      setNotice('Generated output received. Save locally to retain it.')
    })
  }

  async function loadImageModels() {
    await action(async () => {
      const result = await api<{ models: ImageCatalogEntry[] }>('/api/v1/images/models')
      setImageModels(result.models)
      setNotice(result.models.length + ' available image models listed (no generation or paid request).')
    })
  }

  function setReferenceFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) { setReference(null); return }
    if (!['image/png','image/jpeg','image/webp'].includes(file.type) || file.size > 5_000_000) {
      setAlert('Reference must be PNG, JPEG or WebP under 5 MB.'); return
    }
    const reader = new FileReader()
    reader.onload = () => setReference(String(reader.result || ''))
    reader.readAsDataURL(file)
  }

  async function saveCurrentChat() {
    if (!messages.length) return
    await action(async () => {
      const first = messages.find(m => m.role === 'user')?.content || 'Saved conversation'
      await api<SavedConversation>('/api/v1/conversations', 'POST',
        { title: first.slice(0, 100), messages })
      setSavedChats(await api<SavedConversation[]>('/api/v1/conversations'))
      setNotice('Conversation snapshot saved locally. No cloud request was made.')
    })
  }

  async function refreshPrivacy() {
    await action(async () => {
      setPrivacyInfo(await api('/api/v1/privacy/status'))
      setNotice('Current local privacy and request-limit settings loaded.')
    })
  }

  async function refreshConsentReceipts() {
    await action(async () => {
      const result = await api<{ receipts: ConsentReceipt[] }>('/api/v1/privacy/consent-receipts?limit=15')
      setConsentReceipts(result.receipts)
      setReceiptsLoaded(true)
      setNotice('Local admission receipts loaded; no prompt contents or provider charges are recorded.')
    })
  }

  async function clearConsentReceipts() {
    if (!window.confirm(
      'Clear local cloud-consent admission receipts? Request-count quota and backups are unchanged.'
    )) return
    await action(async () => {
      const result = await api<{ deleted_receipts: number }>(
        '/api/v1/privacy/consent-receipts/clear', 'POST', { approved: true })
      setConsentReceipts([])
      setReceiptsLoaded(true)
      setNotice(result.deleted_receipts + ' local consent receipts cleared. Request-count quota unchanged.')
    })
  }

  async function purgeOldChats() {
    if (!window.confirm(
      'Permanently delete expired locally saved chats? Backups and SQLite freed pages may retain copies.'
    )) return
    await action(async () => {
      const reply = await api<{ deleted_conversations: number }>(
        '/api/v1/privacy/purge-expired', 'POST', { approved: true })
      setSavedChats(await api<SavedConversation[]>('/api/v1/conversations'))
      setNotice(reply.deleted_conversations + ' expired conversation snapshots deleted.')
    })
  }

  async function refreshChats() {
    await action(async () => setSavedChats(await api<SavedConversation[]>('/api/v1/conversations')))
  }

  async function openChat(id: string) {
    await action(async () => {
      const saved = await api<SavedConversation>('/api/v1/conversations/' + id)
      setMessages(saved.messages || [])
      setCloudConsent(false)
      setNotice('Loaded local conversation snapshot.')
    })
  }

  async function importChatFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (file.size > 350000 || !file.name.toLowerCase().endsWith('.json')) {
      setAlert('Choose a GoreeCloud conversation JSON export smaller than 350 KB.')
      return
    }
    await action(async () => {
      const document: unknown = JSON.parse(await file.text())
      await api('/api/v1/conversations/import', 'POST', document)
      setSavedChats(await api<SavedConversation[]>('/api/v1/conversations'))
      setChatResults(null)
      setNotice('Imported a new local snapshot. Original IDs and timestamps were not reused.')
    })
  }

  async function searchChats() {
    if (chatQuery.trim().length < 2) {
      setAlert('Enter at least two characters to search saved chats.')
      return
    }
    await action(async () => {
      const reply = await api<{ results: SavedConversation[] }>(
        '/api/v1/search/conversations?q=' + encodeURIComponent(chatQuery.trim()))
      setChatResults(reply.results)
      setNotice(reply.results.length + ' matching local saved conversations. No cloud processing.')
    })
  }

  async function renameChat(id: string, oldTitle: string) {
    const value = window.prompt('Rename saved conversation', oldTitle)
    if (value === null) return
    const title = value.trim()
    if (!title || title.length > 150) { setAlert('Enter a title of 1–150 characters.'); return }
    await action(async () => {
      await api('/api/v1/conversations/' + id, 'PATCH', { title })
      setSavedChats(await api<SavedConversation[]>('/api/v1/conversations'))
      setChatResults(null)
      setNotice('Saved conversation renamed locally.')
    })
  }

  async function exportChat(id: string, format: 'json' | 'md') {
    await action(async () => {
      if (!token.trim()) throw Error('Set an owner token first.')
      const reply = await fetch(apiOrigin(endpoint) +
        '/api/v1/conversations/' + id + '/export?format=' + format, {
        headers: { Authorization: 'Bearer ' + token },
        cache: 'no-store', referrerPolicy: 'no-referrer'
      })
      if (!reply.ok) throw Error('Conversation export failed (' + reply.status + ')')
      const objectURL = URL.createObjectURL(await reply.blob())
      const anchor = document.createElement('a')
      anchor.href = objectURL
      anchor.download = 'goreecloud-conversation-' + id + '.' + format
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(objectURL), 1000)
      setNotice('Private conversation downloaded to your device. Protect the unencrypted file.')
    })
  }

  function branchChat(index: number) {
    if (busy) return
    setMessages(messages.slice(0, index + 1))
    setCloudConsent(false)
    setNotice('Branched in this tab; save explicitly to retain the new conversation.')
  }

  async function deleteChat(id: string) {
    if (!window.confirm('Permanently delete this locally saved conversation?')) return
    await action(async () => {
      await api<void>('/api/v1/conversations/' + id, 'DELETE')
      setSavedChats(await api<SavedConversation[]>('/api/v1/conversations'))
      setChatResults(null)
      setNotice('Saved conversation deleted.')
    })
  }

  async function findDocs() {
    if (!searchText.trim()) return
    await action(async () => {
      const result = await api<{ results: SearchHit[] }>(
        '/api/v1/search/documents?q=' + encodeURIComponent(searchText.trim()))
      setSearchHits(result.results)
      setResearchAnswer(''); setResearchSources([])
      setNotice(result.results.length + ' local matches. No cloud request was made.')
    })
  }

  async function askDocuments() {
    if (!searchText.trim()) return
    await action(async () => {
      const result = await api<{
        answer: string; sources: Array<{ id: string; title: string }>; sent_to_cloud: boolean
      }>('/api/v1/research/answer', 'POST', {
        question: searchText.trim(), provider, allow_cloud_processing: cloudConsent
      })
      setResearchAnswer(result.answer)
      setResearchSources(result.sources)
      setNotice(result.sent_to_cloud
        ? 'Selected local excerpts were sent to OpenRouter with your consent.'
        : 'Answer used local inference or no inference.')
    })
  }

  async function deleteDoc() {
    if (!docId || !window.confirm('Permanently delete this document and its search index?')) return
    await action(async () => {
      await api<void>('/api/v1/documents/' + docId, 'DELETE')
      setDocId(''); setDocTitle(''); setDocBody('')
      setDocumentRevisions([]); setPreviewRevision(null); setRecordRevision(false)
      setDocs(await api<SavedDoc[]>('/api/v1/documents'))
      setSearchHits([])
      setNotice('Document permanently removed from the local database.')
    })
  }

  async function refreshDocs() {
    await action(async () => setDocs(await api<SavedDoc[]>('/api/v1/documents')))
  }

  async function openDoc(id: string) {
    await action(async () => {
      const doc = await api<SavedDoc>('/api/v1/documents/' + id)
      setDocId(doc.id); setDocTitle(doc.title); setDocBody(doc.body || '')
      setDocumentRevisions([]); setPreviewRevision(null); setRecordRevision(false)
    })
  }

  async function refreshDocumentRevisions() {
    if (!docId) return
    await action(async () => {
      const reply = await api<{ revisions: DocumentRevision[] }>(
        '/api/v1/documents/' + docId + '/revisions')
      setDocumentRevisions(reply.revisions)
      setPreviewRevision(null)
      setNotice(reply.revisions.length + ' saved earlier versions. No cloud request.')
    })
  }

  async function inspectRevision(id: string) {
    if (!docId) return
    await action(async () => {
      const revision = await api<DocumentRevision>(
        '/api/v1/documents/' + docId + '/revisions/' + id)
      setPreviewRevision(revision)
      setNotice('Previous version loaded for read-only review. Editor unchanged.')
    })
  }

  async function restoreRevision(id: string) {
    if (!docId || !window.confirm(
      'Replace the saved document with this earlier version? The current saved version ' +
      'will be snapshotted for recovery, but unsaved editor changes will be lost.'
    )) return
    await action(async () => {
      const restored = await api<SavedDoc>(
        '/api/v1/documents/' + docId + '/revisions/' + id + '/restore',
        'POST', { approved: true })
      setDocTitle(restored.title); setDocBody(restored.body || '')
      setDocumentRevisions([]); setPreviewRevision(null); setRecordRevision(false)
      setDocs(await api<SavedDoc[]>('/api/v1/documents'))
      setNotice('Restored locally. The displaced saved version is available in history.')
    })
  }

  function saveDoc(e: FormEvent) {
    e.preventDefault()
    void action(async () => {
      const saved = await api<SavedDoc>('/api/v1/documents' + (docId ? '/' + docId : ''),
        docId ? 'PUT' : 'POST', {
          title: docTitle, body: docBody, record_revision: docId ? recordRevision : false
        })
      setDocId(saved.id); setRecordRevision(false)
      setDocumentRevisions([]); setPreviewRevision(null)
      setDocs(await api<SavedDoc[]>('/api/v1/documents'))
      setNotice('Document saved in the configured local database.')
    })
  }

  async function importFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await action(async () => {
      const form = new FormData(); form.append('file', file)
      const reply = await fetch(apiOrigin(endpoint) + '/api/v1/documents/extract', {
        method: 'POST', headers: { Authorization: 'Bearer ' + token }, body: form
      })
      if (!reply.ok) throw Error('Document import failed (' + reply.status + ')')
      const extracted = await reply.json() as { name: string; text: string; truncated: boolean }
      setDocId(''); setDocTitle(extracted.name); setDocBody(extracted.text)
      setDocumentRevisions([]); setPreviewRevision(null); setRecordRevision(false)
      setNotice(extracted.truncated ? 'Imported preview truncated at 250,000 characters.' : 'Loaded into editor. Save to retain.')
    })
  }

  async function exportDoc(format: 'md' | 'docx') {
    await action(async () => {
      const reply = await fetch(apiOrigin(endpoint) +
        '/api/v1/documents/' + docId + '/export?format=' + format,
        { headers: { Authorization: 'Bearer ' + token } })
      if (!reply.ok) throw Error('Export failed')
      const objectURL = URL.createObjectURL(await reply.blob())
      const anchor = document.createElement('a'); anchor.href = objectURL
      anchor.download = (docTitle.replace(/[^a-z0-9_-]/gi, '-') || 'document') + '.' + format
      anchor.click()
      setTimeout(() => URL.revokeObjectURL(objectURL), 1000)
    })
  }

  function planAgent(e: FormEvent) {
    e.preventDefault()
    void action(async () => {
      const response = await api<{ plan: string }>('/api/v1/agents/plan', 'POST', { goal, provider, allow_cloud_processing: cloudConsent })
      setPlan(response.plan); setNotice('The agent plan was created. No tool executed.')
    })
  }

  async function agentRead() {
    await action(async () => {
      const response = await api<{ result: SavedDoc }>('/api/v1/agents/run', 'POST',
        { action: 'document.read', document_id: docId, approved: true })
      setToolResult(response.result.title + '\n\n' + (response.result.body || ''))
      setNotice('Approved local read completed.')
    })
  }

  async function discoverTools() {
    await action(async () => {
      const reply = await api<{ tools: string[] }>('/api/v1/mcp/tools')
      setTools(reply.tools); setNotice('Discovered tools; none executed.')
    })
  }

  function callTool(e: FormEvent) {
    e.preventDefault()
    void action(async () => {
      const parsed: unknown = JSON.parse(toolArguments)
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
        throw Error('Enter a JSON object for tool arguments.')
      const reply = await api<unknown>('/api/v1/mcp/call', 'POST',
        { name: toolName, arguments: parsed, approved: toolApproval })
      setToolResult(JSON.stringify(reply, null, 2)); setToolApproval(false)
      setNotice('Tool response received.')
    })
  }

  return <div className="gc-app app" data-gc-theme="dark" data-gc-accent="iris">
    <aside className="navigation" aria-label="Primary navigation">
      <div className="brand"><span className="symbol">✦</span><div><strong>GoreeCloud <em>AI</em></strong>
        <small>Intelligence workspace</small></div></div>
      <nav>{(['Chat','Images','Documents','Agents','MCP'] as Tab[]).map(name =>
        <button key={name} type="button" className={'nav-button ' + (tab === name ? 'selected' : '')}
          onClick={() => { setTab(name); setAlert(''); setNotice('') }}
          aria-current={tab === name ? 'page' : undefined}>{name}</button>)}</nav>
      <div className="navigation-foot">DEVELOPER PREVIEW<p>Cloud requests transmit selected content to the chosen provider. Review sensitive inputs before sending.</p></div>
    </aside>
    <main>
      <header className="toolbar">
        <div><small className="eyebrow">GOREECLOUD / INTELLIGENCE</small><h1>{tab}</h1></div>
        <div className="credentials">
          <label>API endpoint<input value={endpoint} onChange={e => setEndpoint(e.target.value)} /></label>
          <label>Owner token<input type="password" autoComplete="off" value={token}
            placeholder="Kept in this tab only" onChange={e => setToken(e.target.value)} /></label>
        </div>
      </header>
      {alert && <p className="notice error" role="alert">{alert}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}

      {tab === 'Chat' && <div className="split">
        <div className="chat">
          <div className="thread" role="log" aria-live="polite">
            {messages.length === 0 && <div className="empty"><span className="symbol">✳</span>
              <h2>What would you like to work on?</h2>
              <p>Reason, create, research and plan from one calm workspace.</p></div>}
            {messages.map((entry, i) => <article key={i} className={'message ' + entry.role}>
              <strong>{entry.role === 'user' ? 'You' : 'GoreeCloud AI'}</strong>
              <p>{entry.content}</p>
              {i < messages.length - 1 && <button type="button" className="secondary branch-action"
                disabled={busy} onClick={() => branchChat(i)}
                aria-label={'Branch conversation after message ' + (i + 1)}>Branch from here</button>}
            </article>)}
          </div>
          <form className="composer" onSubmit={send}>
            <label className="sr-only" htmlFor="chat-prompt">Chat prompt</label>
            <textarea id="chat-prompt" value={prompt} rows={3} placeholder="Ask anything…" onChange={e => setPrompt(e.target.value)} />
            <div className="actions"><small>Cloud processing requires separate consent.</small>
              {busy && streaming && <button type="button" className="secondary"
                onClick={() => streamAbort.current?.abort()}>Stop stream</button>}
              <button disabled={busy || !prompt.trim()}>Send message</button></div>
          </form>
        </div>
        <aside className="controls"><h2>Model routing</h2>
          <label>Provider<select value={provider} onChange={e => setProvider(e.target.value)}>
            <option value="auto">Auto · OpenRouter first</option>
            <option value="openrouter">OpenRouter</option>
            <option value="ollama">Ollama local</option>
          </select></label>
          <label>Model ID<input value={model} onChange={e => setModel(e.target.value)} /></label>
          <label className="check"><input type="checkbox" checked={cloudConsent}
            onChange={e => setCloudConsent(e.target.checked)} /> Allow selected text to leave this server for OpenRouter inference</label>
          <label className="check"><input type="checkbox" checked={fallback} disabled={streaming}
            onChange={e => setFallback(e.target.checked)} /> Allow local fallback on transient OpenRouter errors (non-stream mode)</label>
          <label className="check"><input type="checkbox" checked={streaming}
            onChange={e => { setStreaming(e.target.checked); if (e.target.checked) setFallback(false) }} /> Stream responses with cancel control</label>
          <p>Without cloud consent, Auto uses a configured local model or refuses the request. Paid calls consume a daily request slot.</p>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy}
              onClick={() => { setMessages([]); setCloudConsent(false) }}>New chat</button>
            <button type="button" disabled={busy || messages.length === 0} onClick={() => void saveCurrentChat()}>Save locally</button>
          </div>
          <div className="heading"><h2>Saved conversations</h2>
            <button className="secondary" type="button" onClick={() => void refreshChats()}>Refresh</button></div>
          <label>Import conversation JSON (local-only)
            <input type="file" accept=".json,application/json"
              disabled={busy} onChange={e => void importChatFile(e)} /></label>
          <label>Find in saved conversations
            <input value={chatQuery} maxLength={200} placeholder="Search local chat history…"
              onChange={e => setChatQuery(e.target.value)} /></label>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy || chatQuery.trim().length < 2}
              onClick={() => void searchChats()}>Search locally</button>
            {chatResults !== null && <button type="button" className="secondary"
              disabled={busy} onClick={() => { setChatResults(null); setChatQuery('') }}>Show all</button>}
          </div>
          {chatResults !== null && <small role="status">{chatResults.length} local matches</small>}
          {(chatResults ?? savedChats).map(chat => <div className="saved-chat" key={chat.id}>
            <button type="button" className="doc-link" onClick={() => void openChat(chat.id)}>
              {chat.title}<small>{chat.message_count} messages</small></button>
            <div className="saved-chat-actions">
              <button type="button" className="secondary" disabled={busy}
                aria-label={'Rename ' + chat.title}
                onClick={() => void renameChat(chat.id, chat.title)}>Rename</button>
              <button type="button" className="secondary" disabled={busy}
                aria-label={'Export ' + chat.title + ' as JSON'}
                onClick={() => void exportChat(chat.id, 'json')}>JSON</button>
              <button type="button" className="secondary" disabled={busy}
                aria-label={'Export ' + chat.title + ' as Markdown'}
                onClick={() => void exportChat(chat.id, 'md')}>MD</button>
              <button type="button" className="secondary" disabled={busy}
                aria-label={'Delete ' + chat.title}
                onClick={() => void deleteChat(chat.id)}>Delete</button>
            </div>
          </div>)}
          <div className="heading"><h2>Privacy and quotas</h2>
            <button className="secondary" type="button" disabled={busy}
              onClick={() => void refreshPrivacy()}>Review</button></div>
          {privacyInfo && <div role="status">
            <p>Authentication: {privacyInfo.auth_mode}. Cloud quota remaining:
              {' '}{privacyInfo.cloud_requests.remaining} of {privacyInfo.cloud_requests.limit} requests.</p>
            <p>Retention: {privacyInfo.conversation_retention_days === 0
              ? 'manual only' : privacyInfo.conversation_retention_days + ' days'}.
              Provider key cap verification: {privacyInfo.provider_key_cap_required ? 'required' : 'off'}.</p>
            <p>Storage: {privacyInfo.document_storage === 'local-sqlcipher-fts5'
              ? 'SQLCipher configured for live data' : 'plaintext local SQLite'}.
              Downloaded conversation exports are unencrypted. Provider credit-cap checks
              are not a dollar guarantee.</p>
            <button type="button" className="secondary"
              disabled={busy || privacyInfo.conversation_retention_days === 0}
              onClick={() => void purgeOldChats()}>Purge expired saved chats</button>
            <p>Cloud admission receipts retain only event metadata for
              {' '}{privacyInfo.consent_receipt_retention_days} days, not your prompts or billed cost.</p>
            <div className="actions">
              <button type="button" className="secondary" disabled={busy}
                onClick={() => void refreshConsentReceipts()}>Review cloud consent receipts</button>
              <button type="button" className="secondary danger" disabled={busy}
                onClick={() => void clearConsentReceipts()}>Clear receipts</button>
            </div>
            {receiptsLoaded && <div aria-live="polite">
              {consentReceipts.length === 0 ? <p>No recent cloud admission receipts.</p> :
                consentReceipts.map(item => <p key={item.id}>
                  {item.created_at} · {item.kind} · {item.approval}
                </p>)}
              <small>An admission does not prove a provider call completed or was billed.</small>
            </div>}
          </div>}
        </aside>
      </div>}

      {tab === 'Images' && <div className="split">
        <section className="canvas"><h2>Image studio</h2>
          <div className="image-stage">{image
            ? <img src={image} alt={'AI generated output from prompt: ' + imagePrompt} />
            : <div className="empty"><span className="symbol">◈</span><h2>Start with an idea</h2>
              <p>Generate an original image or edit a reference.</p></div>}</div>
          {image && <div className="actions"><a className="button" href={image} download={'goreecloud-ai.' + (
            imageMime === 'image/jpeg' ? 'jpg' : imageMime === 'image/webp' ? 'webp' : 'png'
          )}>Save image</a>
            {imageCost != null && <small>Reported request cost: {String(imageCost)} USD</small>}</div>}
        </section>
        <form className="controls" onSubmit={generateImage}><h2>Creative controls</h2>
          <div className="heading"><h3>Image models</h3>
            <button type="button" className="secondary" disabled={busy}
              onClick={() => void loadImageModels()}>Browse available</button></div>
          {imageModels.length > 0 && <label>Available image models
            <select aria-label="Choose available image model"
              value={imageModels.some(item => item.id === imageModel) ? imageModel : ''}
              onChange={e => { if (e.target.value) setImageModel(e.target.value) }}>
              <option value="">Choose a discovered model</option>
              {imageModels.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}
            </select></label>}
          <label>Image model ID<input value={imageModel} onChange={e => setImageModel(e.target.value)} /></label>
          {reference && imageModels.some(item => item.id === imageModel && !item.supports_reference) &&
            <p role="alert">Selected model does not advertise reference-image support.</p>}
          <label>Prompt<textarea rows={5} required value={imagePrompt} onChange={e => setImagePrompt(e.target.value)} /></label>
          <label>Optional reference<input type="file" accept="image/png,image/jpeg,image/webp" onChange={setReferenceFile} /></label>
          {reference && <button className="secondary" type="button" onClick={() => setReference(null)}>Clear reference</button>}
          <label className="check"><input type="checkbox" checked={paidApproved} onChange={e => setPaidApproved(e.target.checked)} />
            I approve this paid image-generation request</label>
          <button disabled={busy || !paidApproved || !imagePrompt.trim()}>Generate image</button>
          <p>Reference editing only works with compatible models. Images are not stored on the server.</p>
        </form>
      </div>}

      {tab === 'Documents' && <div className="split">
        <section className="canvas"><div className="heading"><h2>Document editor</h2>
          <button className="secondary" onClick={() => {
            setDocId(''); setDocTitle(''); setDocBody('')
            setDocumentRevisions([]); setPreviewRevision(null); setRecordRevision(false)
          }}>New</button></div>
          <form className="doc-editor" onSubmit={saveDoc}>
            <input aria-label="Document title" className="doc-title" placeholder="Untitled document"
              value={docTitle} onChange={e => setDocTitle(e.target.value)} required />
            <textarea aria-label="Document body" value={docBody} onChange={e => setDocBody(e.target.value)}
              placeholder="Write in Markdown…" rows={14} />
            {docId && <label className="check">
              <input type="checkbox" checked={recordRevision}
                onChange={e => setRecordRevision(e.target.checked)} />
              Save a private copy of the current saved version before overwriting it
            </label>}
            <div className="actions"><button disabled={busy || !docTitle.trim()}>Save</button>
              <button type="button" className="secondary" disabled={!docId || busy} onClick={() => void exportDoc('md')}>Export MD</button>
              <button type="button" className="secondary" disabled={!docId || busy} onClick={() => void exportDoc('docx')}>Export DOCX</button>
              <button type="button" className="secondary danger" disabled={!docId || busy}
                onClick={() => void deleteDoc()}>Delete document</button></div>
          </form>
        </section>
        <aside className="controls"><h2>Library</h2><button className="secondary" onClick={() => void refreshDocs()}>Refresh library</button>
          {docId && <section aria-label="Document history">
            <div className="heading"><h2>Earlier versions</h2>
              <button type="button" className="secondary" disabled={busy}
                onClick={() => void refreshDocumentRevisions()}>Load history</button></div>
            <p>History is opt-in per save, retained locally (up to 20 versions).
              Restores capture the displaced saved version automatically.</p>
            {documentRevisions.map(revision => <div className="revision-entry" key={revision.id}>
              <button type="button" className="doc-link" disabled={busy}
                onClick={() => void inspectRevision(revision.id)}>
                {revision.title}<small>{revision.created_at}</small></button>
              <button type="button" className="secondary" disabled={busy}
                onClick={() => void restoreRevision(revision.id)}>Restore</button>
            </div>)}
            {previewRevision && <div aria-label="Read-only revision preview">
              <strong>Preview: {previewRevision.title}</strong>
              <pre className="result">{previewRevision.body}</pre>
            </div>}
          </section>}
          <label>Import document<input type="file" accept=".pdf,.docx,.md,.txt" onChange={e => void importFile(e)} /></label>
          {docs.map(doc => <button type="button" key={doc.id} className="doc-link"
            onClick={() => void openDoc(doc.id)}>{doc.title}<small>{doc.updated_at.slice(0, 10)}</small></button>)}
          <h2>Private document search</h2>
          <label>Search or question<input value={searchText} onChange={e => setSearchText(e.target.value)}
            placeholder="Search saved documents…" /></label>
          <div className="actions">
            <button type="button" className="secondary" disabled={busy || !searchText.trim()}
              onClick={() => void findDocs()}>Find locally</button>
            <button type="button" disabled={busy || !searchText.trim()}
              onClick={() => void askDocuments()}>Ask documents</button>
          </div>
          <label className="check"><input type="checkbox" checked={cloudConsent}
            onChange={e => setCloudConsent(e.target.checked)} />
            Allow selected snippets to be sent to OpenRouter if chosen</label>
          {searchHits.map(hit => <button className="doc-link" key={hit.id}
            onClick={() => void openDoc(hit.id)}>{hit.title}<small>{hit.excerpt}</small></button>)}
          {researchAnswer && <section aria-label="Document answer">
            <h2>Answer · source-linked</h2><p className="research-answer">{researchAnswer}</p>
            {researchSources.map(source => <button key={source.id} className="doc-link"
              onClick={() => void openDoc(source.id)}>{source.title}</button>)}
          </section>}
          <p>Saved documents live in local SQLite, unencrypted in this preview. Retrieval uses local full-text search, not an embedding model.</p>
        </aside>
      </div>}

      {tab === 'Agents' && <div className="split">
        <section className="canvas"><h2>Plan safely</h2><p>Plans do not run automatically.</p>
          <form className="stack" onSubmit={planAgent}>
            <label>Describe the goal<textarea value={goal} rows={5} required onChange={e => setGoal(e.target.value)} /></label>
            <button disabled={busy || !goal.trim()}>Generate plan</button></form>
          {plan && <pre className="result">{plan}</pre>}
        </section>
        <aside className="controls"><h2>Read-only approved action</h2>
          <p>Select a saved document ID to let the agent read it after your explicit click.</p>
          <label>Document UUID<input value={docId} onChange={e => setDocId(e.target.value)} /></label>
          <button disabled={!docId || busy} onClick={() => void agentRead()}>Approve &amp; read</button>
          {toolResult && <pre className="result">{toolResult}</pre>}
        </aside>
      </div>}

      {tab === 'MCP' && <div className="split">
        <section className="canvas"><div className="heading"><h2>Connected tools</h2>
          <button className="secondary" onClick={() => void discoverTools()}>Discover</button></div>
          {tools.length ? tools.map(name => <button key={name} className="doc-link"
            onClick={() => setToolName(name)}>{name}</button>)
            : <div className="empty"><h2>Connections are opt-in</h2>
              <p>An operator configures the trusted MCP endpoint and tool allowlist on the server.</p></div>}
        </section>
        <form className="controls" onSubmit={callTool}><h2>Manual call</h2>
          <label>Tool name<input required value={toolName} onChange={e => setToolName(e.target.value)} /></label>
          <label>Arguments JSON<textarea rows={6} value={toolArguments} onChange={e => setToolArguments(e.target.value)} /></label>
          <label className="check"><input type="checkbox" checked={toolApproval}
            onChange={e => setToolApproval(e.target.checked)} /> Approve this specific external action</label>
          <button disabled={!toolApproval || !toolName || busy}>Call tool</button>
          {toolResult && <pre className="result">{toolResult}</pre>}
        </form>
      </div>}
    </main>
  </div>
}
