import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'

type Tab = 'Chat' | 'Images' | 'Documents' | 'Agents' | 'MCP'
type Message = { role: 'user' | 'assistant'; content: string }
type SavedDoc = { id: string; title: string; body?: string; updated_at: string }

export default function App() {
  const [tab, setTab] = useState<Tab>('Chat')
  const [endpoint, setEndpoint] = useState('http://127.0.0.1:8000')
  const [token, setToken] = useState('')
  const [provider, setProvider] = useState('auto')
  const [model, setModel] = useState('openrouter/auto')
  const [fallback, setFallback] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [prompt, setPrompt] = useState('')
  const [imagePrompt, setImagePrompt] = useState('')
  const [imageModel, setImageModel] = useState('bytedance-seed/seedream-4.5')
  const [reference, setReference] = useState<string | null>(null)
  const [paidApproved, setPaidApproved] = useState(false)
  const [image, setImage] = useState('')
  const [imageCost, setImageCost] = useState<number | null>(null)
  const [docs, setDocs] = useState<SavedDoc[]>([])
  const [docId, setDocId] = useState('')
  const [docTitle, setDocTitle] = useState('')
  const [docBody, setDocBody] = useState('')
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

  async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
    if (!token.trim()) throw Error('Set an owner token first.')
    const result = await fetch(endpoint.replace(/\/+$/, '') + path, {
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
    return await result.json() as T
  }

  async function action(task: () => Promise<void>) {
    if (busy) return
    setBusy(true); setAlert(''); setNotice('')
    try { await task() }
    catch (e) { setAlert(e instanceof Error ? e.message : 'Unexpected failure') }
    finally { setBusy(false) }
  }

  function send(e: FormEvent) {
    e.preventDefault()
    if (!prompt.trim()) return
    const next: Message[] = [...messages, { role: 'user', content: prompt.trim() }]
    setMessages(next); setPrompt('')
    void action(async () => {
      const reply = await api<{ content: string; provider: string; model: string }>(
        '/api/v1/chat', 'POST',
        { messages: next, provider, model, allow_local_fallback: fallback })
      setMessages([...next, { role: 'assistant', content: reply.content }])
      setNotice('Response via ' + reply.provider + ' · ' + reply.model)
    })
  }

  function generateImage(e: FormEvent) {
    e.preventDefault()
    void action(async () => {
      const reply = await api<{ image: string; cost: number | null }>(
        '/api/v1/images', 'POST',
        { prompt: imagePrompt, model: imageModel, reference_data_url: reference,
          approve_paid_generation: paidApproved })
      setImage(reply.image); setImageCost(reply.cost)
      setPaidApproved(false)
      setNotice('Generated output received. Save locally to retain it.')
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

  async function refreshDocs() {
    await action(async () => setDocs(await api<SavedDoc[]>('/api/v1/documents')))
  }

  async function openDoc(id: string) {
    await action(async () => {
      const doc = await api<SavedDoc>('/api/v1/documents/' + id)
      setDocId(doc.id); setDocTitle(doc.title); setDocBody(doc.body || '')
    })
  }

  function saveDoc(e: FormEvent) {
    e.preventDefault()
    void action(async () => {
      const saved = await api<SavedDoc>('/api/v1/documents' + (docId ? '/' + docId : ''),
        docId ? 'PUT' : 'POST', { title: docTitle, body: docBody })
      setDocId(saved.id); setDocs(await api<SavedDoc[]>('/api/v1/documents'))
      setNotice('Document saved in the configured local database.')
    })
  }

  async function importFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    await action(async () => {
      const form = new FormData(); form.append('file', file)
      const reply = await fetch(endpoint.replace(/\/+$/, '') + '/api/v1/documents/extract', {
        method: 'POST', headers: { Authorization: 'Bearer ' + token }, body: form
      })
      if (!reply.ok) throw Error('Document import failed (' + reply.status + ')')
      const extracted = await reply.json() as { name: string; text: string; truncated: boolean }
      setDocId(''); setDocTitle(extracted.name); setDocBody(extracted.text)
      setNotice(extracted.truncated ? 'Imported preview truncated at 250,000 characters.' : 'Loaded into editor. Save to retain.')
    })
  }

  async function exportDoc(format: 'md' | 'docx') {
    await action(async () => {
      const reply = await fetch(endpoint.replace(/\/+$/, '') +
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
      const response = await api<{ plan: string }>('/api/v1/agents/plan', 'POST', { goal, provider })
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
              <p>{entry.content}</p></article>)}
          </div>
          <form className="composer" onSubmit={send}>
            <label className="sr-only" htmlFor="chat-prompt">Chat prompt</label>
            <textarea id="chat-prompt" value={prompt} rows={3} placeholder="Ask anything…" onChange={e => setPrompt(e.target.value)} />
            <div className="actions"><small>Requests may incur OpenRouter charges.</small>
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
          <label className="check"><input type="checkbox" checked={fallback}
            onChange={e => setFallback(e.target.checked)} /> Allow local fallback on transient OpenRouter errors</label>
          <p>Local fallback is never enabled without your choice.</p>
          <button type="button" className="secondary" onClick={() => setMessages([])}>New conversation</button>
        </aside>
      </div>}

      {tab === 'Images' && <div className="split">
        <section className="canvas"><h2>Image studio</h2>
          <div className="image-stage">{image
            ? <img src={image} alt={'AI generated output from prompt: ' + imagePrompt} />
            : <div className="empty"><span className="symbol">◈</span><h2>Start with an idea</h2>
              <p>Generate an original image or edit a reference.</p></div>}</div>
          {image && <div className="actions"><a className="button" href={image} download="goreecloud-ai.png">Save image</a>
            {imageCost != null && <small>Reported request cost: {String(imageCost)} USD</small>}</div>}
        </section>
        <form className="controls" onSubmit={generateImage}><h2>Creative controls</h2>
          <label>Image model<input value={imageModel} onChange={e => setImageModel(e.target.value)} /></label>
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
          <button className="secondary" onClick={() => { setDocId(''); setDocTitle(''); setDocBody('') }}>New</button></div>
          <form className="doc-editor" onSubmit={saveDoc}>
            <input aria-label="Document title" className="doc-title" placeholder="Untitled document"
              value={docTitle} onChange={e => setDocTitle(e.target.value)} required />
            <textarea aria-label="Document body" value={docBody} onChange={e => setDocBody(e.target.value)}
              placeholder="Write in Markdown…" rows={14} />
            <div className="actions"><button disabled={busy || !docTitle.trim()}>Save</button>
              <button type="button" className="secondary" disabled={!docId || busy} onClick={() => void exportDoc('md')}>Export MD</button>
              <button type="button" className="secondary" disabled={!docId || busy} onClick={() => void exportDoc('docx')}>Export DOCX</button></div>
          </form>
        </section>
        <aside className="controls"><h2>Library</h2><button className="secondary" onClick={() => void refreshDocs()}>Refresh library</button>
          <label>Import document<input type="file" accept=".pdf,.docx,.md,.txt" onChange={e => void importFile(e)} /></label>
          {docs.map(doc => <button type="button" key={doc.id} className="doc-link"
            onClick={() => void openDoc(doc.id)}>{doc.title}<small>{doc.updated_at.slice(0, 10)}</small></button>)}
          <p>Saved documents live in local SQLite, unencrypted in this preview.</p>
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
