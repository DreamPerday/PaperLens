"use client"

import React, { useRef, useCallback, useState } from "react"
import {
  BookOpen,
  FileText,
  Maximize2,
  Minimize2,
  Languages,
  Loader2,
  Download,
  AlertCircle,
  Pin,
  PinOff,
  X,
  List,
} from "lucide-react"
import { useAppStore } from "@/store"
import { useSyncScroll } from "@/hooks"
import { api } from "@/lib/api"
import { Button } from "@/components/ui"
import { TOC } from "./TOC"
import { DocumentView } from "./DocumentView"
import { ExportModal } from "../export/ExportModal"
import { cn } from "@/lib/utils"

export function DualPaneReader() {
  const translationResult = useAppStore((s) => s.translationResult)
  const readerSettings = useAppStore((s) => s.readerSettings)
  const updateReaderSettings = useAppStore((s) => s.updateReaderSettings)
  const activeFileId = useAppStore((s) => s.activeFileId)
  const documentLoading = useAppStore((s) => s.documentLoading)
  const documentError = useAppStore((s) => s.documentError)
  const documentContent = useAppStore((s) => s.documentContent)
  const startTranslation = useAppStore((s) => s.startTranslation)
  const translatingFileId = useAppStore((s) => s.translatingFileId)
  const mobileTab = useAppStore((s) => s.mobileTab)
  const setMobileTab = useAppStore((s) => s.setMobileTab)
  const mobileTocOpen = useAppStore((s) => s.mobileTocOpen)
  const setMobileTocOpen = useAppStore((s) => s.setMobileTocOpen)

  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)

  const { handleScroll } = useSyncScroll(
    leftRef,
    rightRef,
    readerSettings.syncScroll
  )

  const [showToc, setShowToc] = useState(false)
  const [tocPinned, setTocPinned] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [exportModalOpen, setExportModalOpen] = useState(false)

  const isTranslating = translatingFileId === activeFileId

  const handleTocNavigate = useCallback((id: string, panel?: "left" | "right") => {
    const targetRef = panel === "right" ? rightRef : leftRef
    const scrollingEl = targetRef.current
    if (!scrollingEl) return
    const element = scrollingEl.querySelector(`[id="${id}"]`)
    if (!element) return
    const containerTop = scrollingEl.getBoundingClientRect().top
    const targetTop = element.getBoundingClientRect().top
    const offset = targetTop - containerTop + scrollingEl.scrollTop - 16
    scrollingEl.scrollTo({ top: Math.max(0, offset), behavior: "smooth" })
    setMobileTocOpen(false)
  }, [setMobileTocOpen])

  const handleStartTranslate = useCallback(async () => {
    if (!activeFileId) return
    if (isTranslating) return
    await startTranslation(activeFileId)
  }, [activeFileId, startTranslation, isTranslating])

  const handleExport = useCallback(() => {
    setExportModalOpen(true)
  }, [])

  const hasTranslation = translationResult
    ? (translationResult.status === "completed" || translationResult.status === "translating")
      && !!translationResult.translatedContent
    : false

  if (!activeFileId) {
    return (
      <div className="flex-1 flex items-center justify-center h-full overflow-hidden">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center">
            <BookOpen className="w-8 h-8 text-surface-400" />
          </div>
          <h3 className="text-lg font-medium text-surface-600 dark:text-surface-400 mb-1">
            选择论文开始阅读
          </h3>
          <p className="text-sm text-surface-400 dark:text-surface-500">
            从左侧项目列表中选择一篇论文
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("flex-1 flex flex-col min-h-0", fullscreen && "fixed inset-0 z-50 bg-[rgb(var(--background))]")}>

      {/* Mobile Tab Switcher */}
      {hasTranslation && (
        <div className="lg:hidden flex items-center border-b border-surface-200/50 dark:border-surface-700/30 bg-surface-50/80 dark:bg-surface-900/80 backdrop-blur-sm sticky top-0 z-10 flex-shrink-0">
          <button
            onClick={() => setMobileTocOpen(true)}
            className="px-3 py-2.5 text-surface-500 hover:text-surface-700 dark:hover:text-surface-300"
          >
            <List className="w-4 h-4" />
          </button>
          <div className="flex-1 flex">
            <button
              onClick={() => setMobileTab("original")}
              className={cn(
                "flex-1 py-2.5 text-xs font-medium text-center transition-colors border-b-2",
                mobileTab === "original"
                  ? "border-accent-500 text-accent-600 dark:text-accent-400"
                  : "border-transparent text-surface-400"
              )}
            >
              <span className="badge-primary text-2xs mr-1">原文</span>
              EN
            </button>
            <button
              onClick={() => setMobileTab("translation")}
              className={cn(
                "flex-1 py-2.5 text-xs font-medium text-center transition-colors border-b-2",
                mobileTab === "translation"
                  ? "border-emerald-500 text-emerald-600 dark:text-emerald-400"
                  : "border-transparent text-surface-400"
              )}
            >
              <span className="badge-success text-2xs mr-1">译文</span>
              ZH
            </button>
          </div>
        </div>
      )}

      {/* PC Toolbar */}
      <div className="hidden lg:flex items-center justify-between px-4 py-2 border-b border-surface-200/50 dark:border-surface-700/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5">
            <Button
              variant={showToc ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setShowToc(!showToc)}
            >
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">目录</span>
            </Button>
            {showToc && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setTocPinned(!tocPinned)}
                className={tocPinned ? "text-accent-500" : ""}
              >
                {tocPinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
              </Button>
            )}
          </div>
          <div className="w-px h-4 bg-surface-200 dark:bg-surface-700" />
          <div className="flex items-center gap-1.5">
            <Button
              variant={readerSettings.syncScroll ? "secondary" : "ghost"}
              size="sm"
              onClick={() =>
                updateReaderSettings({ syncScroll: !readerSettings.syncScroll })
              }
            >
              <span className="text-xs">
                {readerSettings.syncScroll ? "同步滚动: 开" : "同步滚动: 关"}
              </span>
            </Button>
          </div>
          <div className="w-px h-4 bg-surface-200 dark:bg-surface-700" />
          <Button
            variant="primary"
            size="sm"
            onClick={handleStartTranslate}
            disabled={isTranslating || !activeFileId}
          >
            {isTranslating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Languages className="w-4 h-4" />
            )}
            {isTranslating
              ? "翻译中..."
              : translationResult?.status === "completed"
              ? "重新翻译"
              : "AI 翻译"}
          </Button>
          {translationResult && (
            <>
              <div className="w-px h-4 bg-surface-200 dark:bg-surface-700" />
              <Button
                variant="ghost"
                size="sm"
                onClick={handleExport}
              >
                <Download className="w-3.5 h-3.5" />
                <span className="text-2xs hidden sm:inline">导出</span>
              </Button>
            </>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              const current = readerSettings.fontSize
              const next = Math.min(current + 2, 28)
              updateReaderSettings({ fontSize: next })
            }}
          >
            A+
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              const current = readerSettings.fontSize
              const next = Math.max(current - 2, 12)
              updateReaderSettings({ fontSize: next })
            }}
          >
            A-
          </Button>
          <span className="text-2xs text-surface-400 w-7 text-center tabular-nums">
            {readerSettings.fontSize}px
          </span>
          <div className="w-px h-4 bg-surface-200 dark:bg-surface-700 mx-1" />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFullscreen(!fullscreen)}
          >
            {fullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Mobile Toolbar (compact) */}
      <div className="lg:hidden flex items-center justify-between px-3 py-1.5 border-b border-surface-200/50 dark:border-surface-700/30 flex-shrink-0 gap-1">
        <Button
          variant="primary"
          size="sm"
          onClick={handleStartTranslate}
          disabled={isTranslating || !activeFileId}
        >
          {isTranslating ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Languages className="w-3.5 h-3.5" />
          )}
          <span className="text-2xs ml-1">
            {isTranslating ? "翻译中" : translationResult?.status === "completed" ? "重译" : "翻译"}
          </span>
        </Button>

        <div className="flex items-center gap-0.5">
          <Button variant="ghost" size="sm" onClick={() => updateReaderSettings({ fontSize: Math.max(readerSettings.fontSize - 1, 14) })}>
            <span className="text-xs">A-</span>
          </Button>
          <span className="text-2xs text-surface-400 w-6 text-center">{readerSettings.fontSize}</span>
          <Button variant="ghost" size="sm" onClick={() => updateReaderSettings({ fontSize: Math.min(readerSettings.fontSize + 1, 24) })}>
            <span className="text-xs">A+</span>
          </Button>
          <div className="w-px h-3 bg-surface-200 dark:bg-surface-700 mx-0.5" />
          <Button variant="ghost" size="sm" onClick={() => setFullscreen(!fullscreen)}>
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </Button>
          {hasTranslation && (
            <Button variant="ghost" size="sm" className="px-1.5" onClick={handleExport}>
              <Download className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {isTranslating && (
        <div className="px-4 py-2 border-b border-surface-200/50 dark:border-surface-700/30 bg-accent-50/50 dark:bg-accent-500/5 flex-shrink-0">
          <div className="flex items-center justify-between text-xs text-surface-500 mb-1.5">
            <div className="flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-500" />
              <span>AI 正在翻译...</span>
            </div>
          </div>
          <div className="relative w-full h-1 rounded-full bg-surface-200 dark:bg-surface-700 overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-accent-500 rounded-full transition-all duration-500"
              style={{ width: `${translationResult?.progress || 0}%` }}
            />
          </div>
        </div>
      )}

      <div className="flex-1 flex min-h-0 relative">

        {/* PC TOC Sidebar */}
        {(showToc || tocPinned) && (
          <div className="hidden lg:block w-48 flex-shrink-0 overflow-y-auto py-4 border-r border-surface-200/50 dark:border-surface-700/30 overscroll-contain">
            {documentContent && (
              <TOC
                content={documentContent.original_text || ""}
                onNavigate={(id) => handleTocNavigate(id, "left")}
              />
            )}
            {translationResult?.translatedContent && (
              <div className="mt-6 pt-4 border-t border-surface-200/50 dark:border-surface-700/30">
                <TOC
                  content={translationResult.translatedContent || ""}
                  onNavigate={(id) => handleTocNavigate(id, "right")}
                />
              </div>
            )}
          </div>
        )}

        {/* Mobile TOC Drawer */}
        {mobileTocOpen && (
          <div className="lg:hidden fixed inset-0 z-40 flex">
            <div
              className="absolute inset-0 bg-black/30 backdrop-blur-sm"
              onClick={() => setMobileTocOpen(false)}
            />
            <div className="relative z-10 w-72 max-w-[80vw] h-full bg-white dark:bg-surface-900 shadow-modal overflow-y-auto overscroll-contain animate-slide-in-left">
              <div className="flex items-center justify-between px-4 py-3 border-b border-surface-200/50 dark:border-surface-700/30">
                <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100">目录</h3>
                <Button variant="icon" onClick={() => setMobileTocOpen(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              <div className="p-4">
                {documentContent && (
                  <TOC
                    content={documentContent.original_text || ""}
                    onNavigate={(id) => handleTocNavigate(id, hasTranslation ? (mobileTab === "translation" ? "right" : "left") : "left")}
                  />
                )}
              </div>
            </div>
          </div>
        )}

        {/* Content Panels */}
        <div className="flex-1 flex min-h-0">

          {/* Left/Original Panel */}
          <div className={cn(
            "flex-1 min-w-0 flex flex-col min-h-0",
            !hasTranslation ? "flex" : mobileTab === "original" ? "flex" : "hidden lg:flex"
          )}>
            <div
              ref={leftRef}
              onScroll={() => handleScroll("left")}
              className="flex-1 min-h-0 overflow-y-auto px-4 lg:px-6 py-4 reader-panel overscroll-contain lg:border-r border-surface-200/50 dark:border-surface-700/30"
            >
              <div className="hidden lg:flex items-center gap-2 mb-4 pb-3 border-b border-surface-100 dark:border-surface-800">
                <span className="badge-primary text-xs">原文</span>
                <span className="text-xs text-surface-400">EN</span>
              </div>
              {documentLoading ? (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 text-surface-400 gap-3">
                  <Loader2 className="w-8 h-8 animate-spin text-accent-500" />
                  <p>正在加载文档...</p>
                </div>
              ) : documentError ? (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 gap-3 p-8">
                  <div className="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-rose-500" />
                  </div>
                  <p className="text-sm text-rose-500 text-center">{documentError}</p>
                </div>
              ) : translationResult ? (
                <DocumentView
                  content={translationResult.originalContent || ""}
                  fontSize={readerSettings.fontSize}
                  lineHeight={readerSettings.lineHeight}
                />
              ) : (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 text-surface-400 gap-3">
                  <BookOpen className="w-8 h-8" />
                  <p>选择文件或点击"AI 翻译"开始</p>
                </div>
              )}
            </div>
          </div>

          {/* Right/Translation Panel */}
          <div className={cn(
            "flex-1 min-w-0 flex flex-col min-h-0",
            !hasTranslation ? "hidden lg:flex" : mobileTab === "translation" ? "flex" : "hidden lg:flex"
          )}>
            <div
              ref={rightRef}
              onScroll={() => handleScroll("right")}
              className="flex-1 min-h-0 overflow-y-auto px-4 lg:px-6 py-4 reader-panel overscroll-contain"
            >
              <div className="hidden lg:flex items-center gap-2 mb-4 pb-3 border-b border-surface-100 dark:border-surface-800">
                {translationResult?.status === "translating" ? (
                  <>
                    <span className="badge-primary text-xs">翻译中</span>
                    <span className="text-xs text-surface-400">{translationResult?.progress || 0}%</span>
                  </>
                ) : (
                  <>
                    <span className="badge-success text-xs">翻译</span>
                    <span className="text-xs text-surface-400">ZH-CN</span>
                  </>
                )}
              </div>
              {translationResult?.status === "error" ? (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 gap-3 p-8">
                  <div className="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-rose-500" />
                  </div>
                  <p className="text-sm text-rose-500 text-center">翻译失败，请重试</p>
                  <button onClick={handleStartTranslate} className="text-xs text-accent-500 hover:underline">
                    点击重新翻译
                  </button>
                </div>
              ) : translationResult?.status === "pending" || !translationResult?.translatedContent ? (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 gap-4">
                  <div className="w-12 h-12 rounded-xl bg-accent-50 dark:bg-accent-500/10 flex items-center justify-center">
                    <Languages className="w-6 h-6 text-accent-500" />
                  </div>
                  <p className="text-sm text-surface-400">点击上方「AI 翻译」按钮获取翻译结果</p>
                  <button
                    onClick={handleStartTranslate}
                    className="px-4 py-2 rounded-lg bg-accent-500 text-white text-sm font-medium hover:bg-accent-600 transition-colors shadow-soft"
                  >
                    <Languages className="w-4 h-4 inline mr-1.5" />
                    开始 AI 翻译
                  </button>
                </div>
              ) : translationResult ? (
                <DocumentView
                  content={translationResult.translatedContent || ""}
                  fontSize={readerSettings.fontSize}
                  lineHeight={readerSettings.lineHeight}
                />
              ) : (
                <div className="flex flex-col items-center justify-center flex-1 min-h-0 text-surface-400 gap-3">
                  <Languages className="w-8 h-8" />
                  <p>点击上方"AI 翻译"按钮开始翻译</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile bottom bar */}
      {!hasTranslation && !documentLoading && !documentError && (
        <div className="lg:hidden px-4 py-3 border-t border-surface-200/50 dark:border-surface-700/30 flex-shrink-0 bg-surface-50/80 dark:bg-surface-900/80 backdrop-blur-sm">
          <Button
            variant="primary"
            className="w-full"
            onClick={handleStartTranslate}
            disabled={isTranslating || !activeFileId}
          >
            {isTranslating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                AI 翻译中...
              </>
            ) : (
              <>
                <Languages className="w-4 h-4" />
                开始 AI 翻译
              </>
            )}
          </Button>
        </div>
      )}

      <ExportModal
        open={exportModalOpen}
        onClose={() => setExportModalOpen(false)}
        projectId={useAppStore.getState().activeProjectId}
        docId={activeFileId}
      />

    </div>
  )
}