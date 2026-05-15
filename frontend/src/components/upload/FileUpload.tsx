"use client"

import React, { useState, useCallback, useRef } from "react"
import { Upload, File, X, FileText, Loader2 } from "lucide-react"
import { useAppStore } from "@/store"
import { Dialog, Button, Badge, Progress } from "@/components/ui"
import { cn, formatFileSize } from "@/lib/utils"
import { api } from "@/lib/api"

export function FileUploadDialog() {
  const uploadDialogOpen = useAppStore((s) => s.uploadDialogOpen)
  const setUploadDialogOpen = useAppStore((s) => s.setUploadDialogOpen)
  const activeProjectId = useAppStore((s) => s.activeProjectId)
  const addFileToProject = useAppStore((s) => s.addFileToProject)
  const loadProjects = useAppStore((s) => s.loadProjects)

  const [dragOver, setDragOver] = useState(false)
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [currentUploadName, setCurrentUploadName] = useState("")
  const [uploadError, setUploadError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    setFiles((prev) => [...prev, ...droppedFiles])
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOver(false)
  }, [])

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (!activeProjectId || files.length === 0) return
    setUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        setCurrentUploadName(file.name)
        setUploadProgress(Math.round((i / files.length) * 100))
        console.log(`[UPLOAD] Uploading file ${i + 1}/${files.length}: ${file.name}`)

        const res = await api.files.upload(activeProjectId, file)
        const uploadedFile = res.data
        console.log(`[UPLOAD] Upload success:`, uploadedFile)

        addFileToProject(activeProjectId, uploadedFile)
        setUploadProgress(Math.round(((i + 1) / files.length) * 100))
      }

      setUploadProgress(100)
      await loadProjects()
      console.log(`[UPLOAD] All ${files.length} files uploaded successfully`)
      setTimeout(() => {
        setUploading(false)
        setFiles([])
        setUploadDialogOpen(false)
        setCurrentUploadName("")
      }, 500)
    } catch (err) {
      console.error(`[UPLOAD] Upload failed:`, err)
      setUploadError(`上传失败: ${err instanceof Error ? err.message : "网络错误"}`)
      setUploading(false)
    }
  }

  const handleClose = () => {
    if (uploading) return
    setFiles([])
    setUploadError(null)
    setUploadDialogOpen(false)
  }

  return (
    <Dialog open={uploadDialogOpen} onClose={handleClose} title="上传论文文件">
      <div className="space-y-4">
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => !uploading && inputRef.current?.click()}
          className={cn(
            "relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200",
            dragOver
              ? "border-accent-500 bg-accent-50/50 dark:bg-accent-500/5"
              : "border-surface-300 dark:border-surface-600 hover:border-accent-400 dark:hover:border-accent-500 hover:bg-surface-50 dark:hover:bg-surface-900/50",
            uploading && "pointer-events-none opacity-60"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.md,.tex,.html,.txt"
            className="hidden"
            disabled={uploading}
            onChange={(e) => {
              const selectedFiles = Array.from(e.target.files || [])
              setFiles((prev) => [...prev, ...selectedFiles])
              setUploadError(null)
            }}
          />
          <div className="flex flex-col items-center gap-2">
            <div className="w-12 h-12 rounded-xl bg-accent-50 dark:bg-accent-500/10 flex items-center justify-center">
              {uploading ? (
                <Loader2 className="w-6 h-6 text-accent-500 animate-spin" />
              ) : (
                <Upload className="w-6 h-6 text-accent-500" />
              )}
            </div>
            <p className="text-sm font-medium text-surface-700 dark:text-surface-300">
              {uploading ? `正在上传 ${currentUploadName}...` : "拖拽文件到此处，或点击上传"}
            </p>
            <p className="text-xs text-surface-400">
              支持 PDF、DOCX、Markdown、LaTeX、HTML 格式
            </p>
          </div>
        </div>

        {uploadError && (
          <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-sm text-rose-600 dark:text-rose-400 animate-fade-in">
            {uploadError}
          </div>
        )}

        {uploading && (
          <div className="space-y-2 animate-fade-in">
            <div className="flex items-center justify-between text-xs text-surface-500">
              <div className="flex items-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-accent-500" />
                <span className="truncate">{currentUploadName}</span>
              </div>
              <span>{files.length > 1 ? `(${Math.round(uploadProgress / 100 * files.length)}/${files.length}) ` : ""}{uploadProgress}%</span>
            </div>
            <Progress value={uploadProgress} size="md" />
          </div>
        )}

        {files.length > 0 && !uploading && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            <span className="section-title">
              待上传 ({files.length} 个文件)
            </span>
            {files.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface-50 dark:bg-surface-800/50 animate-slide-up"
              >
                <FileText className="w-4 h-4 text-surface-400" />
                <span className="flex-1 text-sm text-surface-700 dark:text-surface-300 truncate">
                  {file.name}
                </span>
                <span className="text-xs text-surface-400">
                  {formatFileSize(file.size)}
                </span>
                <button
                  onClick={() => removeFile(index)}
                  className="p-0.5 rounded hover:bg-surface-200 dark:hover:bg-surface-700 text-surface-400 hover:text-rose-500"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          {uploading ? (
            <div className="flex items-center gap-2 text-sm text-surface-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              正在上传...
            </div>
          ) : (
            <>
              <Button variant="secondary" onClick={handleClose}>
                取消
              </Button>
              <Button onClick={handleUpload} disabled={files.length === 0}>
                <Upload className="w-4 h-4" />
                上传 ({files.length})
              </Button>
            </>
          )}
        </div>
      </div>
    </Dialog>
  )
}