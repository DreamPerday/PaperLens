"use client"

import React from "react"

interface ProgressProps {
  value: number
  className?: string
  size?: "sm" | "md"
  showLabel?: boolean
}

export function Progress({ value, className = "", size = "sm", showLabel = false }: ProgressProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100)

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`flex-1 rounded-full bg-surface-100 dark:bg-surface-800 overflow-hidden ${
          size === "sm" ? "h-1" : "h-2"
        }`}
      >
        <div
          className="h-full rounded-full bg-accent-500 transition-all duration-500 ease-out"
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-surface-500 dark:text-surface-400 min-w-[3ch] text-right tabular-nums">
          {Math.round(clampedValue)}%
        </span>
      )}
    </div>
  )
}
