"use client"

import React, { useState } from "react"
import { BookmarkPlus, X, Plus, BookMarked } from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button, Card } from "@/components/ui"
import { generateId } from "@/lib/utils"
import type { GlossaryTerm } from "@/types"

export function GlossaryDialog() {
  const glossaryDialogOpen = useAppStore((s) => s.glossaryDialogOpen)
  const setGlossaryDialogOpen = useAppStore((s) => s.setGlossaryDialogOpen)
  const glossary = useAppStore((s) => s.glossary)
  const addGlossaryTerm = useAppStore((s) => s.addGlossaryTerm)
  const removeGlossaryTerm = useAppStore((s) => s.removeGlossaryTerm)

  const [source, setSource] = useState("")
  const [target, setTarget] = useState("")
  const [context, setContext] = useState("")

  const handleAdd = () => {
    if (!source.trim() || !target.trim()) return
    addGlossaryTerm({
      id: generateId(),
      source: source.trim(),
      target: target.trim(),
      context: context.trim() || undefined,
    })
    setSource("")
    setTarget("")
    setContext("")
  }

  return (
    <Dialog
      open={glossaryDialogOpen}
      onClose={() => setGlossaryDialogOpen(false)}
      title="翻译术语库"
      className="max-w-xl"
    >
      <div className="space-y-4">
        <Card className="p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-surface-500 mb-1">
                原文
              </label>
              <input
                className="input-field"
                placeholder="输入原文术语"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-surface-500 mb-1">
                译文
              </label>
              <input
                className="input-field"
                placeholder="输入翻译术语"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-surface-500 mb-1">
              上下文（可选）
            </label>
            <input
              className="input-field"
              placeholder="例如：深度学习术语"
              value={context}
              onChange={(e) => setContext(e.target.value)}
            />
          </div>
          <Button onClick={handleAdd} disabled={!source.trim() || !target.trim()}>
            <Plus className="w-4 h-4" />
            添加术语
          </Button>
        </Card>

        {glossary.length > 0 && (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            <span className="section-title">{glossary.length} 条术语</span>
            {glossary.map((term) => (
              <div
                key={term.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-50 dark:bg-surface-800/50 group animate-slide-up"
              >
                <BookMarked className="w-4 h-4 text-accent-500" />
                <span className="text-sm font-medium text-surface-700 dark:text-surface-300 min-w-[120px]">
                  {term.source}
                </span>
                <span className="text-surface-400">→</span>
                <span className="text-sm font-medium text-surface-700 dark:text-surface-300 min-w-[120px]">
                  {term.target}
                </span>
                {term.context && (
                  <span className="text-xs text-surface-400 flex-1 truncate">
                    {term.context}
                  </span>
                )}
                <button
                  onClick={() => removeGlossaryTerm(term.id)}
                  className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-400 hover:text-rose-500 transition-all"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Dialog>
  )
}
