"use client"

import React, { useState } from "react"
import {
  Settings,
  Type,
  Sun,
  Moon,
  Monitor,
  FolderOpen,
  Download,
  Save,
} from "lucide-react"
import { useAppStore } from "@/store"
import { Card, Button } from "@/components/ui"
import type { ExportOptions } from "@/types"

export function SettingsPanel() {
  const settingsPanelOpen = useAppStore((s) => s.settingsPanelOpen)
  const setSettingsPanelOpen = useAppStore((s) => s.setSettingsPanelOpen)
  const readerSettings = useAppStore((s) => s.readerSettings)
  const updateReaderSettings = useAppStore((s) => s.updateReaderSettings)
  const activeProject = useAppStore((s) =>
    s.projects.find((p) => p.id === s.activeProjectId)
  )
  const updateProject = useAppStore((s) => s.updateProject)
  const translationResult = useAppStore((s) => s.translationResult)
  const theme = useAppStore((s) => s.theme)
  const setTheme = useAppStore((s) => s.setTheme)

  const [outputPath, setOutputPath] = useState(activeProject?.outputPath || "D:/Translations")

  if (!settingsPanelOpen) return null

  const handleSaveOutputPath = () => {
    if (activeProject) {
      updateProject(activeProject.id, { outputPath })
    }
  }

  const handleExport = async (format: "html" | "pdf" | "markdown") => {
    if (!translationResult) return

    const originalContent = translationResult.originalContent || ""
    const translatedContent = translationResult.translatedContent || ""

    const embedImages = async (text: string): Promise<string> => {
      const imgRegex = /<img[^>]+src="([^"]+)"[^>]*\/?>/gi
      let result = text
      const matches = text.matchAll(imgRegex)
      for (const match of matches) {
        const fullTag = match[0]
        const src = match[1]
        try {
          const response = await fetch(src)
          const blob = await response.blob()
          const reader = new FileReader()
          const dataUrl = await new Promise<string>((resolve) => {
            reader.onload = () => resolve(reader.result as string)
            reader.readAsDataURL(blob)
          })
          result = result.replace(fullTag, fullTag.replace(src, dataUrl))
        } catch (e) {
          console.warn(`[EXPORT] Failed to embed image: ${src}`, e)
        }
      }
      return result
    }

    const content = `# Original\n\n${originalContent}\n\n# Translation\n\n${translatedContent}`

    if (format === "html") {
      const htmlContent = await embedImages(content)
      const styledHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>翻译导出</title>
<style>
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.75; color: #1a1a2e; }
h1 { font-size: 1.5rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 0.5rem; margin-top: 2rem; }
h2 { font-size: 1.25rem; margin-top: 1.5rem; }
h3 { font-size: 1.1rem; margin-top: 1.25rem; }
p { margin: 0.75rem 0; }
img { max-width: 100%; height: auto; display: block; margin: 1rem auto; }
pre { background: #f1f5f9; padding: 1rem; border-radius: 8px; overflow-x: auto; }
code { background: #f1f5f9; padding: 0.15rem 0.3rem; border-radius: 4px; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #e2e8f0; padding: 0.5rem; text-align: left; }
th { background: #f8fafc; font-weight: 600; }
</style>
</head>
<body>
${htmlContent.replace(/\n/g, "<br>")}
</body>
</html>`
      const blob = new Blob([styledHtml], { type: "text/html;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "translation.html"
      a.click()
      URL.revokeObjectURL(url)
    } else if (format === "markdown") {
      const mdContent = await embedImages(content)
      const blob = new Blob([mdContent], { type: "text/markdown;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "translation.md"
      a.click()
      URL.revokeObjectURL(url)
    } else {
      const txtContent = `# Original\n\n${originalContent}\n\n# Translation\n\n${translatedContent}`
      const blob = new Blob([txtContent], { type: "text/plain;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "translation.txt"
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 bg-black/20 backdrop-blur-sm"
        onClick={() => setSettingsPanelOpen(false)}
      />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-96 bg-white dark:bg-surface-900 border-l border-surface-200 dark:border-surface-700 shadow-modal animate-slide-in-right overflow-y-auto">
        <div className="sticky top-0 z-10 bg-white dark:bg-surface-900 border-b border-surface-200 dark:border-surface-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-accent-500" />
            <h2 className="text-base font-semibold text-surface-900 dark:text-surface-100">
              设置
            </h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSettingsPanelOpen(false)}
          >
            关闭
          </Button>
        </div>

        <div className="p-6 space-y-6">
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Sun className="w-4 h-4 text-accent-500" />
              <span className="text-sm font-medium text-surface-900 dark:text-surface-100">
                主题模式
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: "light", icon: Sun, label: "浅色" },
                { value: "dark", icon: Moon, label: "深色" },
                { value: "system", icon: Monitor, label: "系统" },
              ].map(({ value, icon: Icon, label }) => (
                  <button
                    key={value}
                    onClick={() => setTheme(value as "light" | "dark" | "system")}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all ${
                      theme === value
                        ? "border-accent-500 bg-accent-50 dark:bg-accent-500/10 text-accent-600 dark:text-accent-400"
                        : "border-surface-200 dark:border-surface-700 text-surface-500 dark:text-surface-400 hover:border-surface-300 dark:hover:border-surface-600"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-xs font-medium">{label}</span>
                  </button>
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center gap-2 mb-3">
              <Type className="w-4 h-4 text-accent-500" />
              <span className="text-sm font-medium text-surface-900 dark:text-surface-100">
                阅读设置
              </span>
            </div>
            <Card className="p-4 space-y-4">
              <div>
                <label className="block text-xs text-surface-500 mb-2">
                  字体大小：{readerSettings.fontSize}px
                </label>
                <input
                  type="range"
                  min="12"
                  max="28"
                  step="1"
                  value={readerSettings.fontSize}
                  onChange={(e) =>
                    updateReaderSettings({
                      fontSize: parseInt(e.target.value),
                    })
                  }
                  className="w-full accent-accent-500"
                />
              </div>
              <div>
                <label className="block text-xs text-surface-500 mb-2">
                  行间距：{readerSettings.lineHeight.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="1.2"
                  max="2.5"
                  step="0.1"
                  value={readerSettings.lineHeight}
                  onChange={(e) =>
                    updateReaderSettings({
                      lineHeight: parseFloat(e.target.value),
                    })
                  }
                  className="w-full accent-accent-500"
                />
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={readerSettings.syncScroll}
                  onChange={(e) =>
                    updateReaderSettings({
                      syncScroll: e.target.checked,
                    })
                  }
                  className="rounded border-surface-300 dark:border-surface-600 text-accent-500 focus:ring-accent-500"
                />
                <span className="text-sm text-surface-700 dark:text-surface-300">
                  双栏同步滚动
                </span>
              </label>
            </Card>
          </section>

          <section>
            <div className="flex items-center gap-2 mb-3">
              <FolderOpen className="w-4 h-4 text-accent-500" />
              <span className="text-sm font-medium text-surface-900 dark:text-surface-100">
                输出路径
              </span>
            </div>
            <Card className="p-4">
              <div className="flex gap-2">
                <input
                  className="input-field flex-1"
                  value={outputPath}
                  onChange={(e) => setOutputPath(e.target.value)}
                  placeholder="D:/Translations"
                />
                <Button variant="secondary" size="sm" onClick={handleSaveOutputPath}>
                  <Save className="w-3.5 h-3.5" />
                </Button>
              </div>
              <p className="text-xs text-surface-400 mt-2">
                翻译后的文件将保存到此目录
              </p>
            </Card>
          </section>

          <section>
            <div className="flex items-center gap-2 mb-3">
              <Download className="w-4 h-4 text-accent-500" />
              <span className="text-sm font-medium text-surface-900 dark:text-surface-100">
                导出翻译
              </span>
            </div>
            <Card className="p-4">
              <div className="grid grid-cols-3 gap-2">
                {(["HTML", "PDF", "Markdown"] as const).map((fmt) => (
                  <Button
                    key={fmt}
                    variant="secondary"
                    size="sm"
                    onClick={() => handleExport(fmt.toLowerCase() as "html" | "pdf" | "markdown")}
                    disabled={!translationResult}
                  >
                    <Download className="w-3.5 h-3.5" />
                    {fmt}
                  </Button>
                ))}
              </div>
              {!translationResult && (
                <p className="text-xs text-surface-400 mt-2 text-center">
                  请先完成翻译后再导出
                </p>
              )}
            </Card>
          </section>
        </div>
      </div>
    </>
  )
}