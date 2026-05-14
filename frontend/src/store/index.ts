import { create } from "zustand"
import type {
  Project,
  PaperFile,
  TranslationResult,
  ThemeMode,
  ReaderSettings,
  ApiStats,
  GlossaryTerm,
  FileType,
} from "@/types"
import { generateId } from "@/lib/utils"
import { api, type DocumentContent } from "@/lib/api"

interface AppState {
  theme: ThemeMode
  setTheme: (theme: ThemeMode) => void

  projects: Project[]
  activeProjectId: string | null
  setActiveProject: (id: string | null) => void
  addProject: (name: string, description?: string) => Promise<void>
  updateProject: (id: string, data: Partial<Project>) => void
  deleteProject: (id: string) => Promise<void>
  loadProjects: () => Promise<void>

  activeFileId: string | null
  setActiveFile: (id: string | null) => Promise<void>

  documentContent: DocumentContent | null
  documentLoading: boolean
  documentError: string | null

  translationResult: TranslationResult | null
  setTranslationResult: (result: TranslationResult | null) => void
  recoverTranslation: (projectId: string, docId: string) => Promise<void>
  startTranslation: (docId: string) => Promise<void>

  readerSettings: ReaderSettings
  updateReaderSettings: (settings: Partial<ReaderSettings>) => void

  mobileTab: "original" | "translation"
  setMobileTab: (tab: "original" | "translation") => void

  mobileTocOpen: boolean
  setMobileTocOpen: (open: boolean) => void

  apiStats: ApiStats
  updateApiStats: (stats: ApiStats) => void
  refreshApiStats: () => Promise<void>

  glossary: GlossaryTerm[]
  addGlossaryTerm: (term: GlossaryTerm) => void
  removeGlossaryTerm: (id: string) => void

  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  settingsPanelOpen: boolean
  setSettingsPanelOpen: (open: boolean) => void

  uploadDialogOpen: boolean
  setUploadDialogOpen: (open: boolean) => void

  glossaryDialogOpen: boolean
  setGlossaryDialogOpen: (open: boolean) => void

  batchDialogOpen: boolean
  setBatchDialogOpen: (open: boolean) => void

  searchDialogOpen: boolean
  setSearchDialogOpen: (open: boolean) => void

  translatingFileId: string | null
  setTranslatingFileId: (id: string | null) => void

  addFileToProject: (projectId: string, file: PaperFile) => Promise<void>
  deleteFile: (projectId: string, fileId: string) => Promise<void>
  renameFile: (projectId: string, fileId: string, newName: string) => Promise<void>

  searchResults: Array<{
    project_id: string; project_name: string; doc_id: string
    doc_name: string; doc_type: string; match_position: number; snippet: string
  }>
  searchQuery: string
  searchLoading: boolean
  performSearch: (q: string) => Promise<void>
  clearSearch: () => void

  orphanData: {
    orphan_uploads: Array<{ name: string; path: string; size: number; mtime: number }>
    in_use_uploads: Array<{ name: string; path: string; size: number; mtime: number }>
    orphan_images: Array<{ name: string; path: string; size: number; mtime: number }>
    in_use_images: Array<{ name: string; path: string; size: number; mtime: number }>
    cache_files: Array<{ name: string; path: string; size: number; mtime: number }>
    total_orphans: number
    total_size: number
  } | null
  orphanLoading: boolean
  cleanupDialogOpen: boolean
  setCleanupDialogOpen: (open: boolean) => void
  loadOrphanData: () => Promise<void>
  deleteSelectedOrphans: (paths: string[]) => Promise<void>
  executeCleanup: () => Promise<void>

  tokenBreakdown: Array<{
    project_id: string; project_name: string; document_count: number
    translation_count: number; tokens_used: number; cost?: number
  }> | null
  totalTokenUsage: number
  totalTokenCost: number
  tokenLoading: boolean
  tokenDialogOpen: boolean
  setTokenDialogOpen: (open: boolean) => void
  loadTokenStats: () => Promise<void>

  tokenHistory: {
    records: Array<{
      timestamp: string; project_id: string; doc_id: string
      doc_name: string; tokens_used: number; paragraph_count: number
      prompt_tokens?: number; completion_tokens?: number; cached_tokens?: number
    }>
    daily_summary: Array<{ date: string; tokens: number; prompt_tokens: number; completion_tokens: number; cached_tokens: number; count: number }>
    total_records: number
    total_tokens: number
    total_prompt_tokens: number
    total_completion_tokens: number
    total_cached_tokens: number
  } | null
  tokenHistoryDays: number
  tokenHistoryLoading: boolean
  loadTokenHistory: (days?: number) => Promise<void>
}

const defaultReaderSettings: ReaderSettings = {
  fontSize: 16,
  lineHeight: 1.75,
  fontFamily: "sans",
  showLineNumbers: false,
  syncScroll: true,
}

export const useAppStore = create<AppState>((set, get) => ({
  theme: "system",
  setTheme: (theme) => set({ theme }),

  projects: [],
  activeProjectId: null,
  setActiveProject: (id) =>
    set({ activeProjectId: id, activeFileId: null, translationResult: null, documentContent: null }),

  addProject: async (name, description) => {
    console.log(`[STORE] Creating project: ${name}`)
    try {
      const res = await api.projects.create({ name, description } as Partial<Project>)
      const project = { ...res.data, files: [] as PaperFile[] } as Project
      console.log(`[STORE] Project created:`, project)
      set((state) => ({ projects: [...state.projects, project] }))
    } catch (err) {
      console.error(`[STORE] Failed to create project:`, err)
      const fallback: Project = {
        id: generateId(),
        name,
        description,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        sourceLanguage: "en",
        targetLanguage: "zh-CN",
        outputPath: "",
        status: "idle",
        files: [],
      }
      set((state) => ({ projects: [...state.projects, fallback] }))
    }
  },

  updateProject: (id, data) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === id ? { ...p, ...data, updatedAt: new Date().toISOString() } : p
      ),
    })),

  deleteProject: async (id) => {
    console.log(`[STORE] Deleting project: ${id}`)
    try {
      await api.projects.delete(id)
    } catch (err) {
      console.error(`[STORE] Failed to delete project from backend:`, err)
    }
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== id),
      activeProjectId: state.activeProjectId === id ? null : state.activeProjectId,
    }))
  },

  loadProjects: async () => {
    console.log(`[STORE] Loading projects from backend...`)
    try {
      const res = await api.projects.list()
      const rawProjects: any[] = res.data || []
      console.log(`[STORE] Loaded ${rawProjects.length} raw projects`)

      // 并行获取每个项目的文档列表
      const projectsWithFiles = await Promise.all(
        rawProjects.map(async (p: any) => {
          try {
            const docsRes = await api.files.list(p.id)
            return {
              ...p,
              files: (docsRes.data || []).map((d: any) => ({
                id: d.id,
                name: d.original_name || d.filename || "unknown",
                type: d.doc_type || "pdf",
                size: d.size || 0,
                uploadedAt: d.created_at || "",
                status: d.status || "uploaded",
                path: d.file_path || "",
              })) as PaperFile[],
            }
          } catch {
            return { ...p, files: [] as PaperFile[] }
          }
        })
      )

      console.log(`[STORE] Projects with files:`, projectsWithFiles)
      set({ projects: projectsWithFiles as Project[] })
      if (projectsWithFiles.length > 0 && !get().activeProjectId) {
        set({ activeProjectId: projectsWithFiles[0].id })
      }

      const savedTranslatingId = localStorage.getItem("translating_file_id")
      const savedTime = localStorage.getItem("translating_file_time")
      if (savedTranslatingId && savedTime) {
        const elapsed = Date.now() - parseInt(savedTime)
        if (elapsed < 3600000) {
          const foundFile = projectsWithFiles.reduce<PaperFile | null>((acc, p: any) => {
            if (acc) return acc
            return (p.files || []).find((f: any) => f.id === savedTranslatingId) || null
          }, null)
          if (foundFile && foundFile.status !== "completed") {
            set({ translatingFileId: savedTranslatingId })
          } else {
            localStorage.removeItem("translating_file_id")
            localStorage.removeItem("translating_file_time")
          }
        } else {
          localStorage.removeItem("translating_file_id")
          localStorage.removeItem("translating_file_time")
        }
      }
    } catch (err) {
      console.error(`[STORE] Failed to load projects:`, err)
    }
  },

  activeFileId: null,
  setActiveFile: async (id) => {
    console.log(`[STORE] Selecting file: ${id}`)
    set({ activeFileId: id, documentLoading: true, documentError: null, translationResult: null, documentContent: null })

    const state = get()
    const projectId = state.activeProjectId
    if (!projectId || !id) {
      set({ documentLoading: false })
      return
    }

    try {
      const res = await api.files.getContent(projectId, id)
      const content = res.data
      console.log(`[STORE] File content loaded:`, {
        id: content.id,
        doc_type: content.doc_type,
        original_length: content.original_text?.length || 0,
        translated_length: content.translated_text?.length || 0,
      })

      const hasTranslation = content.translated_text && content.translated_text.length > 0
      const isRecovering = get().translatingFileId === id

      set({
        documentContent: content,
        documentLoading: false,
        translationResult: {
          id: `trans-${id}`,
          fileId: id,
          originalContent: content.original_text || "",
          translatedContent: content.translated_text || "",
          progress: hasTranslation && !isRecovering ? 100 : 0,
          status: isRecovering ? "translating" : (hasTranslation ? "completed" : "pending"),
          tokenUsage: { inputCacheHit: 0, inputCacheMiss: 0, output: 0, total: 0, cost: 0 },
          cached: hasTranslation,
          createdAt: new Date().toISOString(),
        },
      })

      if (isRecovering) {
        get().recoverTranslation(projectId, id)
      }
    } catch (err) {
      console.error(`[STORE] Failed to load file content:`, err)
      set({
        documentLoading: false,
        documentError: `无法加载文档内容: ${err instanceof Error ? err.message : "未知错误"}`,
      })
    }
  },

  documentContent: null,
  documentLoading: false,
  documentError: null,

  translationResult: null,
  setTranslationResult: (result) => set({ translationResult: result }),

  recoverTranslation: async (projectId, docId) => {
    const state = get()
    if (state.translatingFileId !== docId) return

    console.log(`[STORE] Recovering translation state: project=${projectId}, doc=${docId}`)
    try {
      const statusRes = await api.translation.status(projectId, docId)
      const job = statusRes.data
      if (!job) return

      if (job.status === "translating") {
        const currentResult = get().translationResult
        const hasContent = currentResult?.translatedContent && currentResult.translatedContent.length > 100
        set((s) => ({
          translationResult: s.translationResult ? {
            ...s.translationResult,
            progress: hasContent ? Math.max(s.translationResult?.progress || 0, job.progress || 0) : (job.progress || 0),
            status: "translating",
          } : {
            id: `trans-${docId}`,
            fileId: docId,
            originalContent: "",
            translatedContent: "",
            progress: job.progress || 0,
            status: "translating",
            tokenUsage: { inputCacheHit: 0, inputCacheMiss: 0, output: 0, total: 0, cost: 0 },
            cached: false,
            createdAt: new Date().toISOString(),
          },
        }))

        const pollInterval = setInterval(async () => {
          const current = get()
          if (current.translatingFileId !== docId) {
            clearInterval(pollInterval)
            return
          }
          try {
            const sr = await api.translation.status(projectId, docId)
            const j = sr.data
            if (!j) return

            if (j.status === "completed" && j.result) {
              clearInterval(pollInterval)
              get().setTranslatingFileId(null)
              get().refreshApiStats()
              set((s) => ({
                translationResult: s.translationResult ? {
                  ...s.translationResult,
                  translatedContent: j.result.text || "",
                  progress: 100,
                  status: "completed",
                  tokenUsage: {
                    inputCacheHit: 0,
                    inputCacheMiss: 0,
                    output: j.result.tokens || 0,
                    total: j.result.tokens || 0,
                    cost: 0,
                  },
                } : null,
              }))
              console.log("[STORE] Translation recovered via polling")
            } else if (j.status === "failed") {
              clearInterval(pollInterval)
              get().setTranslatingFileId(null)
              set((s) => ({
                translationResult: s.translationResult ? {
                  ...s.translationResult,
                  status: "error",
                  progress: 0,
                } : null,
              }))
            } else if (j.status === "translating") {
              set((s) => ({
                translationResult: s.translationResult ? {
                  ...s.translationResult,
                  progress: j.progress || 0,
                  status: "translating",
                } : null,
              }))
            }
          } catch (e) {
            console.error("[STORE] recovery poll error:", e)
          }
        }, 2000)
      } else if (job.status === "completed" && job.result) {
        get().setTranslatingFileId(null)
        get().refreshApiStats()
        set((s) => ({
          translationResult: s.translationResult ? {
            ...s.translationResult,
            translatedContent: job.result.text || "",
            progress: 100,
            status: "completed",
            tokenUsage: {
              inputCacheHit: 0,
              inputCacheMiss: 0,
              output: job.result.tokens || 0,
              total: job.result.tokens || 0,
              cost: 0,
            },
          } : null,
        }))
        console.log("[STORE] Translation already completed, state restored")
      }
    } catch (err) {
      console.warn(`[STORE] Translation recovery failed:`, err)
    }
  },

  startTranslation: async (docId) => {
    const state = get()
    const projectId = state.activeProjectId
    if (!projectId) {
      console.error(`[STORE] No active project to translate`)
      return
    }

    if (state.translatingFileId) {
      console.warn(`[STORE] Force restarting translation: was=${state.translatingFileId}, new=${docId}`)
      get().setTranslatingFileId(null)
      set((s) => ({
        translationResult: s.translationResult ? {
          ...s.translationResult,
          status: "error",
          progress: 0,
        } : null,
      }))
    }

    console.log(`[STORE] Starting translation: project=${projectId}, doc=${docId}`)
    get().setTranslatingFileId(docId)

    const docContent = get().documentContent
    const originalText = docContent?.original_text || ""

    const chunkMap = new Map<number, string>()
    let ws: WebSocket | null = null
    let pollInterval: ReturnType<typeof setInterval> | null = null
    let done = false
    let lastProgressTime = Date.now()
    let usePolling = false

    const imgTagRegex = /<img[^>]*\/?>/gi
    const originalImgs: { tag: string; src: string }[] = []
    let imgMatch: RegExpExecArray | null
    while ((imgMatch = imgTagRegex.exec(originalText)) !== null) {
      const srcMatch = imgMatch[0].match(/src="([^"]+)"/i)
      if (srcMatch) {
        originalImgs.push({ tag: imgMatch[0], src: srcMatch[1] })
      }
    }

    set((s) => ({
      translationResult: {
        id: `trans-${docId}`,
        fileId: docId,
        originalContent: originalText,
        translatedContent: "",
        progress: 0,
        status: "translating",
        tokenUsage: { inputCacheHit: 0, inputCacheMiss: 0, output: 0, total: 0, cost: 0 },
        cached: false,
        createdAt: new Date().toISOString(),
      },
    }))

    const buildContent = (): string => {
      const parts: string[] = []
      const sortedKeys = Array.from(chunkMap.keys()).sort((a, b) => a - b)
      for (const k of sortedKeys) {
        parts.push(chunkMap.get(k)!)
      }
      if (originalImgs.length > 0) {
        const currentText = parts.join("\n\n")
        const missingImgs = originalImgs.filter((img) => !currentText.includes(img.src))
        if (missingImgs.length > 0) {
          parts.push(missingImgs.map((img) => img.tag).join("\n\n"))
        }
      }
      return parts.join("\n\n")
    }

    const finishWith = (finalText: string, tokens: number, status: "completed" | "error") => {
      done = true
      get().setTranslatingFileId(null)
      if (pollInterval) clearInterval(pollInterval)
      if (ws) {
        try { ws.close() } catch {}
        ws = null
      }
      get().refreshApiStats()
      set((s) => ({
        translationResult: s.translationResult ? {
          ...s.translationResult,
          translatedContent: finalText,
          progress: status === "completed" ? 100 : 0,
          status,
          tokenUsage: {
            inputCacheHit: 0,
            inputCacheMiss: 0,
            output: tokens || 0,
            total: tokens || 0,
            cost: 0,
          },
        } : null,
      }))
    }

    try {
      const res = await api.translation.start(projectId, docId)
      console.log(`[STORE] Translation started: ${res.data.status}`)

      function startPolling() {
        if (done) return
        usePolling = true
        console.log("[STORE] Switched to polling mode")
        pollInterval = setInterval(async () => {
          if (done) { clearInterval(pollInterval!); return }
          try {
            const statusRes = await api.translation.status(projectId, docId)
            const job = statusRes.data

            set((s) => ({
              translationResult: s.translationResult ? {
                ...s.translationResult,
                progress: job.progress,
                status: job.status === "translating" ? "translating" : job.status === "completed" ? "completed" : "error",
              } : null,
            }))
            lastProgressTime = Date.now()

            if (job.status === "completed" && job.result) {
              finishWith(job.result.text, job.result.tokens, "completed")
              console.log("[STORE] Translation completed via polling")
            } else if (job.status === "failed") {
              finishWith("", 0, "error")
              console.error("[STORE] Translation failed")
            }
          } catch (e) {
            console.error("[STORE] translation poll error:", e)
          }
        }, 2000)
      }

      try {
        const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws"
        const hostname = typeof window !== "undefined" ? window.location.hostname : "localhost"
        const API_PORT = process.env.NEXT_PUBLIC_API_PORT || '8000'
        const wsUrl = `${protocol}://${hostname}:${API_PORT}/api/projects/${projectId}/documents/${docId}/translate/ws`
        console.log(`[STORE] Connecting WebSocket: ${wsUrl}`)
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          console.log("[STORE] WebSocket connected")
        }

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            if (msg.type === "chunk") {
              chunkMap.set(msg.index, msg.content)
              const partialContent = buildContent()
              lastProgressTime = Date.now()
              set((s) => ({
                translationResult: s.translationResult ? {
                  ...s.translationResult,
                  translatedContent: partialContent,
                  progress: msg.progress,
                } : null,
              }))
            } else if (msg.type === "done") {
              finishWith(msg.result.text, msg.result.tokens, "completed")
              console.log("[STORE] Translation completed via WebSocket")
            } else if (msg.type === "error") {
              const partial = buildContent()
              finishWith(partial || originalText, 0, "error")
              console.error("[STORE] Translation error via WebSocket:", msg.message)
            } else if (msg.type === "status") {
              console.log(`[STORE] WS status: ${msg.status} progress=${msg.progress}`)
            }
          } catch (e) {
            console.error("[STORE] WS message parse error:", e)
          }
        }

        ws.onerror = () => {
          console.warn("[STORE] WebSocket error, falling back to polling")
          if (ws) { try { ws.close() } catch {}; ws = null }
          startPolling()
        }

        ws.onclose = () => {
          if (!done) {
            console.warn("[STORE] WebSocket closed early, falling back to polling")
            startPolling()
          }
        }
      } catch {
      startPolling()
    }

    const WATCHDOG_TIMEOUT = 30_000
    const watchdogInterval = setInterval(() => {
      if (done) { clearInterval(watchdogInterval); return }
      const stallDuration = Date.now() - lastProgressTime
      if (stallDuration > WATCHDOG_TIMEOUT) {
        console.warn(`[STORE] WATCHDOG: Progress stalled for ${Math.round(stallDuration / 1000)}s, usePolling=${usePolling}`)
        if (!usePolling && ws) {
          console.warn("[STORE] WATCHDOG: Closing stale WebSocket, falling back to polling")
          try { ws.close() } catch {}
          ws = null
          startPolling()
        } else {
          console.warn("[STORE] WATCHDOG: Polling also stalled, marking as failed")
          const partial = buildContent()
          finishWith(partial || originalText, 0, "error")
          clearInterval(watchdogInterval)
        }
      }
    }, 5_000)

    } catch (err) {
      console.error(`[STORE] Translation start failed:`, err)
      get().setTranslatingFileId(null)
      set((s) => ({
        translationResult: s.translationResult ? {
          ...s.translationResult,
          status: "error",
          progress: 0,
        } : null,
      }))
    }
  },

  readerSettings: defaultReaderSettings,
  updateReaderSettings: (settings) =>
    set((state) => ({
      readerSettings: { ...state.readerSettings, ...settings },
    })),

  mobileTab: "original",
  setMobileTab: (tab) => set({ mobileTab: tab }),

  mobileTocOpen: false,
  setMobileTocOpen: (open) => set({ mobileTocOpen: open }),

  apiStats: {
    totalRequests: 0,
    totalTokens: { inputCacheHit: 0, inputCacheMiss: 0, output: 0, total: 0, cost: 0 },
    todayRequests: 0,
    todayTokens: { inputCacheHit: 0, inputCacheMiss: 0, output: 0, total: 0, cost: 0 },
  },
  updateApiStats: (stats) => set({ apiStats: stats }),

  refreshApiStats: async () => {
    console.log(`[STORE] Refreshing API stats...`)
    try {
      const res = await api.stats.api()
      console.log(`[STORE] API stats raw response:`, res)

      const rawData: any = (res as any).data || res
      const promptTokens = rawData.prompt_tokens || 0
      const completionTokens = rawData.completion_tokens || 0
      const cachedTokens = rawData.cached_tokens || 0
      const totalTokens = rawData.tokens_used || (promptTokens + completionTokens) || 0
      const cost = typeof rawData.cost === "number" ? rawData.cost : 0
      const newStats: ApiStats = {
        totalRequests: rawData.documents || rawData.totalRequests || 0,
        totalTokens: {
          inputCacheHit: cachedTokens,
          inputCacheMiss: Math.max(0, promptTokens - cachedTokens),
          output: completionTokens,
          total: totalTokens,
          cost,
        },
        todayRequests: rawData.todayRequests || 0,
        todayTokens: {
          inputCacheHit: 0,
          inputCacheMiss: 0,
          output: 0,
          total: 0,
          cost: 0,
        },
      }
      set({ apiStats: newStats })
    } catch (err) {
      console.error(`[STORE] Failed to load stats:`, err)
    }
  },

  glossary: [
    { id: "gl-1", source: "Transformer", target: "Transformer", context: "模型名称" },
    { id: "gl-2", source: "attention", target: "注意力机制", context: "深度学习" },
    { id: "gl-3", source: "encoder", target: "编码器", context: "序列到序列" },
    { id: "gl-4", source: "decoder", target: "解码器", context: "序列到序列" },
  ],
  addGlossaryTerm: (term) =>
    set((state) => ({ glossary: [...state.glossary, term] })),
  removeGlossaryTerm: (id) =>
    set((state) => ({
      glossary: state.glossary.filter((t) => t.id !== id),
    })),

  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  settingsPanelOpen: false,
  setSettingsPanelOpen: (open) => set({ settingsPanelOpen: open }),

  uploadDialogOpen: false,
  setUploadDialogOpen: (open) => set({ uploadDialogOpen: open }),

  glossaryDialogOpen: false,
  setGlossaryDialogOpen: (open) => set({ glossaryDialogOpen: open }),

  batchDialogOpen: false,
  setBatchDialogOpen: (open) => set({ batchDialogOpen: open }),

  searchDialogOpen: false,
  setSearchDialogOpen: (open) => set({ searchDialogOpen: open }),

  translatingFileId: null,
  setTranslatingFileId: (id) => {
    set({ translatingFileId: id })
    if (id) {
      localStorage.setItem("translating_file_id", id)
      localStorage.setItem("translating_file_time", Date.now().toString())
    } else {
      localStorage.removeItem("translating_file_id")
      localStorage.removeItem("translating_file_time")
    }
  },

  deleteFile: async (projectId, fileId) => {
    console.log(`[STORE] Deleting file: ${fileId} from project: ${projectId}`)
    try {
      await api.files.delete(projectId, fileId)
      const res = await api.files.list(projectId)
      const files = res.data || []
      set((state) => {
        const newState: any = {
          projects: state.projects.map((p) =>
            p.id === projectId ? { ...p, files: files.map((d: any) => ({
              id: d.id,
              name: d.original_name || d.filename || "unknown",
              type: d.doc_type || "pdf",
              size: d.size || 0,
              uploadedAt: d.created_at || "",
              status: d.status || "uploaded",
              path: d.file_path || "",
            })) } : p
          ),
        }
        if (state.activeFileId === fileId) {
          newState.activeFileId = null
          newState.documentContent = null
          newState.translationResult = null
        }
        return newState
      })
    } catch (err) {
      console.error(`[STORE] Failed to delete file:`, err)
    }
  },

  renameFile: async (projectId, fileId, newName) => {
    console.log(`[STORE] Renaming file: ${fileId} in project: ${projectId} to: ${newName}`)
    try {
      await api.files.rename(projectId, fileId, newName)
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === projectId
            ? {
                ...p,
                files: p.files.map((f) =>
                  f.id === fileId ? { ...f, name: newName } : f
                ),
              }
            : p
        ),
      }))
    } catch (err) {
      console.error(`[STORE] Failed to rename file:`, err)
    }
  },

  addFileToProject: async (projectId, file) => {
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, files: [...p.files, file] } : p
      ),
    }));
    try {
      const res = await api.files.list(projectId);
      const files = res.data || [];
      set((state) => ({
        projects: state.projects.map((p) =>
          p.id === projectId ? { ...p, files } : p
        ),
      }));
    } catch (err) {
      console.error(`[STORE] Failed to fetch documents after upload:`, err);
    }
  },

  searchResults: [],
  searchQuery: "",
  searchLoading: false,

  performSearch: async (q) => {
    if (!q.trim()) {
      set({ searchResults: [], searchQuery: "" })
      return
    }
    set({ searchLoading: true, searchQuery: q })
    try {
      const res = await api.search.query(q)
      set({ searchResults: res.data || [], searchLoading: false })
    } catch (err) {
      console.error(`[STORE] Search failed:`, err)
      set({ searchLoading: false })
    }
  },

  clearSearch: () => set({ searchResults: [], searchQuery: "", searchLoading: false }),

  orphanData: null,
  orphanLoading: false,
  cleanupDialogOpen: false,
  setCleanupDialogOpen: (open) => set({ cleanupDialogOpen: open }),

  loadOrphanData: async () => {
    set({ orphanLoading: true })
    try {
      const res = await api.cleanup.listOrphans()
      set({ orphanData: res.data, orphanLoading: false })
    } catch (err) {
      console.error(`[STORE] Failed to load orphan data:`, err)
      set({ orphanLoading: false })
    }
  },

  deleteSelectedOrphans: async (paths) => {
    if (paths.length === 0) return
    set({ orphanLoading: true })
    try {
      await api.cleanup.deleteSelected(paths)
      const res = await api.cleanup.listOrphans()
      set({ orphanData: res.data, orphanLoading: false })
    } catch (err) {
      console.error(`[STORE] Selective cleanup failed:`, err)
      set({ orphanLoading: false })
    }
  },

  executeCleanup: async () => {
    set({ orphanLoading: true })
    try {
      await api.cleanup.deleteOrphans()
      set({ orphanData: null, orphanLoading: false })
    } catch (err) {
      console.error(`[STORE] Cleanup failed:`, err)
      set({ orphanLoading: false })
    }
  },

  tokenBreakdown: null,
  totalTokenUsage: 0,
  totalTokenCost: 0,
  tokenLoading: false,
  tokenDialogOpen: false,
  setTokenDialogOpen: (open) => set({ tokenDialogOpen: open }),

  loadTokenStats: async () => {
    set({ tokenLoading: true })
    try {
      const res = await api.stats.tokens()
      set({
        tokenBreakdown: res.data.project_breakdown || [],
        totalTokenUsage: res.data.total_tokens || 0,
        totalTokenCost: (res.data as any).total_cost || 0,
        tokenLoading: false,
      })
    } catch (err) {
      console.error(`[STORE] Failed to load token stats:`, err)
      set({ tokenLoading: false })
    }
  },

  tokenHistory: null,
  tokenHistoryDays: 30,
  tokenHistoryLoading: false,

  loadTokenHistory: async (days) => {
    set({ tokenHistoryLoading: true, tokenHistoryDays: days ?? useAppStore.getState().tokenHistoryDays })
    try {
      const res = await api.stats.history(days ?? useAppStore.getState().tokenHistoryDays)
      set({
        tokenHistory: {
          records: res.data.records || [],
          daily_summary: res.data.daily_summary || [],
          total_records: res.data.total_records || 0,
          total_tokens: res.data.total_tokens || 0,
          total_prompt_tokens: res.data.total_prompt_tokens || 0,
          total_completion_tokens: res.data.total_completion_tokens || 0,
          total_cached_tokens: res.data.total_cached_tokens || 0,
        },
        tokenHistoryLoading: false,
      })
    } catch (err) {
      console.error(`[STORE] Failed to load token history:`, err)
      set({ tokenHistoryLoading: false })
    }
  },
}))