"use client"

import React, { useState, useCallback, useRef, useEffect } from "react"
import { Search, X, FileText, FolderOpen, Loader2, ArrowRight } from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button } from "@/components/ui"
import { cn } from "@/lib/utils"

export function SearchDialog() {
  const searchResults = useAppStore((s) => s.searchResults)
  const searchQuery = useAppStore((s) => s.searchQuery)
  const searchLoading = useAppStore((s) => s.searchLoading)
  const performSearch = useAppStore((s) => s.performSearch)
  const clearSearch = useAppStore((s) => s.clearSearch)
  const setActiveProject = useAppStore((s) => s.setActiveProject)
  const setActiveFile = useAppStore((s) => s.setActiveFile)
  const searchDialogOpen = useAppStore((s) => s.searchDialogOpen)
  const setSearchDialogOpen = useAppStore((s) => s.setSearchDialogOpen)

  const [input, setInput] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (searchDialogOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [searchDialogOpen])

  const handleInput = useCallback((value: string) => {
    setInput(value)
    clearTimeout(timerRef.current)
    if (value.trim().length >= 1) {
      timerRef.current = setTimeout(() => performSearch(value), 300)
    } else {
      clearSearch()
    }
  }, [performSearch, clearSearch])

  const handleNavigate = useCallback((projectId: string, docId: string) => {
    setActiveProject(projectId)
    setActiveFile(docId)
    setSearchDialogOpen(false)
  }, [setActiveProject, setActiveFile, setSearchDialogOpen])

  const handleClose = useCallback(() => {
    setSearchDialogOpen(false)
    clearSearch()
  }, [clearSearch, setSearchDialogOpen])

  return (
    <>
      <Dialog open={searchDialogOpen} onClose={handleClose} className="!max-w-lg">
        <div className="flex flex-col max-h-[420px]">
          <div className="flex items-center gap-3 px-4 py-3 border-b border-surface-200/50 dark:border-surface-700/30">
            <Search className="w-4 h-4 text-surface-400 flex-shrink-0" />
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => handleInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") handleClose()
              }}
              placeholder="搜索文档内容..."
              className="flex-1 bg-transparent border-none outline-none text-sm text-surface-900 dark:text-surface-100 placeholder:text-surface-400"
            />
            {searchLoading && <Loader2 className="w-4 h-4 animate-spin text-accent-500 flex-shrink-0" />}
            <Button variant="icon" onClick={handleClose} className="flex-shrink-0">
              <X className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto overscroll-contain">
            {searchQuery && searchResults.length === 0 && !searchLoading && (
              <div className="px-4 py-8 text-center">
                <FileText className="w-8 h-8 mx-auto mb-2 text-surface-300" />
                <p className="text-sm text-surface-500">未找到匹配结果</p>
              </div>
            )}

            {!searchQuery && (
              <div className="px-4 py-8 text-center">
                <Search className="w-8 h-8 mx-auto mb-2 text-surface-300" />
                <p className="text-sm text-surface-400">输入关键词搜索所有文档</p>
              </div>
            )}

            {searchResults.map((r, i) => (
              <button
                key={i}
                onClick={() => handleNavigate(r.project_id, r.doc_id)}
                className={cn(
                  "w-full text-left px-4 py-3 hover:bg-surface-50 dark:hover:bg-surface-800/40 transition-colors",
                  i < searchResults.length - 1 && "border-b border-surface-100/60 dark:border-surface-800/40"
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-3.5 h-3.5 text-accent-500" />
                  <span className="text-sm font-medium text-surface-900 dark:text-surface-100 truncate">
                    {r.doc_name}
                  </span>
                  <ArrowRight className="w-3 h-3 text-surface-300 ml-auto flex-shrink-0" />
                </div>
                <div className="flex items-center gap-2 mb-1">
                  <FolderOpen className="w-3 h-3 text-surface-400" />
                  <span className="text-xs text-surface-500">{r.project_name}</span>
                  <span className="badge-secondary text-2xs">{r.doc_type}</span>
                </div>
                <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed line-clamp-2 mt-1">
                  {r.snippet}
                </p>
              </button>
            ))}
          </div>

          {searchResults.length > 0 && (
            <div className="px-4 py-2 border-t border-surface-200/50 dark:border-surface-700/30 text-xs text-surface-400">
              共 {searchResults.length} 条结果
            </div>
          )}
        </div>
      </Dialog>
    </>
  )
}