"use client"

import React, { useEffect, useState, useCallback, useMemo } from "react"
import {
  Trash2, FileWarning, Image, Loader2, HardDrive, CheckCircle,
  FileText, ChevronDown, ChevronRight, CheckSquare, Square,
} from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button } from "@/components/ui"
import { formatFileSize, cn } from "@/lib/utils"

interface FileEntry {
  name: string
  path: string
  size: number
  mtime: number
}

function SectionHeader({
  label, icon: Icon, count, totalSize, expanded, onToggle,
  allChecked, someChecked, onCheckAll,
}: {
  label: string
  icon: React.ElementType
  count: number
  totalSize: number
  expanded: boolean
  onToggle: () => void
  allChecked: boolean
  someChecked: boolean
  onCheckAll: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-2 px-3 py-2 hover:bg-surface-50 dark:hover:bg-surface-800/40 rounded-lg transition-colors group"
    >
      <span onClick={(e) => { e.stopPropagation(); onCheckAll() }} className="flex-shrink-0 cursor-pointer">
        {allChecked ? (
          <CheckSquare className="w-4 h-4 text-accent-500" />
        ) : someChecked ? (
          <div className="w-4 h-4 flex items-center justify-center">
            <div className="w-2.5 h-2.5 rounded-sm bg-accent-400" />
          </div>
        ) : (
          <Square className="w-4 h-4 text-surface-400" />
        )}
      </span>
      {expanded ? (
        <ChevronDown className="w-3.5 h-3.5 text-surface-400" />
      ) : (
        <ChevronRight className="w-3.5 h-3.5 text-surface-400" />
      )}
      <Icon className="w-3.5 h-3.5 text-surface-500 flex-shrink-0" />
      <span className="text-xs font-medium text-surface-700 dark:text-surface-300">{label}</span>
      <span className="text-xs text-surface-400 ml-auto flex-shrink-0">
        {count} 个 · {formatFileSize(totalSize)}
      </span>
    </button>
  )
}

function FileRow({
  entry, checked, onToggle,
}: {
  entry: FileEntry
  checked: boolean
  onToggle: () => void
}) {
  const mtimeStr = new Date(entry.mtime * 1000).toLocaleDateString("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  })

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-2xs hover:bg-surface-50/50 dark:hover:bg-surface-800/30 rounded transition-colors">
      <span onClick={onToggle} className="flex-shrink-0 cursor-pointer">
        {checked ? (
          <CheckSquare className="w-3.5 h-3.5 text-accent-500" />
        ) : (
          <Square className="w-3.5 h-3.5 text-surface-400" />
        )}
      </span>
      <span className="truncate flex-1 text-surface-600 dark:text-surface-400">{entry.name}</span>
      <span className="text-surface-400 flex-shrink-0 ml-1">{formatFileSize(entry.size)}</span>
      <span className="text-surface-300 flex-shrink-0 w-16 text-right">{mtimeStr}</span>
    </div>
  )
}

export function CleanupDialog() {
  const cleanupDialogOpen = useAppStore((s) => s.cleanupDialogOpen)
  const setCleanupDialogOpen = useAppStore((s) => s.setCleanupDialogOpen)
  const orphanData = useAppStore((s) => s.orphanData)
  const orphanLoading = useAppStore((s) => s.orphanLoading)
  const loadOrphanData = useAppStore((s) => s.loadOrphanData)
  const deleteSelectedOrphans = useAppStore((s) => s.deleteSelectedOrphans)

  const [checkedPaths, setCheckedPaths] = useState<Set<string>>(new Set())
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["orphan-uploads", "cache-files", "orphan-images"])
  )

  useEffect(() => {
    if (cleanupDialogOpen) {
      loadOrphanData()
    }
  }, [cleanupDialogOpen, loadOrphanData])

  useEffect(() => {
    if (!orphanData) return
    const paths = new Set<string>()
    for (const f of orphanData.orphan_uploads) paths.add(f.path)
    for (const f of orphanData.cache_files) paths.add(f.path)
    for (const f of orphanData.orphan_images) paths.add(f.path)
    setCheckedPaths(paths)
  }, [orphanData])

  const toggleSection = useCallback((name: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  const toggleFile = useCallback((path: string) => {
    setCheckedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }, [])

  const toggleAllInSection = useCallback((entries: FileEntry[]) => {
    setCheckedPaths((prev) => {
      const next = new Set(prev)
      const paths = entries.map((e) => e.path)
      const allChecked = paths.every((p) => next.has(p))
      if (allChecked) {
        for (const p of paths) next.delete(p)
      } else {
        for (const p of paths) next.add(p)
      }
      return next
    })
  }, [])

  const handleDelete = useCallback(async () => {
    if (checkedPaths.size === 0) return
    await deleteSelectedOrphans(Array.from(checkedPaths))
  }, [checkedPaths, deleteSelectedOrphans])

  const sectionState = useCallback(
    (entries: FileEntry[]) => {
      if (entries.length === 0) return { all: false, some: false, totalSize: 0 }
      const paths = entries.map((e) => e.path)
      const checked = paths.filter((p) => checkedPaths.has(p))
      const totalSize = entries.reduce((s, e) => s + e.size, 0)
      return {
        all: checked.length === entries.length,
        some: checked.length > 0 && checked.length < entries.length,
        totalSize,
      }
    },
    [checkedPaths]
  )

  const orphanUploads = orphanData?.orphan_uploads || []
  const cacheFiles = orphanData?.cache_files || []
  const orphanImages = orphanData?.orphan_images || []
  const inUseUploads = orphanData?.in_use_uploads || []
  const inUseImages = orphanData?.in_use_images || []

  const orphanUploadsState = sectionState(orphanUploads)
  const cacheFilesState = sectionState(cacheFiles)
  const orphanImagesState = sectionState(orphanImages)
  const inUseUploadsState = sectionState(inUseUploads)
  const inUseImagesState = sectionState(inUseImages)

  const totalSelected = checkedPaths.size
  const totalSelectedSize = useMemo(() => {
    const all = [
      ...orphanUploads, ...cacheFiles, ...orphanImages, ...inUseUploads, ...inUseImages,
    ]
    return all.filter((f) => checkedPaths.has(f.path)).reduce((s, f) => s + f.size, 0)
  }, [checkedPaths, orphanUploads, cacheFiles, orphanImages, inUseUploads, inUseImages])

  const hasAnyFiles = orphanUploads.length + cacheFiles.length + orphanImages.length +
    inUseUploads.length + inUseImages.length > 0

  return (
    <Dialog open={cleanupDialogOpen} onClose={() => setCleanupDialogOpen(false)} className="!max-w-lg">
      <div className="flex flex-col max-h-[520px]">
        <div className="flex items-center gap-3 px-5 py-3 border-b border-surface-200/50 dark:border-surface-700/30">
          <HardDrive className="w-5 h-5 text-accent-500 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100">存储清理</h3>
            <p className="text-xs text-surface-400">勾选要删除的文件，支持分类勾选</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto overscroll-contain">
          {orphanLoading && (
            <div className="flex items-center justify-center py-10 gap-2 text-surface-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span className="text-sm">扫描中...</span>
            </div>
          )}

          {!orphanLoading && !hasAnyFiles && (
            <div className="flex flex-col items-center py-8 text-center">
              <CheckCircle className="w-10 h-10 text-emerald-400 mb-2" />
              <p className="text-sm text-surface-500">存储为空</p>
            </div>
          )}

          {!orphanLoading && hasAnyFiles && (
            <div className="py-2">
              {/* Orphan uploads - default checked */}
              {orphanUploads.length > 0 && (
                <div>
                  <SectionHeader
                    label="废弃上传文件"
                    icon={FileWarning}
                    count={orphanUploads.length}
                    totalSize={orphanUploadsState.totalSize}
                    expanded={expandedSections.has("orphan-uploads")}
                    onToggle={() => toggleSection("orphan-uploads")}
                    allChecked={orphanUploadsState.all}
                    someChecked={orphanUploadsState.some}
                    onCheckAll={() => toggleAllInSection(orphanUploads)}
                  />
                  {expandedSections.has("orphan-uploads") && (
                    <div className="ml-3 mb-1">
                      {orphanUploads.map((f) => (
                        <FileRow
                          key={f.path}
                          entry={f}
                          checked={checkedPaths.has(f.path)}
                          onToggle={() => toggleFile(f.path)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Cache files - default checked */}
              {cacheFiles.length > 0 && (
                <div>
                  <SectionHeader
                    label="解析缓存文件"
                    icon={FileText}
                    count={cacheFiles.length}
                    totalSize={cacheFilesState.totalSize}
                    expanded={expandedSections.has("cache-files")}
                    onToggle={() => toggleSection("cache-files")}
                    allChecked={cacheFilesState.all}
                    someChecked={cacheFilesState.some}
                    onCheckAll={() => toggleAllInSection(cacheFiles)}
                  />
                  {expandedSections.has("cache-files") && (
                    <div className="ml-3 mb-1">
                      {cacheFiles.map((f) => (
                        <FileRow
                          key={f.path}
                          entry={f}
                          checked={checkedPaths.has(f.path)}
                          onToggle={() => toggleFile(f.path)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Orphan images - default checked */}
              {orphanImages.length > 0 && (
                <div>
                  <SectionHeader
                    label="废弃图片"
                    icon={Image}
                    count={orphanImages.length}
                    totalSize={orphanImagesState.totalSize}
                    expanded={expandedSections.has("orphan-images")}
                    onToggle={() => toggleSection("orphan-images")}
                    allChecked={orphanImagesState.all}
                    someChecked={orphanImagesState.some}
                    onCheckAll={() => toggleAllInSection(orphanImages)}
                  />
                  {expandedSections.has("orphan-images") && (
                    <div className="ml-3 mb-1">
                      {orphanImages.map((f) => (
                        <FileRow
                          key={f.path}
                          entry={f}
                          checked={checkedPaths.has(f.path)}
                          onToggle={() => toggleFile(f.path)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* In-use uploads - NOT checked by default */}
              {inUseUploads.length > 0 && (
                <div>
                  <SectionHeader
                    label="使用中的上传文件"
                    icon={FileText}
                    count={inUseUploads.length}
                    totalSize={inUseUploadsState.totalSize}
                    expanded={expandedSections.has("inuse-uploads")}
                    onToggle={() => toggleSection("inuse-uploads")}
                    allChecked={inUseUploadsState.all}
                    someChecked={inUseUploadsState.some}
                    onCheckAll={() => toggleAllInSection(inUseUploads)}
                  />
                  {expandedSections.has("inuse-uploads") && (
                    <div className="ml-3 mb-1">
                      {inUseUploads.map((f) => (
                        <FileRow
                          key={f.path}
                          entry={f}
                          checked={checkedPaths.has(f.path)}
                          onToggle={() => toggleFile(f.path)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* In-use images - NOT checked by default */}
              {inUseImages.length > 0 && (
                <div>
                  <SectionHeader
                    label="使用中的图片"
                    icon={Image}
                    count={inUseImages.length}
                    totalSize={inUseImagesState.totalSize}
                    expanded={expandedSections.has("inuse-images")}
                    onToggle={() => toggleSection("inuse-images")}
                    allChecked={inUseImagesState.all}
                    someChecked={inUseImagesState.some}
                    onCheckAll={() => toggleAllInSection(inUseImages)}
                  />
                  {expandedSections.has("inuse-images") && (
                    <div className="ml-3 mb-1">
                      {inUseImages.map((f) => (
                        <FileRow
                          key={f.path}
                          entry={f}
                          checked={checkedPaths.has(f.path)}
                          onToggle={() => toggleFile(f.path)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {hasAnyFiles && (
          <div className="px-5 py-3 border-t border-surface-200/50 dark:border-surface-700/30 space-y-2">
            <div className="flex items-center justify-between text-xs text-surface-500">
              <span>已选 {totalSelected} 个文件</span>
              <span>{formatFileSize(totalSelectedSize)}</span>
            </div>
            <Button
              variant="danger"
              className="w-full"
              onClick={handleDelete}
              disabled={orphanLoading || totalSelected === 0}
            >
              {orphanLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
              删除选中文件 ({totalSelected})
            </Button>
          </div>
        )}
      </div>
    </Dialog>
  )
}