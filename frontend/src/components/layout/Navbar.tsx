"use client"

import React from "react"
import {
  Menu,
  Sun,
  Moon,
  Monitor,
  Search,
  Bell,
  Settings,
  ChevronDown,
  BookOpen,
  Coins,
  Trash2,
} from "lucide-react"
import { useAppStore } from "@/store"
import { useTheme } from "@/hooks"
import { Button } from "@/components/ui"

export function Navbar() {
  const { theme, setTheme, mounted } = useTheme()
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)
  const setSettingsPanelOpen = useAppStore((s) => s.setSettingsPanelOpen)
  const setBatchDialogOpen = useAppStore((s) => s.setBatchDialogOpen)
  const setCleanupDialogOpen = useAppStore((s) => s.setCleanupDialogOpen)
  const setTokenDialogOpen = useAppStore((s) => s.setTokenDialogOpen)
  const setSearchDialogOpen = useAppStore((s) => s.setSearchDialogOpen)
  const activeProject = useAppStore((s) =>
    s.projects.find((p) => p.id === s.activeProjectId)
  )
  const [notifCount, setNotifCount] = React.useState(0)

  const cycleTheme = () => {
    const themes: Array<"light" | "dark" | "system"> = ["light", "dark", "system"]
    const idx = themes.indexOf(theme)
    setTheme(themes[(idx + 1) % themes.length])
  }

  const themeIcon = !mounted ? (
    <Monitor className="w-4 h-4" />
  ) : theme === "dark" ? (
    <Moon className="w-4 h-4" />
  ) : theme === "light" ? (
    <Sun className="w-4 h-4" />
  ) : (
    <Monitor className="w-4 h-4" />
  )

  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-[rgb(var(--background))]/80 backdrop-blur-md border-b border-surface-200/50 dark:border-surface-700/30">
      <div className="flex items-center justify-between px-3 lg:px-4 h-11 lg:h-12">
        <div className="flex items-center gap-2 lg:gap-3">
          <Button variant="icon" onClick={toggleSidebar} aria-label="Toggle sidebar" className="lg:flex">
            <Menu className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-2 lg:gap-2.5">
            <div className="w-6 h-6 lg:w-7 lg:h-7 rounded-lg bg-accent-500 flex items-center justify-center">
              <BookOpen className="w-3.5 h-3.5 lg:w-4 lg:h-4 text-white" />
            </div>
            <span className="font-semibold text-xs lg:text-sm text-surface-900 dark:text-surface-100">
              PaperLens
            </span>
          </div>
          {activeProject && (
            <>
              <div className="w-px h-5 bg-surface-200 dark:bg-surface-700 hidden sm:block" />
              <span className="text-xs lg:text-sm text-surface-600 dark:text-surface-400 hidden sm:block truncate max-w-[120px] lg:max-w-[300px]">
                {activeProject.name}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-0.5 lg:gap-1.5">
          <div className="relative hidden lg:block">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
            <button
              onClick={() => setSearchDialogOpen(true)}
              className="w-48 pl-8 pr-3 py-1.5 rounded-lg text-xs bg-surface-100 dark:bg-surface-800 border-none text-surface-400 hover:bg-surface-200 dark:hover:bg-surface-700 transition-all text-left cursor-pointer"
            >
              Ctrl+K 搜索...
            </button>
          </div>

          <Button variant="icon" onClick={() => setSearchDialogOpen(true)} className="lg:hidden" aria-label="搜索">
            <Search className="w-4 h-4" />
          </Button>

          <Button variant="icon" onClick={() => setCleanupDialogOpen(true)} aria-label="清理存储" className="hidden sm:flex">
            <Trash2 className="w-4 h-4" />
          </Button>

          <Button variant="icon" onClick={() => setTokenDialogOpen(true)} aria-label="Token用量" className="hidden sm:flex">
            <Coins className="w-4 h-4" />
          </Button>

          <Button variant="icon" onClick={cycleTheme} aria-label="Toggle theme" className="hidden sm:flex">
            {themeIcon}
          </Button>

          <Button variant="icon" onClick={() => setNotifCount(0)} aria-label="Notifications" className="hidden sm:flex relative">
            <Bell className="w-4 h-4" />
            {notifCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-rose-500 text-white text-2xs flex items-center justify-center font-medium">
                {notifCount}
              </span>
            )}
          </Button>

          <Button
            variant="icon"
            onClick={() => setSettingsPanelOpen(true)}
            aria-label="Settings"
          >
            <Settings className="w-4 h-4" />
          </Button>

          <div className="w-px h-5 bg-surface-200 dark:bg-surface-700 mx-1" />

          <button className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800/60 transition-colors">
            <div className="w-6 h-6 rounded-full bg-accent-500/10 flex items-center justify-center">
              <span className="text-xs font-medium text-accent-600 dark:text-accent-400">
                U
              </span>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-surface-400" />
          </button>
        </div>
      </div>
    </header>
  )
}
