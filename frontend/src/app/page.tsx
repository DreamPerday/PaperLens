"use client"

import React, { useEffect } from "react"
import { useAppStore } from "@/store"
import { useKeyboard } from "@/hooks"
import { Navbar } from "@/components/layout/Navbar"
import { Sidebar } from "@/components/layout/Sidebar"
import { StatusBar } from "@/components/layout/StatusBar"
import { DualPaneReader } from "@/components/reader"
import { SettingsPanel } from "@/components/settings"
import { FileUploadDialog } from "@/components/upload"
import { GlossaryDialog, TokenStats, BatchDialog, SearchDialog, CleanupDialog, TokenUsageDialog } from "@/components/translation"
import { cn } from "@/lib/utils"

export default function Home() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const loadProjects = useAppStore((s) => s.loadProjects)
  const refreshApiStats = useAppStore((s) => s.refreshApiStats)

  useKeyboard()

  useEffect(() => {
    console.log(`[PAGE] Initializing - loading projects and stats...`)
    loadProjects()
    refreshApiStats()
  }, [loadProjects, refreshApiStats])

  return (
    <div className="h-screen overflow-hidden bg-[rgb(var(--background))] overscroll-none">
      <Navbar />

      <div className="flex" style={{
        height: "100vh",
        paddingTop: "44px",
        paddingBottom: "36px",
        boxSizing: "border-box",
      }}>
        <Sidebar />

        <main
          className={cn(
            "flex-1 flex flex-col min-h-0 max-w-full overflow-hidden transition-all duration-300",
            sidebarOpen ? "lg:ml-sidebar" : "ml-0"
          )}
        >
          <DualPaneReader />
        </main>
      </div>

      <StatusBar />
      <SettingsPanel />
      <FileUploadDialog />
      <GlossaryDialog />
      <BatchDialog />
      <SearchDialog />
      <CleanupDialog />
      <TokenUsageDialog />
    </div>
  )
}
