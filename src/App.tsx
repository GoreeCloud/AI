import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { AlertCircle, Bot, CheckCircle2, ChevronDown, Copy, FileText, FolderPlus, GitBranch, Globe2, Menu, MessageSquarePlus, PanelRight, Paperclip, Pencil, Plus, RefreshCw, Search, Send, ShieldCheck, Sparkles, Square, Trash2, X } from 'lucide-react'
import { MarkdownMessage } from './components/MarkdownMessage'
import { TextDialog } from './components/TextDialog'
import { OllamaClient, type ChatMessage, type OllamaModel } from './lib/ollama'
import { createConversation, getConversation, listConversations, removeConversation, saveConversation, type ConversationSummary } from './lib/conversations'
import { resolveModelRoles, roleForModel, type ModelRoleId } from './lib/modelRoles'
import { createWorkspace, listWorkspaces, saveWorkspace, type Workspace } from './lib/workspaces'
import { listFiles, uploadFile, type StoredFile } from './lib/files'

const welcome: ChatMessage = { role: 'assistant', content: 'Welcome to GoreeCloud AI. Start a private conversation with a local model.' }
const stored = (items: ChatMessage[]) => items.filter((message) => message !== welcome)
const fileTrustLabel: Record<StoredFile['status'], string> = {
  available: 'Verified',
  held: 'Held',
  blocked: 'Blocked',
  unverified: 'Unverified',
}

type DialogState =
  | { kind: 'rename'; id: string; value: string }
  | { kind: 'edit'; index: number; value: string }
  | { kind: 'workspace'; value: string }
  | null

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([welcome])
  const [history, setHistory] = useState<ConversationSummary[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [models, setModels] = useState<OllamaModel[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null)
  const [files, setFiles] = useState<StoredFile[]>([])
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [runtimeState, setRuntimeState] = useState<'checking' | 'ready' | 'offline'>('checking')
  const [dialog, setDialog] = useState<DialogState>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [retryMessages, setRetryMessages] = useState<ChatMessage[] | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const client = useMemo(() => new OllamaClient('/api/ollama'), [])
  const resolvedRoles = useMemo(() => resolveModelRoles(models), [models])
  const currentRole = useMemo(() => roleForModel(selectedModel, models), [selectedModel, models])
  const selectedWorkspace = workspaces.find((workspace) => workspace.id === selectedWorkspaceId)
  const workspaceFiles = files.filter((file) => selectedWorkspaceId ? file.workspaceId === selectedWorkspaceId : file.workspaceId === null)
  const verifiedWorkspaceFiles = workspaceFiles.filter((file) => file.status === 'available')
  const restrictedWorkspaceFiles = workspaceFiles.filter((file) => file.status !== 'available')

  async function refreshHistory() { try { setHistory(await listConversations()) } catch {} }
  async function refreshWorkspaces() { try { setWorkspaces(await listWorkspaces()) } catch {} }
  async function refreshFiles() { try { setFiles(await listFiles()) } catch {} }

  useEffect(() => {
    void refreshHistory()
    void refreshWorkspaces()
    void refreshFiles()
    let active = true
    client.listModels().then((available) => {
      if (!active) return
      setModels(available)
      const assistant = resolveModelRoles(available).find((role) => role.id === 'assistant' && role.model)
      setSelectedModel((current) => current || assistant?.model?.name || available[0]?.name || '')
      setRuntimeState('ready')
    }).catch(() => active && setRuntimeState('offline'))
    return () => { active = false }
  }, [client])

  async function persist(id: string, nextMessages: ChatMessage[], model = selectedModel, explicitTitle?: string, workspaceId = selectedWorkspaceId) {
    const firstUser = nextMessages.find((message) => message.role === 'user')?.content.trim()
    await saveConversation({ id, title: explicitTitle || firstUser?.slice(0, 72) || 'New conversation', model, workspaceId, messages: stored(nextMessages) })
    await refreshHistory()
  }

  async function ensureConversation(nextMessages: ChatMessage[]) {
    if (conversationId) return conversationId
    const created = await createConversation({ model: selectedModel, workspaceId: selectedWorkspaceId })
    setConversationId(created.id)
    await persist(created.id, nextMessages)
    return created.id
  }

  async function generate(requestMessages: ChatMessage[], id: string) {
    setGenerationError(null)
    setRetryMessages(null)
    setMessages([...requestMessages, { role: 'assistant', content: '' }])
    setIsGenerating(true)
    const controller = new AbortController()
    controllerRef.current = controller
    try {
      await client.streamChat({
        model: selectedModel,
        messages: stored(requestMessages),
        signal: controller.signal,
        onToken(token) {
          setMessages((current) => {
            const copy = [...current]
            const last = copy[copy.length - 1]
            if (last?.role === 'assistant') copy[copy.length - 1] = { ...last, content: `${last.content}${token}` }
            return copy
          })
        },
      })
      setRuntimeState('ready')
      setMessages((current) => { void persist(id, current); return current })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        setMessages((current) => { const next = current.at(-1)?.content ? current : current.slice(0, -1); void persist(id, next); return next })
      } else {
        setMessages(requestMessages)
        setRetryMessages(requestMessages)
        setGenerationError(error instanceof Error ? error.message : 'The local model request failed.')
        setRuntimeState('offline')
        await persist(id, requestMessages)
      }
    } finally {
      setIsGenerating(false)
      controllerRef.current = null
    }
  }

  async function submitPrompt(event: FormEvent) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || !selectedModel || isGenerating) return
    const requestMessages: ChatMessage[] = [...stored(messages), { role: 'user', content: text }]
    setPrompt('')
    const id = await ensureConversation(requestMessages)
    await generate(requestMessages, id)
  }

  function stopGeneration() { controllerRef.current?.abort() }
  function newConversation() { controllerRef.current?.abort(); setConversationId(null); setMessages([welcome]); setPrompt(''); setGenerationError(null); setRetryMessages(null); setSidebarOpen(false) }

  async function openConversation(id: string) {
    controllerRef.current?.abort()
    const conversation = await getConversation(id)
    setConversationId(id)
    setMessages(conversation.messages.length ? conversation.messages : [welcome])
    if (conversation.model) setSelectedModel(conversation.model)
    setSelectedWorkspaceId(conversation.workspaceId ?? null)
    setGenerationError(null)
    setRetryMessages(null)
    setSidebarOpen(false)
  }

  async function deleteConversation(id: string) { await removeConversation(id); if (id === conversationId) newConversation(); await refreshHistory() }
  async function changeModel(model: string) { setSelectedModel(model); if (conversationId) { const item = history.find((entry) => entry.id === conversationId); await persist(conversationId, messages, model, item?.title) } }

  async function changeWorkspace(workspaceId: string) {
    const nextId = workspaceId || null
    setSelectedWorkspaceId(nextId)
    const workspace = workspaces.find((item) => item.id === nextId)
    if (workspace) {
      const role = resolvedRoles.find((item) => item.id === workspace.defaultModelRole && item.model)
      if (role?.model?.name) setSelectedModel(role.model.name)
    }
    if (conversationId) {
      const item = history.find((entry) => entry.id === conversationId)
      await persist(conversationId, messages, workspace?.defaultModelRole ? (resolvedRoles.find((role) => role.id === workspace.defaultModelRole)?.model?.name || selectedModel) : selectedModel, item?.title, nextId)
    }
  }

  async function confirmDialog(value: string) {
    if (!dialog) return
    if (dialog.kind === 'workspace') {
      const roleId = (currentRole?.id || 'assistant') as ModelRoleId
      const workspace = await createWorkspace({ name: value.slice(0, 120), defaultModelRole: roleId })
      await refreshWorkspaces()
      setSelectedWorkspaceId(workspace.id)
      if (conversationId) {
        const item = history.find((entry) => entry.id === conversationId)
        await persist(conversationId, messages, selectedModel, item?.title, workspace.id)
      }
      setDialog(null)
      return
    }
    if (dialog.kind === 'rename') {
      const conversation = await getConversation(dialog.id)
      await saveConversation({ id: dialog.id, title: value.slice(0, 120), model: conversation.model, workspaceId: conversation.workspaceId, messages: conversation.messages })
      await refreshHistory()
      setDialog(null)
      return
    }
    const message = messages[dialog.index]
    if (message?.role !== 'user' || isGenerating) return
    const next = messages.slice(0, dialog.index + 1)
    next[dialog.index] = { role: 'user', content: value }
    setDialog(null)
    const id = await ensureConversation(next)
    await persist(id, next)
    await generate(next, id)
  }

  async function regenerate(index: number) {
    if (isGenerating || messages[index]?.role !== 'assistant') return
    const request = messages.slice(0, index).filter((message) => message.role !== 'assistant' || message.content)
    if (!request.some((message) => message.role === 'user')) return
    const id = await ensureConversation(request)
    await generate(request, id)
  }

  async function retryGeneration() {
    if (!retryMessages || isGenerating) return
    const id = await ensureConversation(retryMessages)
    await generate(retryMessages, id)
  }

  async function branchFrom(index: number) {
    const branchMessages = stored(messages.slice(0, index + 1))
    if (!branchMessages.length) return
    const created = await createConversation({
      model: selectedModel,
      workspaceId: selectedWorkspaceId,
      title: `Branch · ${branchMessages.find((message) => message.role === 'user')?.content.slice(0, 55) || 'Conversation'}`,
      parentConversationId: conversationId,
      parentMessageIndex: index,
    })
    await persist(created.id, branchMessages, selectedModel, created.title)
    setConversationId(created.id)
    setMessages(branchMessages)
    setGenerationError(null)
    setRetryMessages(null)
    setSidebarOpen(false)
  }

  async function attachFiles(fileList: FileList | null) {
    if (!fileList?.length) return
    setFileError(null)
    setIsUploading(true)
    try {
      const uploaded: StoredFile[] = []
      for (const file of Array.from(fileList)) uploaded.push(await uploadFile(file, selectedWorkspaceId))
      if (selectedWorkspace) {
        await saveWorkspace(selectedWorkspace.id, { fileIds: [...new Set([...selectedWorkspace.fileIds, ...uploaded.map((file) => file.id)])] })
        await refreshWorkspaces()
      }
      const restricted = uploaded.filter((file) => file.status !== 'available')
      if (restricted.length) {
        setFileError(`${restricted.length} attachment${restricted.length === 1 ? ' is' : 's are'} staged and unavailable to AI context until Wardveil verification succeeds.`)
      }
      await refreshFiles()
      setContextOpen(true)
    } catch (error) {
      setFileError(error instanceof Error ? error.message : 'Attachment upload failed.')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const currentSummary = history.find((item) => item.id === conversationId)
  const assignedModelNames = new Set(resolvedRoles.flatMap((role) => role.model ? [role.model.name] : []))

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'is-open' : ''}`} aria-label="Primary navigation">
      <div className="brand-row"><img className="brand-icon" src="/artwork/icon.svg" alt=""/><div><strong>GoreeCloud AI</strong><span>Local intelligence</span></div><button className="icon-button mobile-only" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={19}/></button></div>
      <button className="new-chat" onClick={newConversation}><MessageSquarePlus size={18}/>New chat</button>
      <nav className="nav-stack"><button className="nav-item active"><Sparkles size={18}/>Chat</button><button className="nav-item"><Search size={18}/>Search & research</button><button className="nav-item" onClick={() => setContextOpen(true)}><FileText size={18}/>Workspaces</button><button className="nav-item"><Globe2 size={18}/>Library</button></nav>
      <div className="sidebar-section"><span className="section-label">Recent</span>{history.length === 0 ? <span className="history-item">No saved conversations</span> : history.map((item) => <div key={item.id} className="history-row"><button className={`history-item ${item.id === conversationId ? 'active' : ''}`} onClick={() => void openConversation(item.id)}>{item.parentConversationId ? '↳ ' : ''}{item.title}</button><button className="icon-button history-action" onClick={() => setDialog({ kind: 'rename', id: item.id, value: item.title })} aria-label={`Rename ${item.title}`}><Pencil size={14}/></button><button className="icon-button history-action" onClick={() => void deleteConversation(item.id)} aria-label={`Delete ${item.title}`}><Trash2 size={14}/></button></div>)}</div>
      <div className="sidebar-footer"><div className={`runtime-pill ${runtimeState}`}>{runtimeState === 'ready' ? <CheckCircle2 size={15}/> : <ShieldCheck size={15}/>} {runtimeState === 'checking' ? 'Checking local runtime' : runtimeState === 'ready' ? 'Local runtime ready' : 'Runtime unavailable'}</div><span>Privacy Shield · Wardveil Security</span></div>
    </aside>

    <main className="main-column">
      <header className="topbar"><button className="icon-button desktop-hidden" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20}/></button><label className="model-picker"><Bot size={17}/><select value={selectedModel} onChange={(event) => void changeModel(event.target.value)} aria-label="Selected model"><option value="">Select model</option><optgroup label="GoreeCloud roles">{resolvedRoles.filter((role) => role.conversational && role.model).map((role) => <option key={role.id} value={role.model!.name}>{role.name} · {role.model!.name}</option>)}</optgroup>{models.some((model) => !assignedModelNames.has(model.name)) && <optgroup label="Installed models">{models.filter((model) => !assignedModelNames.has(model.name)).map((model) => <option key={model.name} value={model.name}>{model.name}</option>)}</optgroup>}</select><ChevronDown size={16}/></label><div className="topbar-actions"><button className="icon-button" onClick={newConversation} aria-label="New conversation"><Plus size={20}/></button><button className="icon-button" onClick={() => setContextOpen((value) => !value)} aria-label="Toggle context panel"><PanelRight size={20}/></button></div></header>

      <section className="conversation" aria-live="polite"><div className="conversation-inner">
        {messages.map((message, index) => <article className={`message ${message.role}`} key={`${message.role}-${index}`}><div className="message-avatar" aria-hidden="true">{message.role === 'assistant' ? <img src="/artwork/icon.svg" alt=""/> : <span>Y</span>}</div><div className="message-body"><div className="message-label">{message.role === 'assistant' ? 'GoreeCloud AI' : 'You'}</div><div className="message-content">{message.content ? (message.role === 'assistant' ? <MarkdownMessage content={message.content}/> : message.content) : (isGenerating && index === messages.length - 1 ? <span className="thinking">Thinking locally…</span> : null)}</div>{message.content && message !== welcome && <div className="message-actions"><button onClick={() => void navigator.clipboard.writeText(message.content)} aria-label="Copy message"><Copy size={14}/></button>{message.role === 'user' && <button onClick={() => setDialog({ kind: 'edit', index, value: message.content })} aria-label="Edit and resubmit"><Pencil size={14}/></button>}{message.role === 'assistant' && <button onClick={() => void regenerate(index)} aria-label="Regenerate response"><RefreshCw size={14}/></button>}<button onClick={() => void branchFrom(index)} aria-label="Branch conversation here"><GitBranch size={14}/></button></div>}</div></article>)}
        {generationError && <div className="generation-error"><AlertCircle size={18}/><div><strong>Generation interrupted</strong><span>{generationError}</span></div><button onClick={() => void retryGeneration()} disabled={!retryMessages || isGenerating}><RefreshCw size={14}/>Retry</button></div>}
      </div></section>

      <div className="composer-wrap"><form className="composer" onSubmit={submitPrompt}><textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} placeholder={runtimeState === 'offline' ? 'Retry the local runtime or continue when it reconnects…' : 'Message GoreeCloud AI'} rows={1}/><div className="composer-toolbar"><div className="composer-tools"><input ref={fileInputRef} className="visually-hidden" type="file" multiple onChange={(event) => void attachFiles(event.target.files)}/><button type="button" className="tool-button" onClick={() => fileInputRef.current?.click()} disabled={isUploading} aria-label="Attach file"><Paperclip size={18}/></button><button type="button" className="tool-chip"><Globe2 size={16}/>Research</button></div>{isGenerating ? <button type="button" className="send-button" onClick={stopGeneration} aria-label="Stop generation"><Square size={17} fill="currentColor"/></button> : <button type="submit" className="send-button" disabled={!prompt.trim() || !selectedModel} aria-label="Send message"><Send size={17}/></button>}</div></form><p className="composer-note">{isUploading ? 'Staging attachment for Wardveil verification…' : 'Local by default. External research is disclosed through Privacy Shield.'}</p></div>
    </main>

    <aside className={`context-panel ${contextOpen ? 'is-open' : ''}`} aria-label="Conversation context"><div className="context-heading"><div><strong>Context</strong><span>Conversation resources</span></div><button className="icon-button" onClick={() => setContextOpen(false)} aria-label="Close context panel"><X size={19}/></button></div>
      <div className="context-card"><span className="context-card-icon"><Bot size={19}/></span><div><strong>{currentRole?.name || 'Direct model'}</strong><p>{currentRole ? `${currentRole.purpose}. Runtime: ${selectedModel}.` : selectedModel ? `Using installed Ollama model ${selectedModel}.` : 'No model selected.'}</p></div></div>
      <div className="context-card"><span className="context-card-icon"><ShieldCheck size={19}/></span><div><strong>Private processing</strong><p>This conversation is configured for the local Ollama runtime.</p></div></div>
      <div className="context-card"><span className="context-card-icon"><GitBranch size={19}/></span><div><strong>Lineage</strong><p>{currentSummary?.parentConversationId ? `Branched from conversation ${currentSummary.parentConversationId.slice(0, 8)} at message ${Number(currentSummary.parentMessageIndex) + 1}.` : 'This is a root conversation.'}</p></div></div>
      <div className="context-card context-card-wide"><span className="context-card-icon"><FileText size={19}/></span><div><strong>Workspace</strong><p>Persistent instructions, files, knowledge, model role, tools, and research preferences.</p><select className="context-select" value={selectedWorkspaceId ?? ''} onChange={(event) => void changeWorkspace(event.target.value)}><option value="">No Workspace</option>{workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}</select><button className="context-action" onClick={() => setDialog({ kind: 'workspace', value: '' })}><FolderPlus size={15}/>New Workspace</button></div></div>
      <div className="context-card context-card-wide"><span className="context-card-icon"><Paperclip size={19}/></span><div><strong>{selectedWorkspace ? 'Workspace files' : 'Unassigned files'}</strong><p>{fileError || (workspaceFiles.length ? `${verifiedWorkspaceFiles.length} verified · ${restrictedWorkspaceFiles.length} restricted. Only Wardveil-clean attachments may become available to AI context.` : 'No files stored here yet.')}</p>{workspaceFiles.slice(0, 5).map((file) => <span className={`file-chip ${file.status}`} key={file.id}><span>{file.name}</span><em>{fileTrustLabel[file.status]}</em></span>)}</div></div>
    </aside>

    <TextDialog open={dialog?.kind === 'rename'} title="Rename conversation" label="Choose a concise name for this conversation." initialValue={dialog?.kind === 'rename' ? dialog.value : ''} onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'edit'} title="Edit message" label="Resubmitting will regenerate the conversation from this point." initialValue={dialog?.kind === 'edit' ? dialog.value : ''} multiline confirmLabel="Save & resubmit" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'workspace'} title="New Workspace" label="Name this persistent AI workspace." initialValue={dialog?.kind === 'workspace' ? dialog.value : ''} confirmLabel="Create Workspace" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    {sidebarOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/>} 
  </div>
}
