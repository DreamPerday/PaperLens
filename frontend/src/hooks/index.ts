"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { useAppStore } from "@/store"

export function useTheme() {
  const theme = useAppStore((s) => s.theme)
  const setTheme = useAppStore((s) => s.setTheme)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return
    const root = document.documentElement
    if (theme === "dark") {
      root.classList.add("dark")
    } else if (theme === "light") {
      root.classList.remove("dark")
    } else {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")
      if (mediaQuery.matches) {
        root.classList.add("dark")
      } else {
        root.classList.remove("dark")
      }
      const handler = (e: MediaQueryListEvent) => {
        if (theme === "system") {
          if (e.matches) root.classList.add("dark")
          else root.classList.remove("dark")
        }
      }
      mediaQuery.addEventListener("change", handler)
      return () => mediaQuery.removeEventListener("change", handler)
    }
  }, [theme, mounted])

  return { theme, setTheme, mounted }
}

export function useSyncScroll(
  leftRef: React.RefObject<HTMLDivElement | null>,
  rightRef: React.RefObject<HTMLDivElement | null>,
  enabled: boolean = true
) {
  const isProgrammatic = useRef(false)

  const handleScroll = useCallback(
    (source: "left" | "right") => {
      if (!enabled || isProgrammatic.current) return
      isProgrammatic.current = true

      const sourceEl = source === "left" ? leftRef.current : rightRef.current
      const targetEl = source === "left" ? rightRef.current : leftRef.current
      if (!sourceEl || !targetEl) {
        isProgrammatic.current = false
        return
      }

      const sourceRatio =
        sourceEl.scrollTop / (sourceEl.scrollHeight - sourceEl.clientHeight)
      targetEl.scrollTop =
        sourceRatio * (targetEl.scrollHeight - targetEl.clientHeight)

      requestAnimationFrame(() => {
        isProgrammatic.current = false
      })
    },
    [enabled, leftRef, rightRef]
  )

  return { handleScroll }
}

export function useAutoSave(key: string, data: unknown, delay: number = 2000) {
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(data))
      } catch {
      }
    }, delay)
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [key, data, delay])
}

export function useKeyboard() {
  useEffect(() => {
    const store = useAppStore.getState()
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "b") {
        e.preventDefault()
        store.toggleSidebar()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "u") {
        e.preventDefault()
        store.setUploadDialogOpen(true)
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        store.setSearchDialogOpen(true)
      }
      if (e.key === "Escape") {
        store.setSettingsPanelOpen(false)
        store.setUploadDialogOpen(false)
        store.setGlossaryDialogOpen(false)
        store.setBatchDialogOpen(false)
        store.setSearchDialogOpen(false)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])
}
