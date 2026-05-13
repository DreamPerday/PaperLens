export const DOCUMENT_AST_VERSION = "1.1.0"

/**
 * Shared AST — single source of truth across Web Reader, PDF, EPUB, DOCX, Markdown.
 *
 * Mirrors backend/app/models/block_schema.py field-for-field to guarantee
 * zero-drift between frontend rendering and backend export.
 */

// ─── Inline Types ────────────────────────────────────────────────────────────

export type InlineType =
  | "text"
  | "bold"
  | "italic"
  | "underline"
  | "strikethrough"
  | "code"
  | "math"
  | "link"
  | "image"
  | "soft_break"

export interface InlineNode {
  type: InlineType
  content: string
  children: InlineNode[]
  url: string
  alt: string
  // style flags (used by rich-text editors)
  bold: boolean
  italic: boolean
  code: boolean
}

// ─── Block Types ─────────────────────────────────────────────────────────────

export type BlockType =
  | "document"
  | "heading"
  | "paragraph"
  | "code_block"
  | "math_block"
  | "image"
  | "bullet_list"
  | "ordered_list"
  | "list_item"
  | "blockquote"
  | "table"
  | "table_row"
  | "table_cell"
  | "thematic_break"
  | "html_block"
  | "footnote"
  | "footnote_ref"
  | "citation"
  | "citation_list"
  | "toc"
  | "figure"
  | "ocr_region"
  | "column_layout"
  | "page_break"

export type TableAlign = "left" | "center" | "right"

// ─── OCR / Layout Types ──────────────────────────────────────────────────────

export interface OCRBBox {
  x: number
  y: number
  width: number
  height: number
  page: number
}

export interface OCRRegion {
  bbox: OCRBBox
  type: "text" | "title" | "figure" | "table" | "formula" | "footer" | "header"
  confidence: number
  text: string
}

// ─── Citation Types ──────────────────────────────────────────────────────────

export interface CitationRef {
  id: string
  index: number
  authors: string
  title: string
  venue: string
  year: number
  doi?: string
  url?: string
}

// ─── Figure Types ────────────────────────────────────────────────────────────

export interface FigureMeta {
  id: string
  caption: string
  label: string
  width: number
  height: number
  src: string
  srcType: "base64" | "url" | "file"
  ocrBbox?: OCRBBox
}

// ─── Translation Types ───────────────────────────────────────────────────────

export interface TranslationPair {
  source: InlineNode[]
  target: InlineNode[]
  confidence: number
}

// ─── Metadata Types ──────────────────────────────────────────────────────────

export interface DocumentMeta {
  title: string
  authors: string[]
  abstract: string
  keywords: string[]
  doi?: string
  arxivId?: string
  venue?: string
  year?: number
  language: string
  pageCount: number
  ocrEngine: string
  ocrConfidence: number
  createdAt: string
  sourceFormat: "pdf" | "docx" | "latex" | "markdown" | "html"
}

// ─── Block ───────────────────────────────────────────────────────────────────

export interface Block {
  type: BlockType
  level: number
  content: string
  info: string
  lang: string
  children: Block[]
  inlines: InlineNode[]
  rows: InlineNode[][][]
  aligns: TableAlign[]
  ordered: boolean
  start: number
  tight: boolean
  meta: Record<string, unknown>
  // Extended fields
  id?: string
  translation?: TranslationPair
  ocrRegion?: OCRRegion
  figureMeta?: FigureMeta
  citationRefs?: CitationRef[]
}

// ─── Document (top-level AST) ────────────────────────────────────────────────

export interface Document {
  blocks: Block[]
  metadata: DocumentMeta
  docType: string | null
  sourceText: string
  version: string
}

// ─── Default factories ───────────────────────────────────────────────────────

export function defaultInlineNode(type: InlineType = "text"): InlineNode {
  return { type, content: "", children: [], url: "", alt: "", bold: false, italic: false, code: false }
}

export function defaultBlock(type: BlockType = "paragraph"): Block {
  return {
    type,
    level: 0,
    content: "",
    info: "",
    lang: "",
    children: [],
    inlines: [],
    rows: [],
    aligns: [],
    ordered: false,
    start: 1,
    tight: false,
    meta: {},
  }
}

export function defaultDocument(): Document {
  return {
    blocks: [],
    metadata: {
      title: "",
      authors: [],
      abstract: "",
      keywords: [],
      language: "en",
      pageCount: 0,
      ocrEngine: "",
      ocrConfidence: 0,
      createdAt: new Date().toISOString(),
      sourceFormat: "pdf",
    },
    docType: null,
    sourceText: "",
    version: DOCUMENT_AST_VERSION,
  }
}