"use client"

import React, { useMemo } from "react"
import { cn } from "@/lib/utils"
import type { TocItem } from "@/types"

interface TOCProps {
  content: string
  onNavigate: (id: string) => void
  className?: string
}

export function TOC({ content, onNavigate, className }: TOCProps) {
  const tocItems: TocItem[] = useMemo(() => {
    const items: TocItem[] = []
    if (typeof content !== "string" || !content) return items

    let headingIndex = 0
    const lines = content.split("\n")
    for (const line of lines) {
      const hMatch = line.match(/^(#{1,4})\s+(.+)/)
      if (!hMatch) continue
      const level = hMatch[1].length
      const title = hMatch[2].replace(/<[^>]*>/g, "").trim()
      if (!title) continue
      if (items.some(i => i.title === title)) continue
      items.push({ id: `toc-heading-${headingIndex++}`, title, level })
    }

    return items
  }, [content])

  if (tocItems.length === 0) return null

  return (
    <div className={cn("space-y-0.5", className)}>
      <span className="section-title block px-3 pb-2">目录</span>
      {tocItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onNavigate(item.id)}
          className={cn(
            "w-full text-left px-3 py-1.5 rounded-md text-xs transition-all duration-150",
            "text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800/40",
            item.level === 1 && "font-medium",
            item.level === 2 && "pl-7",
            item.level === 3 && "pl-10 text-2xs",
            item.level === 4 && "pl-12 text-2xs"
          )}
        >
          {item.title}
        </button>
      ))}
    </div>
  )
}
