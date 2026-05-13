"use client"

import React, { useState } from "react"
import { Layers, Loader2 } from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button, Card, Badge, Progress } from "@/components/ui"

export function BatchDialog() {
  const batchDialogOpen = useAppStore((s) => s.batchDialogOpen)
  const setBatchDialogOpen = useAppStore((s) => s.setBatchDialogOpen)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const projects = useAppStore((s) => s.projects)
  const setTranslationResult = useAppStore((s) => s.setTranslationResult)

  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [currentFile, setCurrentFile] = useState("")

  const activeProject = projects.find((p) => p.id === activeProjectId)
  const untranslatedFiles = activeProject?.files.filter(
    (f) => f.status !== "translated"
  )

  const handleBatchTranslate = async () => {
    if (!untranslatedFiles || untranslatedFiles.length === 0) return
    setRunning(true)
    setProgress(0)

    const totalSteps = untranslatedFiles.length * 20
    let step = 0
    for (const file of untranslatedFiles) {
      setCurrentFile(file.name)
      for (let s = 0; s < 20; s++) {
        await new Promise((r) => setTimeout(r, 60 + Math.random() * 40))
        step++
        setProgress(Math.round((step / totalSteps) * 100))
      }
    }

    setRunning(false)
    setProgress(100)
    setCurrentFile("")
  }

  return (
    <Dialog
      open={batchDialogOpen}
      onClose={() => { if (!running) setBatchDialogOpen(false) }}
      title="批量翻译任务"
    >
      <div className="space-y-4">
        {running && (
          <div className="space-y-2 animate-fade-in">
            <div className="flex items-center justify-between text-xs text-surface-500">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-500" />
                <span>正在翻译: {currentFile}</span>
              </div>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} size="md" />
          </div>
        )}

        {untranslatedFiles && untranslatedFiles.length > 0 && !running ? (
          <div className="space-y-3">
            <p className="text-sm text-surface-600 dark:text-surface-400">
              发现 {untranslatedFiles.length} 个待翻译文件
            </p>
            {untranslatedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-50 dark:bg-surface-800/50"
              >
                <Layers className="w-4 h-4 text-surface-400" />
                <span className="flex-1 text-sm text-surface-700 dark:text-surface-300 truncate">
                  {file.name}
                </span>
                <Badge variant="warning">待翻译</Badge>
              </div>
            ))}
            <Button className="w-full" onClick={handleBatchTranslate}>
              <Layers className="w-4 h-4" />
              开始批量翻译 ({untranslatedFiles.length} 个文件)
            </Button>
          </div>
        ) : !running ? (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center">
              <Layers className="w-6 h-6 text-emerald-500" />
            </div>
            <p className="text-sm text-surface-600 dark:text-surface-400">
              所有文件已翻译完成
            </p>
          </div>
        ) : null}
      </div>
    </Dialog>
  )
}