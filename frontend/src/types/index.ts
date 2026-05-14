export interface Project {
  id: string
  name: string
  description?: string
  createdAt: string
  updatedAt: string
  sourceLanguage: string
  targetLanguage: string
  outputPath: string
  files: PaperFile[]
  status: ProjectStatus
}

export type ProjectStatus = "idle" | "translating" | "completed" | "error"

export interface PaperFile {
  id: string
  name: string
  type: FileType
  size: number
  uploadedAt: string
  status: FileStatus
  path: string
}

export type FileType = "pdf" | "docx" | "markdown" | "latex" | "html"

export type FileStatus = "uploaded" | "processing" | "translated" | "translating" | "completed" | "error" | "failed"

export interface TranslationResult {
  id: string
  fileId: string
  originalContent: string
  translatedContent: string
  progress: number
  status: TranslationStatus
  tokenUsage: TokenUsage
  cached: boolean
  createdAt: string
}

export type TranslationStatus = "pending" | "queued" | "translating" | "completed" | "error"

export interface TokenUsage {
  inputCacheHit: number
  inputCacheMiss: number
  output: number
  total: number
  cost: number
}

export interface ApiStats {
  totalRequests: number
  totalTokens: TokenUsage
  todayRequests: number
  todayTokens: TokenUsage
}

export interface GlossaryTerm {
  id: string
  source: string
  target: string
  context?: string
}

export interface TocItem {
  id: string
  title: string
  level: number
  pageNumber?: number
}

export interface ReaderSettings {
  fontSize: number
  lineHeight: number
  fontFamily: "sans" | "serif" | "mono"
  showLineNumbers: boolean
  syncScroll: boolean
}

export type ExportFormat = "md" | "html" | "pdf" | "docx"

export interface ExportOptions {
  format: ExportFormat
  includeOriginal: boolean
  includeTranslation: boolean
  embedImages?: boolean
  theme?: "academic" | "modern" | "dark" | "compact"
  pageSize?: "A4" | "Letter"
  fontSize?: number
  includeTOC?: boolean
  watermark?: string
  watermarkPos?: "center" | "top" | "bottom"
  coverPage?: boolean
  subtitle?: string
  watermarkTiled?: boolean
  codeHighlight?: boolean
  compactMode?: boolean
}

export interface BatchTranslationJob {
  id: string
  projectId: string
  fileIds: string[]
  status: "pending" | "running" | "completed" | "error"
  progress: number
  createdAt: string
  completedAt?: string
}

export type ThemeMode = "light" | "dark" | "system"

export interface DragItem {
  type: "file" | "project"
  id: string
}
