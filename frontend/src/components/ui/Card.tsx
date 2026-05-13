"use client"

import React from "react"
import { cn } from "@/lib/utils"

interface CardProps {
  children: React.ReactNode
  className?: string
  hover?: boolean
}

export function Card({ children, className, hover = false }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-surface-200/60 dark:border-surface-700/30 bg-white dark:bg-surface-900 shadow-card",
        hover &&
          "hover:shadow-elevated hover:border-surface-300/60 dark:hover:border-surface-600/30 transition-all duration-200",
        className
      )}
    >
      {children}
    </div>
  )
}
