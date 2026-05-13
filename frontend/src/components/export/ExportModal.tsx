import { useState, useEffect } from "react"
import { Download, FileText, FileCode, FileImage, FileType, Check, Loader2, AlertCircle } from "lucide-react"
import { Button, Dialog } from "@/components/ui"
import { api } from "@/lib/api"
import type { ExportOptions, ExportFormat } from "@/types"

interface ExportModalProps {
  open: boolean
  onClose: () => void
  projectId: string | undefined
  docId: string | undefined
}

const formatIcons: Record<string, typeof FileText> = {
  md: FileText,
  html: FileCode,
  pdf: FileImage,
  docx: FileType,
}

const formatLabels: Record<string, string> = {
  md: "Markdown",
  html: "HTML",
  pdf: "PDF",
  docx: "DOCX",
}

const themeLabels: Record<string, string> = {
  academic: "学术风格",
  dark: "深色模式",
  compact: "紧凑模式",
}

const pageSizeLabels: Record<string, string> = {
  A4: "A4",
  Letter: "Letter",
}

export function ExportModal({ open, onClose, projectId, docId }: ExportModalProps) {
  const [format, setFormat] = useState<ExportFormat>("pdf")
  const [includeOriginal, setIncludeOriginal] = useState(true)
  const [includeTranslation, setIncludeTranslation] = useState(true)
  const [embedImages, setEmbedImages] = useState(true)
  const [theme, setTheme] = useState("academic")
  const [pageSize, setPageSize] = useState("A4")
  const [fontSize, setFontSize] = useState(12)
  const [includeTOC, setIncludeTOC] = useState(false)
  const [watermark, setWatermark] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (open) {
      setExportError(null)
      setProgress(0)
    }
  }, [open])

  const handleExport = async () => {
    if (!projectId || !docId) return

    setIsExporting(true)
    setExportError(null)
    setProgress(0)

    try {
      const apiOptions = {
        format: format,
        embed_images: embedImages,
        include_original: includeOriginal,
        include_translation: includeTranslation,
        theme,
        page_size: pageSize,
        font_size: fontSize,
        include_toc: includeTOC,
        watermark: watermark || undefined,
      }

      const startTime = Date.now()
      const progressInterval = setInterval(() => {
        const elapsed = Date.now() - startTime
        if (elapsed < 3000) {
          setProgress(Math.min(30, Math.floor(elapsed / 100)))
        } else if (elapsed < 6000) {
          setProgress(Math.min(60, 30 + Math.floor((elapsed - 3000) / 100)))
        } else {
          setProgress(Math.min(90, 60 + Math.floor((elapsed - 6000) / 150)))
        }
      }, 500)

      const response = await api.export.generate(projectId, docId, apiOptions)
      clearInterval(progressInterval)
      setProgress(100)

      const { content, mime, filename } = response.data
      const blob = new Blob([content], { type: mime })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)

      setTimeout(() => {
        onClose()
        resetForm()
      }, 500)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "导出失败，请重试")
      console.error("[EXPORT] Export failed:", err)
    } finally {
      setIsExporting(false)
    }
  }

  const resetForm = () => {
    setFormat("pdf")
    setIncludeOriginal(true)
    setIncludeTranslation(true)
    setEmbedImages(true)
    setTheme("academic")
    setPageSize("A4")
    setFontSize(12)
    setIncludeTOC(false)
    setWatermark("")
    setProgress(0)
  }

  const isValid = includeOriginal || includeTranslation

  return (
    <Dialog open={open} onClose={onClose} title="导出翻译">
      <div className="space-y-6">
        <div>
          <label className="block mb-2 text-sm font-medium text-surface-900 dark:text-surface-100">导出格式</label>
          <div className="grid grid-cols-4 gap-2">
            {(["md", "html", "pdf", "docx"] as ExportFormat[]).map((fmt) => {
              const Icon = formatIcons[fmt]
              return (
                <button
                  key={fmt}
                  type="button"
                  className={`flex flex-col items-center gap-1 py-3 px-2 rounded-lg border text-sm transition-colors ${
                    format === fmt
                      ? "bg-accent-500 text-white border-accent-500"
                      : "bg-surface-50 dark:bg-surface-800 text-surface-600 dark:text-surface-300 border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700"
                  }`}
                  onClick={() => setFormat(fmt)}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-xs">{formatLabels[fmt]}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="space-y-3">
          <label className="block text-sm font-medium text-surface-900 dark:text-surface-100">内容选项</label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeOriginal}
              onChange={(e) => setIncludeOriginal(e.target.checked)}
              className="w-4 h-4 rounded border-surface-300 text-accent-500 focus:ring-accent-500"
            />
            <span className="text-sm text-surface-700 dark:text-surface-300">包含原文</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeTranslation}
              onChange={(e) => setIncludeTranslation(e.target.checked)}
              className="w-4 h-4 rounded border-surface-300 text-accent-500 focus:ring-accent-500"
            />
            <span className="text-sm text-surface-700 dark:text-surface-300">包含译文</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={embedImages}
              onChange={(e) => setEmbedImages(e.target.checked)}
              className="w-4 h-4 rounded border-surface-300 text-accent-500 focus:ring-accent-500"
            />
            <span className="text-sm text-surface-700 dark:text-surface-300">嵌入图片 (Base64)</span>
          </label>
          {format === "pdf" && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeTOC}
                onChange={(e) => setIncludeTOC(e.target.checked)}
                className="w-4 h-4 rounded border-surface-300 text-accent-500 focus:ring-accent-500"
              />
              <span className="text-sm text-surface-700 dark:text-surface-300">生成目录 (TOC)</span>
            </label>
          )}
        </div>

        {(format === "html" || format === "pdf") && (
          <div>
            <label className="block mb-2 text-sm font-medium text-surface-900 dark:text-surface-100">主题风格</label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm focus:ring-2 focus:ring-accent-500 focus:border-accent-500"
            >
              {Object.entries(themeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        )}

        {(format === "pdf" || format === "docx") && (
          <div>
            <label className="block mb-2 text-sm font-medium text-surface-900 dark:text-surface-100">页面大小</label>
            <select
              value={pageSize}
              onChange={(e) => setPageSize(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm focus:ring-2 focus:ring-accent-500 focus:border-accent-500"
            >
              {Object.entries(pageSizeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
        )}

        {(format === "html" || format === "pdf") && (
          <div>
            <div className="flex justify-between mb-2">
              <label className="text-sm font-medium text-surface-900 dark:text-surface-100">字号</label>
              <span className="text-sm text-surface-500">{fontSize}pt</span>
            </div>
            <input
              type="range"
              min={10}
              max={16}
              step={1}
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value))}
              className="w-full h-2 bg-surface-200 dark:bg-surface-700 rounded-lg appearance-none cursor-pointer accent-accent-500"
            />
          </div>
        )}

        {format === "pdf" && (
          <div>
            <label className="block mb-2 text-sm font-medium text-surface-900 dark:text-surface-100">水印文字 (可选)</label>
            <input
              type="text"
              placeholder="输入水印文字，如：内部文档"
              value={watermark}
              onChange={(e) => setWatermark(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-surface-100 text-sm placeholder-surface-400 focus:ring-2 focus:ring-accent-500 focus:border-accent-500"
            />
          </div>
        )}

        {exportError && (
          <div className="flex items-center gap-2 text-red-500 bg-red-50 dark:bg-red-500/10 p-3 rounded-lg">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="text-sm">{exportError}</span>
          </div>
        )}

        {isExporting && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm text-surface-600 dark:text-surface-400">正在生成 {formatLabels[format]}...</span>
            </div>
            <div className="relative h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-accent-500 transition-all duration-300 rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleExport}
            disabled={!isValid || isExporting}
          >
            {isExporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                导出中...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                导出
              </>
            )}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}