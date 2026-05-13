"use client"

import React from "react"
import { cn } from "@/lib/utils"

interface BadgeProps {
  variant?: "primary" | "success" | "warning" | "danger" | "default"
  children: React.ReactNode
  className?: string
}

const variants = {
  primary: "bg-accent-50 dark:bg-accent-500/10 text-accent-600 dark:text-accent-400",
  success:
    "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning:
    "bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400",
  danger: "bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400",
  default:
    "bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400",
}

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
