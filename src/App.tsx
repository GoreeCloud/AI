import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { AlertCircle, Bot, CheckCircle2, ChevronDown, ChevronUp, Clock, Download, FileText, FolderPlus, GitBranch, Globe2, Menu, MessageSquarePlus, PanelRight, Paperclip, Pencil, Plus, RefreshCw, Search, Send, ShieldCheck, Sparkles, Square, Trash2, X } from 'lucide-react'
import { ConfirmDialog } from './components/ConfirmDialog'
import { CopyMessageButton } from './components/CopyMessageButton'
import { CopyTranscriptButton } from './components/CopyTranscriptButton'
import { MarkdownMessage } from './components/MarkdownMessage'
import { TextDialog } from './components/TextDialog'
import { OllamaClient, type ChatMessage, type OllamaModel } from './lib/ollama'
import { createConversation, getConversation, listConversations, removeConversation, saveConversation, type ConversationSummary } from './lib/conversations'
import { resolveModelRoles, roleForModel, type ModelRoleId } from './lib/modelRoles'
import { createWorkspace, listWorkspaces, removeWorkspace, saveWorkspace, type Workspace } from './lib/workspaces'
import { listFiles, removeFile, uploadFile, type StoredFile } from './lib/files'
import { ConversationEpoch, buildMarkdownTranscript, exportFileName, historyMatches, shouldSubmitComposerKey } from './lib/conversationUx'
import { findLocalMessages, nextLocalMatchCursor, findKeyboardAction, shouldOpenConversationFindShortcut } from './lib/localMessageFind'
import { buildPortableTranscript, portableFileName, type PortableFormat } from './lib/portableTranscript'
import { summarizeLocalConversation } from './lib/localConversationOutline'

const welcome: ChatMessage = { role: 'assistant', content: 'Welcome to GoreeCloud AI. Start a private conversation with a local model.' }
const stored = (items: ChatMessage[]) => items.filter((message) => message !== welcome)
const formatSavedTime = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
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
  | { kind: 'workspace-rename'; id: string; value: string }
  | { kind: 'workspace-instructions'; id: string; value: string }
  | { kind: 'workspace-delete'; id: string; name: string }
  | { kind: 'file-delete'; id: string; name: string }
  | { kind: 'conversation-delete'; id: string; name: string }
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
  const [historyQuery, setHistoryQuery] = useState('')
  const [conversationFindOpen, setConversationFindOpen] = useState(false)
  const [conversationFindQuery, setConversationFindQuery] = useState('')
  const [conversationFindCursor, setConversationFindCursor] = useState(-1)
  const [exportFormat, setExportFormat] = useState<'md' | PortableFormat>('md')
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [followOutput, setFollowOutput] = useState(true)
  const [runtimeState, setRuntimeState] = useState<'checking' | 'ready' | 'no-models' | 'offline'>('checking')
  const [dialog, setDialog] = useState<DialogState>(null)
  const [generationError, setGenerationError] = useState<string | null>(null)
  const [composerError, setComposerError] = useState<string | null>(null)
  const [isPreparing, setIsPreparing] = useState(false)
  const [isChangingSelection, setIsChangingSelection] = useState(false)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [workspaceError, setWorkspaceError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [retryMessages, setRetryMessages] = useState<ChatMessage[] | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const generationEpochRef = useRef(new ConversationEpoch())
  const conversationLoadRef = useRef(0)
  const preparingRef = useRef(false)
  const selectionChangeRef = useRef(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const composerRef = useRef<HTMLTextAreaElement | null>(null)
  const historySearchRef = useRef<HTMLInputElement | null>(null)
  const conversationRef = useRef<HTMLElement | null>(null)
  const conversationFindInputRef = useRef<HTMLInputElement | null>(null)
  const messageArticleRefs = useRef<Array<HTMLElement | null>>([])
  const conversationEndRef = useRef<HTMLDivElement | null>(null)
  const client = useMemo(() => new OllamaClient('/api/ollama'), [])
  const resolvedRoles = useMemo(() => resolveModelRoles(models), [models])
  const currentRole = useMemo(() => roleForModel(selectedModel, models), [selectedModel, models])
  const selectedWorkspace = workspaces.find((workspace) => workspace.id === selectedWorkspaceId)
  const workspaceFiles = files.filter((file) => selectedWorkspaceId ? file.workspaceId === selectedWorkspaceId : file.workspaceId === null)
  const verifiedWorkspaceFiles = workspaceFiles.filter((file) => file.status === 'available')
  const restrictedWorkspaceFiles = workspaceFiles.filter((file) => file.status !== 'available')
  const lastMessageContentLength = messages.at(-1)?.content.length ?? 0
  const conversationFindMatches = useMemo(() => findLocalMessages(messages, conversationFindQuery), [messages, conversationFindQuery])
  const conversationFindMatchSet = useMemo(() => new Set(conversationFindMatches), [conversationFindMatches])
  const activeFindCursor = conversationFindMatches.length && conversationFindCursor >= 0 ? Math.min(conversationFindCursor, conversationFindMatches.length - 1) : -1
  const activeFindMessage = activeFindCursor >= 0 ? conversationFindMatches[activeFindCursor] : -1
  const localOutline = useMemo(() => summarizeLocalConversation(messages, welcome), [messages])
  const visibleHistory = useMemo(() => {
    if (!historyQuery.trim()) return history
    return history.filter((item) => {
      const workspaceName = workspaces.find((workspace) => workspace.id === item.workspaceId)?.name ?? ''
      return historyMatches(historyQuery, [item.title, item.model, workspaceName])
    })
  }, [history, historyQuery, workspaces])

  async function refreshHistory() { try { setHistory(await listConversations()); setHistoryError(null) } catch (error) { setHistoryError(error instanceof Error ? error.message : 'Conversation history could not be refreshed.') } }
  async function refreshWorkspaces() {
    try { setWorkspaces(await listWorkspaces()); setWorkspaceError(null) }
    catch (error) { setWorkspaceError(error instanceof Error ? error.message : 'Workspaces could not be refreshed.') }
  }
  async function refreshFiles() {
    try { setFiles(await listFiles()); setFileError(null) }
    catch (error) { setFileError(error instanceof Error ? error.message : 'Files could not be refreshed.') }
  }
  async function refreshModels() {
    setRuntimeState('checking')
    try {
      const available = await client.listModels()
      setModels(available)
      const assistant = resolveModelRoles(available).find((role) => role.id === 'assistant' && role.model)
      setSelectedModel((current) => available.some((model) => model.name === current) ? current : assistant?.model?.name || available[0]?.name || '')
      setRuntimeState(available.length ? 'ready' : 'no-models')
    } catch {
      setRuntimeState('offline')
    }
  }

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
      setRuntimeState(available.length ? 'ready' : 'no-models')
    }).catch(() => active && setRuntimeState('offline'))
    return () => { active = false }
  }, [client])

  useEffect(() => {
    if (followOutput) conversationEndRef.current?.scrollIntoView({ block: 'end', behavior: 'auto' })
  }, [messages.length, lastMessageContentLength, generationError, followOutput])

  useEffect(() => {
    if (conversationFindOpen) conversationFindInputRef.current?.focus()
  }, [conversationFindOpen])

  useEffect(() => {
    const node = composerRef.current
    if (!node) return
    node.style.height = '0px'
    node.style.height = `${Math.min(node.scrollHeight, 180)}px`
  }, [prompt])

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if (!dialog && shouldOpenConversationFindShortcut(event)) {
        event.preventDefault()
        setConversationFindOpen(true)
        return
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase() === 'k') {
        event.preventDefault()
        focusHistorySearch()
        return
      }
      // IME-owned Escape cancels character composition; never cancel generation.
      if (event.key !== 'Escape' || dialog || event.isComposing || event.keyCode === 229) return
      if (conversationFindOpen) {
        event.preventDefault()
        resetConversationFind()
        return
      }
      if (isGenerating) {
        event.preventDefault()
        stopGeneration()
        return
      }
      if (sidebarOpen || contextOpen) {
        event.preventDefault()
        setSidebarOpen(false)
        setContextOpen(false)
      }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [contextOpen, conversationFindOpen, dialog, isGenerating, sidebarOpen])

  async function persist(id: string, nextMessages: ChatMessage[], model = selectedModel, explicitTitle?: string, workspaceId = selectedWorkspaceId) {
    const firstUser = nextMessages.find((message) => message.role === 'user')?.content.trim()
    await saveConversation({ id, title: explicitTitle || firstUser?.slice(0, 72) || 'New conversation', model, workspaceId, messages: stored(nextMessages) })
    await refreshHistory()
  }

  async function ensureConversation(nextMessages: ChatMessage[]) {
    if (conversationId) return conversationId
    const epoch = generationEpochRef.current.value()
    const created = await createConversation({ model: selectedModel, workspaceId: selectedWorkspaceId })
    if (!generationEpochRef.current.isCurrent(epoch)) throw new Error('Conversation selection changed during creation.')
    setConversationId(created.id)
    await persist(created.id, nextMessages)
    return created.id
  }

  async function generate(requestMessages: ChatMessage[], id: string) {
    const run = generationEpochRef.current.begin()
    setGenerationError(null)
    setComposerError(null)
    setRetryMessages(null)
    setFollowOutput(true)
    setMessages([...requestMessages, { role: 'assistant', content: '' }])
    setIsGenerating(true)
    const controller = new AbortController()
    controllerRef.current = controller
    let assistantContent = ''
    try {
      await client.streamChat({
        model: selectedModel,
        messages: stored(requestMessages),
        workspaceId: selectedWorkspaceId,
        signal: controller.signal,
        onToken(token) {
          if (!generationEpochRef.current.isCurrent(run)) return
          assistantContent += token
          setMessages((current) => {
            if (!generationEpochRef.current.isCurrent(run)) return current
            const copy = [...current]
            const last = copy[copy.length - 1]
            if (last?.role === 'assistant') copy[copy.length - 1] = { ...last, content: `${last.content}${token}` }
            return copy
          })
        },
      })
      if (!generationEpochRef.current.isCurrent(run)) return
      const completedMessages: ChatMessage[] = [...requestMessages, { role: 'assistant', content: assistantContent }]
      setRuntimeState('ready')
      setMessages(completedMessages)
      try { await persist(id, completedMessages) }
      catch { setGenerationError('Response completed, but the conversation could not be saved. The response remains visible in this session.') }
    } catch (error) {
      if (!generationEpochRef.current.isCurrent(run)) return
      if (error instanceof DOMException && error.name === 'AbortError') {
        const interruptedMessages: ChatMessage[] = assistantContent
          ? [...requestMessages, { role: 'assistant', content: assistantContent }]
          : requestMessages
        setMessages(interruptedMessages)
        try { await persist(id, interruptedMessages) }
        catch { setGenerationError('Generation stopped, but the conversation could not be saved. The partial response remains visible in this session.') }
      } else {
        const failureMessage = error instanceof Error ? error.message : 'The local model request failed.'
        setMessages(requestMessages)
        setRetryMessages(requestMessages)
        setGenerationError(failureMessage)
        // Request failure does not establish that model discovery is offline.
        try { await persist(id, requestMessages) }
        catch { setGenerationError(`${failureMessage} The conversation state also could not be saved.`) }
      }
    } finally {
      if (generationEpochRef.current.isCurrent(run)) {
        setIsGenerating(false)
        controllerRef.current = null
      }
    }
  }

  async function submitPrompt(event: FormEvent) {
    event.preventDefault()
    const text = prompt.trim()
    if (!text || !selectedModel || isGenerating || preparingRef.current || selectionChangeRef.current) return
    const epoch = generationEpochRef.current.value()
    preparingRef.current = true
    setIsPreparing(true)
    setComposerError(null)
    const requestMessages: ChatMessage[] = [...stored(messages), { role: 'user', content: text }]
    try {
      const id = await ensureConversation(requestMessages)
      if (!generationEpochRef.current.isCurrent(epoch)) return
      setPrompt('')
      await generate(requestMessages, id)
    } catch (error) {
      if (generationEpochRef.current.isCurrent(epoch)) {
        setComposerError(error instanceof Error ? error.message : 'Conversation could not be started. Your draft was preserved.')
      }
    } finally {
      preparingRef.current = false
      setIsPreparing(false)
    }
  }

  function stopGeneration() { controllerRef.current?.abort() }
  function scrollToLatest() {
    setFollowOutput(true)
    conversationEndRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }
  function handleConversationScroll() {
    const node = conversationRef.current
    if (!node) return
    setFollowOutput(node.scrollHeight - node.scrollTop - node.clientHeight < 96)
  }
  function focusHistorySearch() {
    setSidebarOpen(true)
    window.setTimeout(() => historySearchRef.current?.focus(), 0)
  }
  function jumpToOutlineMessage(index: number) {
    const article = messageArticleRefs.current[index]
    if (!article) return
    setFollowOutput(false)
    article.scrollIntoView({ block: 'center', behavior: 'smooth' })
    article.focus({ preventScroll: true })
  }

  function jumpToConversationMatch(direction: -1 | 1) {
    if (!conversationFindMatches.length) return
    const next = nextLocalMatchCursor(conversationFindMatches.length, activeFindCursor, direction)
    setConversationFindCursor(next)
    setFollowOutput(false)
    messageArticleRefs.current[conversationFindMatches[next]]?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }
  function resetConversationFind() {
    setConversationFindQuery('')
    setConversationFindCursor(-1)
    setConversationFindOpen(false)
  }
  function createTranscriptSnapshot() {
    const exportMessages = stored(messages)
    if (!exportMessages.length) return null
    const firstUser = exportMessages.find((message) => message.role === 'user')?.content.trim()
    const title = currentSummary?.title || firstUser?.slice(0, 72) || 'GoreeCloud AI conversation'
    const transcript = {
      title,
      model: selectedModel,
      workspace: selectedWorkspace?.name ?? null,
      exportedAt: new Date().toISOString(),
      messages: exportMessages,
    }
    const content = exportFormat === 'md' ? buildMarkdownTranscript(transcript) : buildPortableTranscript(transcript, exportFormat)
    return { title, content }
  }

  function exportConversation() {
    const snapshot = createTranscriptSnapshot()
    if (!snapshot) return
    const mime = exportFormat === 'json' ? 'application/json;charset=utf-8'
      : exportFormat === 'txt' ? 'text/plain;charset=utf-8' : 'text/markdown;charset=utf-8'
    const blob = new Blob([snapshot.content], { type: mime })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = exportFormat === 'md' ? exportFileName(snapshot.title) : portableFileName(snapshot.title, exportFormat)
    anchor.style.display = 'none'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(url)
  }
  function newConversation() { generationEpochRef.current.invalidate(); conversationLoadRef.current += 1; controllerRef.current?.abort(); controllerRef.current = null; setIsGenerating(false); setConversationId(null); setMessages([welcome]); setPrompt(''); setGenerationError(null); setComposerError(null); setRetryMessages(null); setFollowOutput(true); setSidebarOpen(false); resetConversationFind() }

  async function openConversation(id: string) {
    generationEpochRef.current.invalidate()
    const load = ++conversationLoadRef.current
    controllerRef.current?.abort()
    controllerRef.current = null
    setIsGenerating(false)
    setHistoryError(null)
    setComposerError(null)
    try {
      const conversation = await getConversation(id)
      if (load !== conversationLoadRef.current) return
      setConversationId(id)
      setMessages(conversation.messages.length ? conversation.messages : [welcome])
      if (conversation.model) setSelectedModel(conversation.model)
      setSelectedWorkspaceId(conversation.workspaceId ?? null)
      setGenerationError(null)
      setRetryMessages(null)
      setFollowOutput(true)
      setSidebarOpen(false)
      resetConversationFind()
    } catch (error) {
      if (load === conversationLoadRef.current) setHistoryError(error instanceof Error ? error.message : 'Conversation could not be opened.')
    }
  }
  async function changeModel(model: string) {
    if (isGenerating || preparingRef.current || selectionChangeRef.current || model === selectedModel) return
    const epoch = generationEpochRef.current.value()
    selectionChangeRef.current = true
    setIsChangingSelection(true)
    setComposerError(null)
    try {
      if (conversationId) {
        const item = history.find((entry) => entry.id === conversationId)
        await persist(conversationId, messages, model, item?.title)
      }
      if (generationEpochRef.current.isCurrent(epoch)) setSelectedModel(model)
    } catch (error) {
      if (generationEpochRef.current.isCurrent(epoch))
        setComposerError(error instanceof Error ? `Model selection was not saved: ${error.message}` : 'Model selection was not saved.')
    } finally {
      selectionChangeRef.current = false
      setIsChangingSelection(false)
    }
  }

  async function changeWorkspace(workspaceId: string) {
    if (isGenerating || preparingRef.current || selectionChangeRef.current) return
    const nextId = workspaceId || null
    const workspace = workspaces.find((item) => item.id === nextId)
    if ((nextId && !workspace) || nextId === selectedWorkspaceId) return
    const targetRole = workspace && resolvedRoles.find((item) => item.id === workspace.defaultModelRole && item.model)
    const nextModel = targetRole?.model?.name || selectedModel
    const epoch = generationEpochRef.current.value()
    selectionChangeRef.current = true
    setIsChangingSelection(true)
    setWorkspaceError(null)
    try {
      if (conversationId) {
        const item = history.find((entry) => entry.id === conversationId)
        await persist(conversationId, messages, nextModel, item?.title, nextId)
      }
      if (generationEpochRef.current.isCurrent(epoch)) {
        setSelectedWorkspaceId(nextId)
        setSelectedModel(nextModel)
      }
    } catch (error) {
      if (generationEpochRef.current.isCurrent(epoch))
        setWorkspaceError(error instanceof Error ? `Workspace selection was not saved: ${error.message}` : 'Workspace selection was not saved.')
    } finally {
      selectionChangeRef.current = false
      setIsChangingSelection(false)
    }
  }

  async function changeWorkspaceRole(roleId: ModelRoleId) {
    if (!selectedWorkspace || isGenerating || preparingRef.current || selectionChangeRef.current) return
    const epoch = generationEpochRef.current.value()
    selectionChangeRef.current = true
    setIsChangingSelection(true)
    setWorkspaceError(null)
    try {
      const updated = await saveWorkspace(selectedWorkspace.id, { defaultModelRole: roleId })
      if (!generationEpochRef.current.isCurrent(epoch)) return
      setWorkspaces((current) => current.map((workspace) => workspace.id === updated.id ? updated : workspace))
      const role = resolvedRoles.find((item) => item.id === roleId && item.model)
      const nextModel = role?.model?.name
      if (!nextModel || nextModel === selectedModel) return
      if (conversationId) {
        const item = history.find((entry) => entry.id === conversationId)
        try { await persist(conversationId, messages, nextModel, item?.title) }
        catch (error) {
          if (generationEpochRef.current.isCurrent(epoch))
            setWorkspaceError(error instanceof Error ? `Workspace role saved, but conversation model could not be saved: ${error.message}` : 'Workspace role saved, but conversation model could not be saved.')
          return
        }
      }
      if (generationEpochRef.current.isCurrent(epoch)) setSelectedModel(nextModel)
    } catch (error) {
      if (generationEpochRef.current.isCurrent(epoch))
        setWorkspaceError(error instanceof Error ? error.message : 'Workspace default model role could not be saved.')
    } finally {
      selectionChangeRef.current = false
      setIsChangingSelection(false)
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
    if (dialog.kind === 'workspace-rename') {
      await saveWorkspace(dialog.id, { name: value.slice(0, 120) })
      await refreshWorkspaces()
      setDialog(null)
      return
    }
    if (dialog.kind === 'workspace-instructions') {
      await saveWorkspace(dialog.id, { instructions: value.slice(0, 20_000) })
      await refreshWorkspaces()
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
    if (dialog.kind !== 'edit') return
    const message = messages[dialog.index]
    if (message?.role !== 'user' || isGenerating) return
    const next = messages.slice(0, dialog.index + 1)
    next[dialog.index] = { role: 'user', content: value }
    setDialog(null)
    const id = await ensureConversation(next)
    await persist(id, next)
    await generate(next, id)
  }

  async function confirmDeletion() {
    if (!dialog) return
    if (dialog.kind === 'conversation-delete') {
      setHistoryError(null)
      try {
        await removeConversation(dialog.id)
        if (dialog.id === conversationId) newConversation()
        await refreshHistory()
        setDialog(null)
      } catch (error) {
        setHistoryError(error instanceof Error ? error.message : 'Conversation deletion failed.')
        setDialog(null)
      }
      return
    }
    if (dialog.kind === 'file-delete') {
      setFileError(null)
      try {
        await removeFile(dialog.id)
        await Promise.all([refreshFiles(), refreshWorkspaces()])
        setDialog(null)
      } catch (error) {
        setFileError(error instanceof Error ? error.message : 'File deletion failed.')
        setDialog(null)
      }
      return
    }
    if (dialog.kind === 'workspace-delete') {
      setWorkspaceError(null)
      try {
        await removeWorkspace(dialog.id)
        if (selectedWorkspaceId === dialog.id) setSelectedWorkspaceId(null)
        await Promise.all([refreshWorkspaces(), refreshHistory()])
        setDialog(null)
      } catch (error) {
        setWorkspaceError(error instanceof Error ? error.message : 'Workspace deletion failed.')
        setDialog(null)
      }
    }
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
    if (isGenerating || isPreparing) return
    const epoch = generationEpochRef.current.value()
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
    if (!generationEpochRef.current.isCurrent(epoch)) return
    generationEpochRef.current.invalidate()
    conversationLoadRef.current += 1
    setConversationId(created.id)
    setMessages(branchMessages)
    setGenerationError(null)
    setRetryMessages(null)
    setSidebarOpen(false)
    resetConversationFind()
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
      await refreshFiles()
      if (restricted.length) {
        setFileError(`${restricted.length} attachment${restricted.length === 1 ? ' is' : 's are'} staged and unavailable to AI context until Wardveil verification succeeds.`)
      }
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
      <nav className="nav-stack"><button className="nav-item active" aria-current="page"><Sparkles size={18}/>Chat</button><button className="nav-item" onClick={focusHistorySearch} title="Search conversations (Ctrl/⌘ K)"><Search size={18}/>Search conversations</button><button className="nav-item" onClick={() => setContextOpen(true)}><FileText size={18}/>Workspaces</button><button className="nav-item" disabled title="The governed knowledge Library is not enabled in this Development build"><Globe2 size={18}/>Library</button></nav>
      <div className="history-search"><Search size={14}/><input ref={historySearchRef} value={historyQuery} maxLength={120} onChange={(event) => setHistoryQuery(event.target.value)} placeholder="Search conversations" aria-label="Search saved conversations by title, model or Workspace"/>{historyQuery && <button type="button" onClick={() => setHistoryQuery('')} aria-label="Clear conversation search"><X size={14}/></button>}</div>
      <div className="sidebar-section"><span className="section-label">{historyQuery ? 'Matches' : 'Recent'}</span>{historyError && <div className="history-recovery"><span className="history-empty history-error">{historyError}</span><button type="button" onClick={() => void refreshHistory()}><RefreshCw size={13}/>Retry</button></div>}{history.length === 0 ? <span className="history-empty">No saved conversations</span> : visibleHistory.length === 0 ? <span className="history-empty">No matching conversations</span> : visibleHistory.map((item) => <div key={item.id} className="history-row"><button className={`history-item ${item.id === conversationId ? 'active' : ''}`} onClick={() => void openConversation(item.id)}>{item.parentConversationId ? '↳ ' : ''}{item.title}</button><button className="icon-button history-action" onClick={() => setDialog({ kind: 'rename', id: item.id, value: item.title })} aria-label={`Rename ${item.title}`}><Pencil size={14}/></button><button className="icon-button history-action" onClick={() => setDialog({ kind: 'conversation-delete', id: item.id, name: item.title })} aria-label={`Delete ${item.title}`}><Trash2 size={14}/></button></div>)}</div>
      <div className="sidebar-footer"><div className={`runtime-pill ${runtimeState}`}>{runtimeState === 'ready' ? <CheckCircle2 size={15}/> : runtimeState === 'no-models' ? <Bot size={15}/> : <ShieldCheck size={15}/>} {runtimeState === 'checking' ? 'Checking local runtime' : runtimeState === 'ready' ? 'Local runtime ready' : runtimeState === 'no-models' ? 'No local models' : 'Runtime unavailable'}</div><span>Privacy Shield · Wardveil Security</span></div>
    </aside>

    <main className="main-column">
      <header className="topbar"><button className="icon-button desktop-hidden" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20}/></button><label className="model-picker"><Bot size={17}/><select value={selectedModel} onChange={(event) => void changeModel(event.target.value)} aria-label="Selected model" disabled={runtimeState === 'no-models' || isGenerating || isPreparing || isChangingSelection}><option value="">{runtimeState === 'no-models' ? 'No local models installed' : 'Select model'}</option><optgroup label="GoreeCloud roles">{resolvedRoles.filter((role) => role.conversational && role.model).map((role) => <option key={role.id} value={role.model!.name}>{role.name} · {role.model!.name}</option>)}</optgroup>{models.some((model) => !assignedModelNames.has(model.name)) && <optgroup label="Installed models">{models.filter((model) => !assignedModelNames.has(model.name)).map((model) => <option key={model.name} value={model.name}>{model.name}</option>)}</optgroup>}</select><ChevronDown size={16}/></label><div className="topbar-actions"><button className="icon-button" onClick={() => { if (conversationFindOpen) resetConversationFind(); else setConversationFindOpen(true) }} aria-label="Find in current conversation" aria-keyshortcuts="Control+Shift+F Meta+Shift+F" title="Find in current conversation (Ctrl/⌘ Shift F)"><Search size={19}/></button><button className="icon-button" onClick={() => void refreshModels()} aria-label="Refresh local models" title="Refresh local models"><RefreshCw size={19}/></button><label className="transcript-format"><span className="visually-hidden">Transcript export format</span><select value={exportFormat} onChange={(event) => setExportFormat(event.target.value as 'md' | PortableFormat)} disabled={!stored(messages).length} aria-label="Transcript export format"><option value="md">Markdown</option><option value="txt">Text</option><option value="json">JSON</option></select></label><button className="icon-button" onClick={exportConversation} disabled={!stored(messages).length} aria-label={`Export conversation as ${exportFormat === 'md' ? 'Markdown' : exportFormat === 'txt' ? 'plain text' : 'JSON'}`} title="Download selected transcript format"><Download size={19}/></button><CopyTranscriptButton key={conversationId ?? 'unsaved'} format={exportFormat} getText={() => createTranscriptSnapshot()?.content ?? ''} disabled={!stored(messages).length}/><button className="icon-button" onClick={newConversation} aria-label="New conversation"><Plus size={20}/></button><button className="icon-button" onClick={() => setContextOpen((value) => !value)} aria-label="Toggle context panel"><PanelRight size={20}/></button></div></header>
      {conversationFindOpen && <div className="conversation-find" role="search" aria-label="Find text within currently loaded conversation"><Search size={17}/><input ref={conversationFindInputRef} value={conversationFindQuery} maxLength={120} onChange={(event) => { setConversationFindQuery(event.target.value); setConversationFindCursor(-1) }} onKeyDown={(event) => { const action = findKeyboardAction(event.nativeEvent); if (action) { event.preventDefault(); event.stopPropagation(); if (action === 'close') resetConversationFind(); else jumpToConversationMatch(action === 'previous' ? -1 : 1) } }} placeholder="Find messages in this conversation" aria-label="Find messages in this conversation"/><span className="conversation-find-count" role="status" aria-live="polite">{conversationFindQuery.trim() ? (conversationFindMatches.length ? `${activeFindCursor < 0 ? 0 : activeFindCursor + 1} of ${conversationFindMatches.length} messages` : 'No matching messages') : 'Search visible messages'}</span><button type="button" className="icon-button" onClick={() => jumpToConversationMatch(-1)} disabled={!conversationFindMatches.length} aria-label="Previous matching message"><ChevronUp size={18}/></button><button type="button" className="icon-button" onClick={() => jumpToConversationMatch(1)} disabled={!conversationFindMatches.length} aria-label="Next matching message"><ChevronDown size={18}/></button><button type="button" className="icon-button" onClick={resetConversationFind} aria-label="Close conversation search"><X size={18}/></button></div>}

      <span className="visually-hidden" role="status" aria-live="polite">{isGenerating ? 'GoreeCloud AI is generating a response.' : generationError ? (retryMessages ? 'Response generation interrupted.' : 'Conversation save warning.') : ''}</span>
      <section ref={conversationRef} className="conversation" aria-busy={isGenerating} onScroll={handleConversationScroll}><div className="conversation-inner">
        {messages.map((message, index) => <article tabIndex={-1} ref={(node) => { messageArticleRefs.current[index] = node }} className={`message ${message.role}${conversationFindMatchSet.has(index) ? ' is-find-match' : ''}${activeFindMessage === index ? ' is-find-current' : ''}`} key={`${message.role}-${index}`}><div className="message-avatar" aria-hidden="true">{message.role === 'assistant' ? <img src="/artwork/icon.svg" alt=""/> : <span>Y</span>}</div><div className="message-body"><div className="message-label">{message.role === 'assistant' ? 'GoreeCloud AI' : 'You'}</div><div className="message-content">{message.content ? (message.role === 'assistant' ? <MarkdownMessage content={message.content}/> : message.content) : (isGenerating && index === messages.length - 1 ? <span className="thinking">Thinking locally…</span> : null)}</div>{message.content && message !== welcome && <div className="message-actions"><CopyMessageButton content={message.content}/>{message.role === 'user' && <button onClick={() => setDialog({ kind: 'edit', index, value: message.content })} aria-label="Edit and resubmit"><Pencil size={14}/></button>}{message.role === 'assistant' && <button onClick={() => void regenerate(index)} aria-label="Regenerate response"><RefreshCw size={14}/></button>}<button onClick={() => void branchFrom(index)} disabled={isGenerating || isPreparing} aria-label="Branch conversation here"><GitBranch size={14}/></button></div>}</div></article>)}
        {generationError && <div className="generation-error"><AlertCircle size={18}/><div><strong>{retryMessages ? 'Generation interrupted' : 'Conversation save warning'}</strong><span>{generationError}</span></div>{retryMessages && <button onClick={() => void retryGeneration()} disabled={isGenerating}><RefreshCw size={14}/>Retry</button>}</div>}
        <div ref={conversationEndRef} aria-hidden="true"/>
      </div>{!followOutput && <button type="button" className="jump-latest" onClick={scrollToLatest} aria-label="Jump to latest message" title="Jump to latest message"><ChevronDown size={18}/></button>}</section>

      <div className="composer-wrap"><form className="composer" onSubmit={submitPrompt}><textarea ref={composerRef} value={prompt} onChange={(event) => setPrompt(event.target.value)} onKeyDown={(event) => { if (shouldSubmitComposerKey(event.nativeEvent)) { event.preventDefault(); if (!isChangingSelection) event.currentTarget.form?.requestSubmit() } }} placeholder={runtimeState === 'offline' ? 'Retry the local runtime or continue when it reconnects…' : runtimeState === 'no-models' ? 'Install a local model to start chatting…' : 'Message GoreeCloud AI'} rows={1}/><div className="composer-toolbar"><div className="composer-tools"><input ref={fileInputRef} className="visually-hidden" type="file" multiple onChange={(event) => void attachFiles(event.target.files)}/><button type="button" className="tool-button" onClick={() => fileInputRef.current?.click()} disabled={isUploading} aria-label="Attach file"><Paperclip size={18}/></button><button type="button" className="tool-chip" disabled title="External research is not connected in this Development build"><Globe2 size={16}/>Research</button></div>{isGenerating ? <button type="button" className="send-button" onClick={stopGeneration} aria-label="Stop generation"><Square size={17} fill="currentColor"/></button> : <button type="submit" className="send-button" disabled={!prompt.trim() || !selectedModel || isPreparing || isChangingSelection} aria-label={isPreparing ? 'Saving conversation before generation' : 'Send message'}><Send size={17}/></button>}</div></form>{composerError && <p className="composer-error" role="alert">{composerError}</p>}<p className="composer-note">{isUploading ? 'Staging attachment for Wardveil verification…' : runtimeState === 'no-models' ? 'No local Ollama models were discovered. Install an approved model, then refresh the model list.' : 'Local by default. External research is disclosed through Privacy Shield.'}</p></div>
    </main>

    <aside className={`context-panel ${contextOpen ? 'is-open' : ''}`} aria-label="Conversation context"><div className="context-heading"><div><strong>Context</strong><span>Conversation resources</span></div><button className="icon-button" onClick={() => setContextOpen(false)} aria-label="Close context panel"><X size={19}/></button></div>
      <div className="context-card"><span className="context-card-icon"><Bot size={19}/></span><div><strong>{currentRole?.name || 'Direct model'}</strong><p>{currentRole ? `${currentRole.purpose}. Runtime: ${selectedModel}.` : selectedModel ? `Using installed Ollama model ${selectedModel}.` : 'No model selected.'}</p></div></div>
      <div className="context-card"><span className="context-card-icon"><ShieldCheck size={19}/></span><div><strong>Private processing</strong><p>This conversation is configured for the local Ollama runtime.</p></div></div>
      <div className="context-card"><span className="context-card-icon"><GitBranch size={19}/></span><div><strong>Lineage</strong><p>{currentSummary?.parentConversationId ? `Branched from conversation ${currentSummary.parentConversationId.slice(0, 8)} at message ${Number(currentSummary.parentMessageIndex) + 1}.` : 'This is a root conversation.'}</p></div></div>
      <div className="context-card context-card-wide conversation-outline"><span className="context-card-icon"><MessageSquarePlus size={19}/></span><div className="outline-content"><strong>Conversation outline</strong><p>{localOutline.userTurns} user turn{localOutline.userTurns === 1 ? '' : 's'} · {localOutline.assistantTurns} AI response{localOutline.assistantTurns === 1 ? '' : 's'}</p>{localOutline.prompts.length ? <nav aria-label="Jump to a user prompt"><ol className="outline-list">{localOutline.prompts.map((item) => <li key={item.messageIndex}><button type="button" onClick={() => jumpToOutlineMessage(item.messageIndex)} aria-label={`Jump to your message ${item.turnNumber}: ${item.preview}`}><span className="outline-number">{item.turnNumber}</span><span className="outline-preview">{item.preview}</span></button></li>)}</ol>{localOutline.hiddenPrompts > 0 && <p className="outline-note">Showing the latest {localOutline.prompts.length} of {localOutline.userTurns} prompts.</p>}</nav> : <p>No user prompts yet.</p>}</div></div>
      <div className="context-card"><span className="context-card-icon"><Clock size={19}/></span><div><strong>Conversation state</strong><p>{currentSummary ? `${currentSummary.messageCount} saved message${currentSummary.messageCount === 1 ? '' : 's'} · Updated ${formatSavedTime(currentSummary.updatedAt)} · Created ${formatSavedTime(currentSummary.createdAt)}` : stored(messages).length ? 'Conversation save metadata is refreshing.' : 'This new conversation will be saved after the first message.'}</p></div></div>
      <div className="context-card context-card-wide"><span className="context-card-icon"><FileText size={19}/></span><div><strong>Workspace</strong><p>{workspaceError || (selectedWorkspace ? selectedWorkspace.instructions.trim() ? 'Workspace instructions are applied as private system context to each local model request.' : 'This Workspace has no custom instructions yet.' : 'Persistent instructions, files, knowledge, model role, tools, and research preferences.')}</p>{workspaceError && <button type="button" className="context-retry" onClick={() => void refreshWorkspaces()}><RefreshCw size={13}/>Retry Workspaces</button>}<select className="context-select" value={selectedWorkspaceId ?? ''} disabled={isGenerating || isPreparing || isChangingSelection} onChange={(event) => void changeWorkspace(event.target.value)}><option value="">No Workspace</option>{workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}</select>{selectedWorkspace && <label className="context-field"><span>Default model role</span><select className="context-select" value={selectedWorkspace.defaultModelRole} disabled={isGenerating || isPreparing || isChangingSelection} onChange={(event) => void changeWorkspaceRole(event.target.value as ModelRoleId)}>{resolvedRoles.filter((role) => role.conversational).map((role) => <option key={role.id} value={role.id}>{role.name}{role.model ? ` · ${role.model.name}` : ' · no installed match'}</option>)}</select></label>}<div className="context-actions"><button className="context-action" onClick={() => setDialog({ kind: 'workspace', value: '' })}><FolderPlus size={15}/>New Workspace</button>{selectedWorkspace && <button className="context-action" onClick={() => setDialog({ kind: 'workspace-rename', id: selectedWorkspace.id, value: selectedWorkspace.name })}><Pencil size={15}/>Rename</button>}{selectedWorkspace && <button className="context-action" onClick={() => setDialog({ kind: 'workspace-instructions', id: selectedWorkspace.id, value: selectedWorkspace.instructions })}><Pencil size={15}/>{selectedWorkspace.instructions.trim() ? 'Edit instructions' : 'Add instructions'}</button>}{selectedWorkspace && <button className="context-action context-action-icon danger-action" disabled={workspaceFiles.length > 0} onClick={() => setDialog({ kind: 'workspace-delete', id: selectedWorkspace.id, name: selectedWorkspace.name })} aria-label={`Delete Workspace ${selectedWorkspace.name}`} title={workspaceFiles.length > 0 ? 'Remove Workspace files before deleting this Workspace' : 'Delete Workspace'}><Trash2 size={15}/></button>}</div></div></div>
      <div className="context-card context-card-wide"><span className="context-card-icon"><Paperclip size={19}/></span><div><strong>{selectedWorkspace ? 'Workspace files' : 'Unassigned files'}</strong><p>{fileError || (workspaceFiles.length ? `${verifiedWorkspaceFiles.length} verified · ${restrictedWorkspaceFiles.length} restricted. Only Wardveil-clean attachments may become available to AI context.` : 'No files stored here yet.')}</p>{fileError && <button type="button" className="context-retry" onClick={() => void refreshFiles()}><RefreshCw size={13}/>Retry files</button>}{workspaceFiles.length > 0 && <div className="file-list">{workspaceFiles.map((file) => <div className={`file-chip ${file.status}`} key={file.id}><span>{file.name}</span><span className="file-chip-actions"><em>{fileTrustLabel[file.status]}</em><button type="button" className="file-delete-button" onClick={() => setDialog({ kind: 'file-delete', id: file.id, name: file.name })} aria-label={`Delete ${file.name}`} title={`Delete ${file.name}`}><Trash2 size={13}/></button></span></div>)}</div>}</div></div>
    </aside>

    <TextDialog open={dialog?.kind === 'rename'} title="Rename conversation" label="Choose a concise name for this conversation." initialValue={dialog?.kind === 'rename' ? dialog.value : ''} onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'edit'} title="Edit message" label="Resubmitting will regenerate the conversation from this point." initialValue={dialog?.kind === 'edit' ? dialog.value : ''} multiline confirmLabel="Save & resubmit" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'workspace'} title="New Workspace" label="Name this persistent AI workspace." initialValue={dialog?.kind === 'workspace' ? dialog.value : ''} confirmLabel="Create Workspace" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'workspace-rename'} title="Rename Workspace" label="Choose a concise name for this Workspace." initialValue={dialog?.kind === 'workspace-rename' ? dialog.value : ''} confirmLabel="Save name" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <TextDialog open={dialog?.kind === 'workspace-instructions'} title="Workspace instructions" label="These private instructions are applied as system context to local model requests in this Workspace. They do not grant authorization or enable blocked tools." initialValue={dialog?.kind === 'workspace-instructions' ? dialog.value : ''} multiline confirmLabel="Save instructions" onCancel={() => setDialog(null)} onConfirm={confirmDialog}/>
    <ConfirmDialog open={dialog?.kind === 'conversation-delete'} title="Delete conversation?" description={dialog?.kind === 'conversation-delete' ? `Delete ${dialog.name}. This removes the saved conversation from GoreeCloud AI local storage.` : ''} confirmLabel="Delete conversation" onCancel={() => setDialog(null)} onConfirm={confirmDeletion}/>
    <ConfirmDialog open={dialog?.kind === 'workspace-delete'} title="Delete Workspace?" description={dialog?.kind === 'workspace-delete' ? `Delete ${dialog.name}. Saved conversations will be detached from this Workspace. Workspaces with file dependencies cannot be deleted.` : ''} confirmLabel="Delete Workspace" onCancel={() => setDialog(null)} onConfirm={confirmDeletion}/>
    <ConfirmDialog open={dialog?.kind === 'file-delete'} title="Delete file?" description={dialog?.kind === 'file-delete' ? `Delete ${dialog.name} from GoreeCloud AI local storage. This also removes its derived text extraction and Workspace file reference.` : ''} confirmLabel="Delete file" onCancel={() => setDialog(null)} onConfirm={confirmDeletion}/>
    {sidebarOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setSidebarOpen(false)}/>} 
  </div>
}
