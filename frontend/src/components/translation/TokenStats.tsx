"use client"

import React, { useState } from "react"
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Zap,
  RefreshCw,
  Database,
  Activity,
} from "lucide-react"
import { useAppStore } from "@/store"
import { Card, Button } from "@/components/ui"
import { formatTokenCount, formatCost } from "@/lib/utils"

const timeRanges = ["today", "7d", "30d", "all"] as const

export function TokenStats() {
  const apiStats = useAppStore((s) => s.apiStats)
  const refreshApiStats = useAppStore((s) => s.refreshApiStats)
  const [timeRange, setTimeRange] = useState<"today" | "7d" | "30d" | "all">("today")

  const tokens = timeRange === "today" ? apiStats.todayTokens : apiStats.totalTokens
  const requests = timeRange === "today" ? apiStats.todayRequests : apiStats.totalRequests

  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-accent-500" />
          <span className="text-sm font-medium text-surface-900 dark:text-surface-100">
            API 消耗统计
          </span>
        </div>
        <Button variant="ghost" size="sm" onClick={refreshApiStats}>
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      <div className="flex gap-1 mb-4">
        {timeRanges.map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
              timeRange === range
                ? "bg-accent-500 text-white"
                : "text-surface-500 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800"
            }`}
          >
            {range === "today"
              ? "今日"
              : range === "7d"
              ? "7天"
              : range === "30d"
              ? "30天"
              : "全部"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50">
          <div className="flex items-center gap-1.5 text-surface-400 mb-1">
            <Zap className="w-3.5 h-3.5" />
            <span className="text-xs">输入 (未命中)</span>
          </div>
          <span className="text-lg font-semibold text-surface-900 dark:text-surface-100">
            {formatTokenCount(tokens.inputCacheMiss)}
          </span>
          <div className="text-[10px] text-surface-400 mt-0.5">¥1/百万 tokens</div>
        </div>
        <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50">
          <div className="flex items-center gap-1.5 text-surface-400 mb-1">
            <Database className="w-3.5 h-3.5" />
            <span className="text-xs">输入 (缓存命中)</span>
          </div>
          <span className="text-lg font-semibold text-emerald-500">
            {formatTokenCount(tokens.inputCacheHit)}
          </span>
          <div className="text-[10px] text-surface-400 mt-0.5">¥0.02/百万 tokens</div>
        </div>
        <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50">
          <div className="flex items-center gap-1.5 text-surface-400 mb-1">
            <TrendingUp className="w-3.5 h-3.5" />
            <span className="text-xs">输出 Tokens</span>
          </div>
          <span className="text-lg font-semibold text-surface-900 dark:text-surface-100">
            {formatTokenCount(tokens.output)}
          </span>
          <div className="text-[10px] text-surface-400 mt-0.5">¥2/百万 tokens</div>
        </div>
        <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50">
          <div className="flex items-center gap-1.5 text-surface-400 mb-1">
            <DollarSign className="w-3.5 h-3.5" />
            <span className="text-xs">总花费</span>
          </div>
          <span className="text-lg font-semibold text-accent-500">
            {formatCost(tokens.cost)}
          </span>
          <div className="text-[10px] text-surface-400 mt-0.5">预估金额</div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-surface-100 dark:border-surface-800">
        <div className="flex items-center justify-between text-xs">
          <span className="text-surface-400">总消耗</span>
          <span className="text-surface-600 dark:text-surface-300 font-medium">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3 h-3" />
              {formatTokenCount(apiStats.totalTokens.total)} tokens
            </span>
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-1">
          <span className="text-surface-400">预估总费用</span>
          <span className="text-accent-500 font-medium">
            {formatCost(apiStats.totalTokens.cost)}
          </span>
        </div>
      </div>
    </Card>
  )
}