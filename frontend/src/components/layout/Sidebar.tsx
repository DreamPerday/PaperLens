"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import {
  FileText,
  Plus,
  Trash2,
  ChevronRight,
  ChevronDown,
  File,
  MoreHorizontal,
  FolderOpen,
  Upload,
  Edit3,
} from "lucide-react"
import { useAppStore } from "@/store"
import { cn, formatFileSize, getFileColor } from "@/lib/utils"
import type { Project, PaperFile } from "@/types"
import { Button } from "@/components/ui"

function ContextMenu({
  x,
  y,
  onClose,
  items,
}: {
  x: number
  y: number
  onClose: () => void
  items: { label: string; icon?: React.ReactNode; action: () => void; danger?: boolean }[]
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose()
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("mousedown", handleClick)
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.removeEventListener("mousedown", handleClick)
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [onClose])

  const menuStyle: React.CSSProperties = {
    position: "fixed",
    left: x,
    top: y,
    zIndex: 9999,
  }

  return (
    <div
      ref={ref}
      style={menuStyle}
      className="min-w-[160px] py-1 rounded-xl border border-surface-200/50 dark:border-surface-700/30 bg-white dark:bg-surface-900 shadow-elevated animate-fade-in"
    >
      {items.map((item, i) => (
        <button
          key={i}
          onClick={() => { item.action(); onClose() }}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-1.5 text-sm transition-colors",
            item.danger
              ? "text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10"
              : "text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800/60"
          )}
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  )
}

function FileItem({
  file,
  isActive,
  onClick,
  onDelete,
  onRename,
}: {
  file: PaperFile
  isActive: boolean
  onClick: () => void
  onDelete: () => void
  onRename: (newName: string) => void
}) {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState(file.name)
  const renameInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (renaming && renameInputRef.current) {
      renameInputRef.current.focus()
      const dotIdx = file.name.lastIndexOf(".")
      if (dotIdx > 0) {
        renameInputRef.current.setSelectionRange(0, dotIdx)
      } else {
        renameInputRef.current.select()
      }
    }
  }, [renaming, file.name])

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const handleRenameSubmit = useCallback(() => {
    const trimmed = (renameValue || "").trim()
    if (trimmed && trimmed !== file.name) {
      onRename(trimmed)
    }
    setRenaming(false)
  }, [renameValue, file.name, onRename])

  const handleRenameKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleRenameSubmit()
    } else if (e.key === "Escape") {
      setRenaming(false)
      setRenameValue(file.name)
    }
  }, [handleRenameSubmit, file.name])

  return (
    <div className="flex items-center gap-1 group" onContextMenu={handleContextMenu}>
      <button
        onClick={onClick}
        className={cn(
          "flex-1 flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150",
          isActive
            ? "bg-accent-50 dark:bg-accent-500/10 text-accent-600 dark:text-accent-400"
            : "text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-800/40"
        )}
      >
        <File className={cn("w-4 h-4 flex-shrink-0", getFileColor(file.type))} />
        {renaming ? (
          <input
            ref={renameInputRef}
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onBlur={handleRenameSubmit}
            onKeyDown={handleRenameKeyDown}
            onClick={(e) => e.stopPropagation()}
            className="flex-1 min-w-0 bg-transparent border-b border-accent-400 outline-none text-sm text-surface-900 dark:text-surface-100"
          />
        ) : (
          <span className="flex-1 text-left truncate">{file.name}</span>
        )}
        <span className="text-2xs text-surface-400 hidden group-hover:block">
          {formatFileSize(file.size)}
        </span>
      </button>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          items={[
            {
              label: "重命名",
              icon: <Edit3 className="w-3.5 h-3.5" />,
              action: () => {
                setRenaming(true)
                setRenameValue(file.name)
              },
            },
            {
              label: "删除",
              icon: <Trash2 className="w-3.5 h-3.5" />,
              action: onDelete,
              danger: true,
            },
          ]}
        />
      )}
    </div>
  )
}

function ProjectItem({
  project,
  isActive,
  onClick,
  onDelete,
  onDeleteFile,
  onRenameFile,
}: {
  project: Project
  isActive: boolean
  onClick: () => void
  onDelete: () => void
  onDeleteFile: (fileId: string) => void
  onRenameFile: (fileId: string, newName: string) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const setActiveFile = useAppStore((s) => s.setActiveFile)
  const activeFileId = useAppStore((s) => s.activeFileId)

  return (
    <div className="animate-fade-in">
      <div className="flex items-center gap-1 group">
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-0.5 rounded hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-400"
        >
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </button>
        <button
          onClick={onClick}
          className={cn(
            "flex-1 flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-all duration-150",
            isActive
              ? "bg-accent-50 dark:bg-accent-500/10 text-accent-600 dark:text-accent-400 font-medium"
              : "text-surface-700 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800/40"
          )}
        >
          <FolderOpen
            className={cn(
              "w-4 h-4 flex-shrink-0",
              isActive
                ? "text-accent-500"
                : "text-surface-400 dark:text-surface-500"
            )}
          />
          <span className="truncate">{project.name}</span>
        </button>
        <Button
          variant="icon"
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10"
          aria-label="Delete project"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>

      {expanded && project.files && project.files.length > 0 && (
        <div className="ml-5 mt-1 space-y-0.5">
          {(project.files || []).map((file) => (
            <FileItem
              key={file.id}
              file={file}
              isActive={file.id === activeFileId}
              onClick={() => setActiveFile(file.id)}
              onDelete={() => onDeleteFile(file.id)}
              onRename={(newName) => onRenameFile(file.id, newName)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const projects = useAppStore((s) => s.projects)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const setActiveProject = useAppStore((s) => s.setActiveProject)
  const deleteProject = useAppStore((s) => s.deleteProject)
  const deleteFile = useAppStore((s) => s.deleteFile)
  const renameFile = useAppStore((s) => s.renameFile)
  const setUploadDialogOpen = useAppStore((s) => s.setUploadDialogOpen)
  const addProject = useAppStore((s) => s.addProject)

  if (!sidebarOpen) return null

  const handleDeleteFile = (fileId: string) => {
    if (activeProjectId) {
      deleteFile(activeProjectId, fileId)
    }
  }

  const handleRenameFile = (fileId: string, newName: string) => {
    if (activeProjectId) {
      renameFile(activeProjectId, fileId, newName)
    }
  }

  return (
    <aside className="glass-sidebar fixed left-0 top-navbar bottom-statusbar w-sidebar z-30 flex flex-col animate-fade-in">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="section-title">项目列表</span>
        <div className="flex items-center gap-0.5">
          <Button
            variant="icon"
            onClick={() => setUploadDialogOpen(true)}
            aria-label="Upload files"
          >
            <Upload className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="icon"
            onClick={() => addProject("新建项目")}
            aria-label="New project"
          >
            <Plus className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
        {projects.map((project) => (
          <ProjectItem
            key={project.id}
            project={project}
            isActive={project.id === activeProjectId}
            onClick={() => setActiveProject(project.id)}
            onDelete={() => deleteProject(project.id)}
            onDeleteFile={handleDeleteFile}
            onRenameFile={handleRenameFile}
          />
        ))}
      </div>

      <div className="px-4 py-3 border-t border-surface-200/50 dark:border-surface-800/50">
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="flex-1"
            onClick={() => setUploadDialogOpen(true)}
          >
            <Upload className="w-3.5 h-3.5" />
            上传文件
          </Button>
        </div>
      </div>
    </aside>
  )
}
