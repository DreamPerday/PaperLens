"use client"

import React from "react"
import {
  Download,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  Languages,
  Database,
  DollarSign,
} from "lucide-react"
import { useAppStore } from "@/store"
import { cn, formatTokenCount, formatCost } from "@/lib/utils"

export function StatusBar() {
  const translationResult = useAppStore((s) => s.translationResult)
  const apiStats = useAppStore((s) => s.apiStats)

  const statusIcon = translationResult
    ? translationResult.status === "completed"
      ? CheckCircle2
      : translationResult.status === "translating"
      ? Loader2
      : translationResult.status === "error"
      ? XCircle
      : Clock
    : Clock

  const StatusIcon = statusIcon
  const statusText = translationResult
    ? translationResult.status === "completed"
      ? "翻译完成"
      : translationResult.status === "translating"
      ? "翻译中..."
      : translationResult.status === "error"
      ? "翻译出错"
      : "等待中"
    : "就绪"

  return (
    <footer className="glass-status fixed bottom-0 left-0 right-0 z-40 h-statusbar">
      <div className="flex items-center justify-between h-full px-4 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-surface-500 dark:text-surface-400">
            <Languages className="w-3.5 h-3.5" />
            <span>EN → ZH</span>
          </div>
          <div className="w-px h-3 bg-surface-200 dark:bg-surface-700" />
          <div className="flex items-center gap-1.5">
            {translationResult && translationResult.status === "translating" ? (
              <Loader2 className="w-3.5 h-3.5 text-accent-500 animate-spin" />
            ) : (
              <StatusIcon
                className={cn("w-3.5 h-3.5", {
                  "text-emerald-500": translationResult?.status === "completed",
                  "text-rose-500": translationResult?.status === "error",
                  "text-surface-400": !translationResult,
                })}
              />
            )}
            <span className="text-surface-500 dark:text-surface-400">
              {statusText}
            </span>
          </div>
          {translationResult?.cached && (
            <>
              <div className="w-px h-3 bg-surface-200 dark:bg-surface-700" />
              <div className="flex items-center gap-1.5 text-emerald-500">
                <Database className="w-3.5 h-3.5" />
                <span>已缓存</span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-surface-500 dark:text-surface-400">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>
              Tokens: {formatTokenCount(apiStats.totalTokens.total)}
            </span>
          </div>
          <div className="w-px h-3 bg-surface-200 dark:bg-surface-700" />
          <div className="flex items-center gap-1.5 text-accent-500">
            <DollarSign className="w-3.5 h-3.5" />
            <span>
              {formatCost(apiStats.totalTokens.cost)}
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
