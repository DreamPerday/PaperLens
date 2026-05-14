"use client"

import React, { useEffect, useState, useMemo } from "react"
import { BarChart3, Zap, TrendingUp, Layers, Loader2, Coins, Activity, DollarSign, Database } from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button, Badge } from "@/components/ui"
import { cn } from "@/lib/utils"

const timeRanges = [
  { key: "today", label: "今日", days: 1 },
  { key: "7d", label: "7天", days: 7 },
  { key: "30d", label: "30天", days: 30 },
  { key: "all", label: "全部", days: -1 },
] as const

function formatToken(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`
  return String(n)
}

function formatCost(cost: number): string {
  return `¥${cost.toFixed(4)}`
}

function TokenBar({ value, max, color }: { value: number; max: number; color: string }) {
  const maxBar = 50
  const barPct = maxBar > 0 ? Math.min(100, (value / maxBar) * 100) : 0
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex-1 h-5 rounded bg-surface-100 dark:bg-surface-800 overflow-hidden relative">
        <div
          className={`h-full rounded transition-all duration-300 ${color}`}
          style={{ width: `${barPct}%`, minWidth: value > 0 ? 3 : 0 }}
        />
      </div>
      <span className="text-2xs text-surface-400 w-14 text-right flex-shrink-0">
        {formatToken(value)}
      </span>
    </div>
  )
}

const emptyTokenData = { inputCacheMiss: 0, inputCacheHit: 0, output: 0, cost: 0, total: 0 }

export function TokenUsageDialog() {
  const tokenDialogOpen = useAppStore((s) => s.tokenDialogOpen)
  const setTokenDialogOpen = useAppStore((s) => s.setTokenDialogOpen)
  const tokenBreakdown = useAppStore((s) => s.tokenBreakdown)
  const totalTokenUsage = useAppStore((s) => s.totalTokenUsage)
  const totalTokenCost = useAppStore((s) => s.totalTokenCost)
  const tokenLoading = useAppStore((s) => s.tokenLoading)
  const loadTokenStats = useAppStore((s) => s.loadTokenStats)
  const tokenHistory = useAppStore((s) => s.tokenHistory)
  const tokenHistoryLoading = useAppStore((s) => s.tokenHistoryLoading)
  const loadTokenHistory = useAppStore((s) => s.loadTokenHistory)

  const [timeRange, setTimeRange] = useState<"today" | "7d" | "30d" | "all">("all")
  const [subTab, setSubTab] = useState<"breakdown" | "history">("breakdown")

  useEffect(() => {
    if (tokenDialogOpen) {
      loadTokenStats()
      loadTokenHistory(90)
    }
  }, [tokenDialogOpen, loadTokenStats, loadTokenHistory])

  const tokenData = useMemo(() => {
    if (timeRange === "all") {
      const total = totalTokenUsage
      const prompt = total > 0 ? Math.round(total * 0.6) : 0
      const completion = total - prompt
      return {
        inputCacheMiss: prompt,
        inputCacheHit: 0,
        output: completion,
        total,
        cost: totalTokenCost,
      }
    }
    if (!tokenHistory) return emptyTokenData
    const h = tokenHistory
    const prompt = h.total_prompt_tokens || 0
    const completion = h.total_completion_tokens || 0
    const cached = h.total_cached_tokens || 0
    const total = h.total_tokens || (prompt + completion)
    const cacheMiss = Math.max(0, prompt - cached)
    const cost = (cached / 1_000_000) * 0.02 + (cacheMiss / 1_000_000) * 1.0 + (completion / 1_000_000) * 2.0
    return {
      inputCacheMiss: cacheMiss,
      inputCacheHit: cached,
      output: completion,
      total,
      cost: Math.round(cost * 1_000_000) / 1_000_000,
    }
  }, [timeRange, totalTokenUsage, totalTokenCost, tokenHistory])

  const handleTimeRangeChange = (key: "today" | "7d" | "30d" | "all") => {
    setTimeRange(key)
    if (key !== "all") {
      const r = timeRanges.find((t) => t.key === key)
      if (r && r.days > 0) loadTokenHistory(r.days)
    }
  }

  const maxTokens = useMemo(() => {
    if (!tokenBreakdown || tokenBreakdown.length === 0) return 1
    return Math.max(...tokenBreakdown.map((p) => p.tokens_used), 1)
  }, [tokenBreakdown])

  const totalDocs = useMemo(
    () => (tokenBreakdown || []).reduce((s, p) => s + p.document_count, 0),
    [tokenBreakdown]
  )
  const totalTrans = useMemo(
    () => (tokenBreakdown || []).reduce((s, p) => s + p.translation_count, 0),
    [tokenBreakdown]
  )

  return (
    <Dialog open={tokenDialogOpen} onClose={() => setTokenDialogOpen(false)} className="!max-w-xl">
      <div className="flex flex-col max-h-[600px]">
        <div className="flex items-center gap-3 px-2 py-3 border-b border-surface-200/50 dark:border-surface-700/30">
          <BarChart3 className="w-5 h-5 text-accent-500 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100">Token 用量统计</h3>
            <p className="text-xs text-surface-400">查看所有项目的翻译Token消耗详情</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain">
          {tokenLoading && (
            <div className="flex items-center justify-center py-12 gap-2 text-surface-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">加载中...</span>
            </div>
          )}

          {!tokenLoading && (
            <div className="p-4">
              <div className="flex gap-1 mb-3">
                {timeRanges.map((r) => (
                  <button
                    key={r.key}
                    onClick={() => handleTimeRangeChange(r.key)}
                    className={cn(
                      "px-2.5 py-1 rounded-md text-xs font-medium transition-all",
                      timeRange === r.key
                        ? "bg-accent-500 text-white"
                        : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800"
                    )}
                  >
                    {r.label}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/40 dark:border-surface-700/30">
                  <div className="flex items-center gap-1 text-surface-400 mb-0.5">
                    <Zap className="w-3 h-3" />
                    <span className="text-2xs">输入（未命中）</span>
                  </div>
                  <span className="block text-base font-semibold text-surface-900 dark:text-surface-100">
                    {formatToken(tokenData.inputCacheMiss)}
                  </span>
                  <div className="text-2xs text-surface-400">¥1.00/百万 tokens</div>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/40 dark:border-surface-700/30">
                  <div className="flex items-center gap-1 text-surface-400 mb-0.5">
                    <Database className="w-3 h-3" />
                    <span className="text-2xs">输入（缓存命中）</span>
                  </div>
                  <span className="block text-base font-semibold text-emerald-500">
                    {formatToken(tokenData.inputCacheHit)}
                  </span>
                  <div className="text-2xs text-surface-400">¥0.02/百万 tokens</div>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/40 dark:border-surface-700/30">
                  <div className="flex items-center gap-1 text-surface-400 mb-0.5">
                    <TrendingUp className="w-3 h-3" />
                    <span className="text-2xs">输出 Tokens</span>
                  </div>
                  <span className="block text-base font-semibold text-surface-900 dark:text-surface-100">
                    {formatToken(tokenData.output)}
                  </span>
                  <div className="text-2xs text-surface-400">¥2.00/百万 tokens</div>
                </div>
                <div className="p-2.5 rounded-lg bg-gradient-to-br from-amber-50 to-amber-100/20 dark:from-amber-500/10 dark:to-amber-500/5 border border-amber-200/30 dark:border-amber-500/20">
                  <div className="flex items-center gap-1 text-amber-500 mb-0.5">
                    <DollarSign className="w-3 h-3" />
                    <span className="text-2xs">总花费</span>
                  </div>
                  <span className="block text-base font-bold text-amber-600 dark:text-amber-400">
                    {formatCost(tokenData.cost)}
                  </span>
                  <div className="text-2xs text-surface-400">预估金额</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5 mb-3">
                <div className="p-2.5 rounded-lg bg-gradient-to-br from-accent-50 to-accent-100/30 dark:from-accent-500/10 dark:to-accent-500/5 border border-accent-200/30 dark:border-accent-500/20">
                  <Coins className="w-4 h-4 text-accent-500 mb-0.5" />
                  <span className="block text-base font-bold text-surface-900 dark:text-surface-100">
                    {formatToken(tokenData.total)}
                  </span>
                  <span className="text-2xs text-surface-400">总 Tokens</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/60 dark:border-surface-700/30">
                  <Layers className="w-4 h-4 text-surface-500 mb-0.5" />
                  <span className="block text-base font-bold text-surface-900 dark:text-surface-100">{totalDocs}</span>
                  <span className="text-2xs text-surface-400">文档数</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/60 dark:border-surface-700/30">
                  <Activity className="w-4 h-4 text-surface-500 mb-0.5" />
                  <span className="block text-base font-bold text-surface-900 dark:text-surface-100">{totalTrans}</span>
                  <span className="text-2xs text-surface-400">翻译次数</span>
                </div>
                <div className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-200/60 dark:border-surface-700/30">
                  <TrendingUp className="w-4 h-4 text-surface-500 mb-0.5" />
                  <span className="block text-base font-bold text-surface-900 dark:text-surface-100">
                    {totalTrans > 0 ? formatToken(Math.round(totalTokenUsage / totalTrans)) : 0}
                  </span>
                  <span className="text-2xs text-surface-400">均/次</span>
                </div>
              </div>

              {tokenBreakdown && tokenBreakdown.length > 0 && (
                <div>
                  <div className="flex border-b border-surface-200/50 dark:border-surface-700/30 mb-3">
                    {(["breakdown", "history"] as const).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setSubTab(tab)}
                        className={cn(
                          "px-3 py-1.5 text-xs font-medium transition-colors relative",
                          subTab === tab
                            ? "text-accent-600 dark:text-accent-400"
                            : "text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
                        )}
                      >
                        {tab === "breakdown" ? "项目明细" : "历史记录"}
                        {subTab === tab && (
                          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4/5 h-0.5 bg-accent-500 rounded-full" />
                        )}
                      </button>
                    ))}
                  </div>

                  {subTab === "breakdown" && (
                    <div className="space-y-1.5">
                      {tokenBreakdown.map((p) => (
                        <div
                          key={p.project_id}
                          className="p-2.5 rounded-lg bg-surface-50 dark:bg-surface-800/50 border border-surface-100/60 dark:border-surface-800/60"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-medium text-surface-700 dark:text-surface-300 truncate pr-2">
                              {p.project_name}
                            </span>
                            <span className="text-xs font-semibold text-surface-900 dark:text-surface-100 flex-shrink-0">
                              {formatToken(p.tokens_used)}
                            </span>
                          </div>
                          <TokenBar value={p.tokens_used} max={maxTokens} color="bg-accent-500" />
                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-2xs text-surface-400">{p.document_count} 文档</span>
                            <span className="text-2xs text-surface-400">{p.translation_count} 次翻译</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {subTab === "history" && (
                    <div>
                      {tokenHistoryLoading && (
                        <div className="flex items-center justify-center py-6 gap-2 text-surface-400">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-xs">加载中...</span>
                        </div>
                      )}

                      {!tokenHistoryLoading && tokenHistory && tokenHistory.daily_summary.length > 0 && (
                        <>
                          <div className="space-y-1 mb-3">
                            {tokenHistory.daily_summary.slice(-14).map((d) => (
                              <div key={d.date} className="flex items-center gap-1.5">
                                <span className="text-2xs text-surface-400 w-12 flex-shrink-0 text-right">
                                  {d.date.slice(5)}
                                </span>
                                <TokenBar value={d.tokens} max={Math.max(...tokenHistory.daily_summary.map((d) => d.tokens), 1)} color="bg-emerald-400" />
                              </div>
                            ))}
                          </div>
                          <div className="border-t border-surface-100/60 dark:border-surface-800/40 pt-2">
                            <div className="flex items-center justify-between text-2xs text-surface-400 mb-1.5">
                              <span>历史翻译记录</span>
                              <span>{tokenHistory.total_records} 次 · {formatToken(tokenHistory.total_tokens)} Tokens</span>
                            </div>
                            <div className="max-h-40 overflow-y-auto space-y-0.5">
                              {tokenHistory.records.slice(-20).reverse().map((r, i) => (
                                <div key={i} className="flex items-center gap-2 px-2 py-1 rounded text-2xs hover:bg-surface-50/50 dark:hover:bg-surface-800/30">
                                  <span className="text-surface-300 w-16 flex-shrink-0">
                                    {new Date(r.timestamp).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
                                  </span>
                                  <span className="truncate flex-1 text-surface-600 dark:text-surface-400">{r.doc_name}</span>
                                  <span className="text-accent-500 font-medium flex-shrink-0">{formatToken(r.tokens_used)}</span>
                                  <span className="text-surface-300 flex-shrink-0">{r.paragraph_count}段</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </>
                      )}

                      {!tokenHistoryLoading && (!tokenHistory || tokenHistory.daily_summary.length === 0) && (
                        <div className="flex flex-col items-center py-6 text-center">
                          <Coins className="w-8 h-8 text-surface-300 mb-1.5" />
                          <p className="text-sm text-surface-500">暂无历史记录</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {(!tokenBreakdown || tokenBreakdown.length === 0) && (
                <div className="flex flex-col items-center py-6 text-center">
                  <Coins className="w-8 h-8 text-surface-300 mb-1.5" />
                  <p className="text-sm text-surface-500">暂无翻译记录</p>
                  <p className="text-xs text-surface-400 mt-1">开始翻译论文后将在此展示Token消耗统计</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Dialog>
  )
}