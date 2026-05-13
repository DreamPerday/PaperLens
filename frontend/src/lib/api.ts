import type { Project, PaperFile, TranslationResult, GlossaryTerm, BatchTranslationJob } from "@/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  console.log(`[API] ${options?.method || "GET"} ${url}`)
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  })
  if (!res.ok) {
    const errBody = await res.text()
    console.error(`[API ERROR] ${res.status} ${res.statusText}: ${errBody}`)
    throw new Error(`API Error: ${res.status} ${res.statusText}`)
  }
  const data = await res.json()
  console.log(`[API RESPONSE]`, data)
  return data
}

export interface DocumentContent {
  id: string
  original_text: string
  translated_text: string
  doc_type: string
  headings: Array<{ level: number; text: string }>
}

/** 将后端文档对象映射为前端 PaperFile */
function mapDocToPaperFile(doc: any): PaperFile {
  return {
    id: doc.id,
    name: doc.original_name || doc.filename || "unknown",
    type: doc.doc_type || "pdf",
    size: doc.size || 0,
    uploadedAt: doc.created_at || "",
    status: doc.status || "uploaded",
    path: doc.file_path || "",
  }
}

export const api = {
  projects: {
    list: () => fetchAPI<{ data: Project[] }>("/api/projects"),
    get: async (id: string) => {
      const [projectRes, docsRes] = await Promise.all([
        fetchAPI<{ data: Project }>(`/api/projects/${id}`),
        fetchAPI<{ data: any[] }>(`/api/projects/${id}/documents`).catch(() => ({ data: [] })),
      ])
      return {
        data: {
          ...projectRes.data,
          files: (docsRes.data || []).map(mapDocToPaperFile),
        } as Project,
      }
    },
    create: (data: Partial<Project>) =>
      fetchAPI<{ data: Project }>("/api/projects", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Project>) =>
      fetchAPI<{ data: Project }>(`/api/projects/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      fetchAPI<{ message: string }>(`/api/projects/${id}`, { method: "DELETE" }),
  },

  files: {
    list: (projectId: string) =>
      fetchAPI<{ data: any[] }>(`/api/projects/${projectId}/documents`),
    upload: async (projectId: string, file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      console.log(`[API UPLOAD] POST /api/projects/${projectId}/documents/upload -> ${file.name}`)
      const res = await fetch(`${API_BASE}/api/projects/${projectId}/documents/upload`, {
        method: "POST",
        body: formData,
      })
      if (!res.ok) {
        const errBody = await res.text()
        console.error(`[API UPLOAD ERROR] ${res.status}: ${errBody}`)
        throw new Error("Upload failed")
      }
      const data = await res.json()
      console.log(`[API UPLOAD RESPONSE]`, data)
      return { data: mapDocToPaperFile(data.data) }
    },
    delete: (projectId: string, docId: string) =>
      fetchAPI<{ message: string }>(`/api/projects/${projectId}/documents/${docId}`, {
        method: "DELETE",
      }),
    rename: (projectId: string, docId: string, newName: string) =>
      fetchAPI<{ data: any; message: string }>(`/api/projects/${projectId}/documents/${docId}`, {
        method: "PUT",
        body: JSON.stringify({ original_name: newName }),
      }),
    getContent: (projectId: string, docId: string) =>
      fetchAPI<{ data: DocumentContent }>(`/api/projects/${projectId}/documents/${docId}/content`),
  },

  translation: {
    start: (projectId: string, docId: string, sourceLang = "en", targetLang = "zh") =>
      fetchAPI<{ data: { job_id: string; status: string; progress: number; result?: { text: string; tokens: number } }; message: string }>(
        `/api/projects/${projectId}/documents/${docId}/translate`,
        {
          method: "POST",
          body: JSON.stringify({
            document_id: docId,
            source_lang: sourceLang,
            target_lang: targetLang,
          }),
        }
      ),
    status: (projectId: string, docId: string) =>
      fetchAPI<{ data: { job_id: string; status: string; progress: number; result?: { text: string; tokens: number } } }>(
        `/api/projects/${projectId}/documents/${docId}/translate/status`
      ),
    glossary: {
      list: (projectId: string) =>
        fetchAPI<{ data: GlossaryTerm[] }>(`/api/projects/${projectId}/glossary`),
      add: (projectId: string, term: GlossaryTerm) =>
        fetchAPI<{ data: GlossaryTerm }>(`/api/projects/${projectId}/glossary`, {
          method: "POST",
          body: JSON.stringify(term),
        }),
      delete: (projectId: string, termId: string) =>
        fetchAPI<{ message: string }>(`/api/projects/${projectId}/glossary/${termId}`, {
          method: "DELETE",
        }),
    },
  },

  stats: {
    api: () => fetchAPI<{ data: { projects: number; documents: number; tokens_used: number } }>("/api/stats"),
    tokens: () => fetchAPI<{
      data: {
        total_tokens: number
        project_breakdown: Array<{
          project_id: string
          project_name: string
          document_count: number
          translation_count: number
          tokens_used: number
        }>
        user_tokens: Record<string, unknown>
      }
    }>("/api/projects/token-stats"),
    history: (days: number = 30) =>
      fetchAPI<{
        data: {
          records: Array<{
            timestamp: string
            project_id: string
            doc_id: string
            doc_name: string
            tokens_used: number
            paragraph_count: number
          }>
          daily_summary: Array<{ date: string; tokens: number; count: number }>
          total_records: number
          total_tokens: number
          days: number
        }
      }>(`/api/projects/token-history?days=${days}`),
  },

  search: {
    query: (q: string) =>
      fetchAPI<{
        data: Array<{
          project_id: string
          project_name: string
          doc_id: string
          doc_name: string
          doc_type: string
          match_position: number
          snippet: string
        }>
        query: string
        total: number
      }>(`/api/projects/search?q=${encodeURIComponent(q)}`),
  },

  export: {
    generate: (
      projectId: string,
      docId: string,
      options: { 
        format: string; 
        embed_images?: boolean; 
        include_original?: boolean; 
        include_translation?: boolean;
        theme?: string;
        page_size?: string;
        font_size?: number;
        include_toc?: boolean;
        watermark?: string;
      }
    ) =>
      fetchAPI<{
        data: {
          content: string
          mime: string
          filename: string
        }
      }>(`/api/projects/${projectId}/documents/${docId}/export`, {
        method: "POST",
        body: JSON.stringify(options),
      }),
    formats: () => 
      fetchAPI<{
        data: {
          formats: string[]
          options: {
            themes: string[]
            page_sizes: string[]
            default_font_size: number
          }
        }
      }>("/api/projects/export/formats"),
  },

  cleanup: {
    listOrphans: () =>
      fetchAPI<{
        data: {
          orphan_uploads: Array<{ name: string; path: string; size: number; mtime: number }>
          in_use_uploads: Array<{ name: string; path: string; size: number; mtime: number }>
          orphan_images: Array<{ name: string; path: string; size: number; mtime: number }>
          in_use_images: Array<{ name: string; path: string; size: number; mtime: number }>
          cache_files: Array<{ name: string; path: string; size: number; mtime: number }>
          total_orphans: number
          total_size: number
        }
      }>("/api/projects/storage/orphans"),
    deleteSelected: (paths: string[]) =>
      fetchAPI<{
        data: { deleted_count: number; deleted_size: number }
        message: string
      }>("/api/projects/storage/orphans/delete-selected", {
        method: "POST",
        body: JSON.stringify({ paths }),
      }),
    deleteOrphans: () =>
      fetchAPI<{
        data: { deleted_count: number; deleted_size: number }
        message: string
      }>("/api/projects/storage/orphans", { method: "DELETE" }),
  },
}