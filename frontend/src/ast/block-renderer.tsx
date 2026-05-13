import React from "react"
import katex from "katex"
import type { Block, InlineNode } from "@/ast/block-schema"
import { cn } from "@/lib/utils"

/**
 * Shared Inline Renderer
 *
 * Pure function that renders an array of InlineNode → React elements.
 * Used identically by Web Reader, Print layout, and SSR export.
 */
export function renderInlines(
  inlines: InlineNode[],
  keyPrefix = ""
): React.ReactNode[] {
  return inlines.map((node, i) => {
    const key = `${keyPrefix}i${i}`

    switch (node.type) {
      case "text":
        return <React.Fragment key={key}>{node.content}</React.Fragment>

      case "bold":
        return <strong key={key}>{renderInlines(node.children.length ? node.children : [{ type: "text", content: node.content, children: [], url: "", alt: "", bold: false, italic: false, code: false }], key)}</strong>

      case "italic":
        return <em key={key}>{renderInlines(node.children.length ? node.children : [{ type: "text", content: node.content, children: [], url: "", alt: "", bold: false, italic: false, code: false }], key)}</em>

      case "underline":
        return <u key={key}>{node.content}</u>

      case "strikethrough":
        return <s key={key}>{node.content}</s>

      case "code":
        return <code key={key} className="inline-code">{node.content}</code>

      case "math":
        return <InlineMath key={key} content={node.content} />

      case "link":
        return (
          <a key={key} href={node.url} target="_blank" rel="noopener noreferrer">
            {renderInlines(node.children.length ? node.children : [{ type: "text", content: node.content, children: [], url: "", alt: "", bold: false, italic: false, code: false }], key)}
          </a>
        )

      case "image":
        return (
          <InlineFigure
            key={key}
            src={node.url}
            alt={node.alt || node.content}
          />
        )

      case "soft_break":
        return <br key={key} />

      default:
        return <React.Fragment key={key}>{node.content}</React.Fragment>
    }
  })
}

// ─── Inline Math ─────────────────────────────────────────────────────────────

function InlineMath({ content }: { content: string }) {
  const html = React.useMemo(() => {
    try {
      return katex.renderToString(content.trim(), {
        displayMode: false,
        throwOnError: false,
        trust: true,
        strict: false,
      })
    } catch {
      return `<span class="italic text-accent-500 font-mono">${esc(content)}</span>`
    }
  }, [content])

  return <span className="math-inline" dangerouslySetInnerHTML={{ __html: html }} />
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
}

// ─── Inline Figure ───────────────────────────────────────────────────────────

function InlineFigure({ src, alt }: { src: string; alt: string }) {
  return (
    <figure className="figure-inline">
      <img src={src} alt={alt} loading="lazy" />
      {alt && <figcaption className="figure-caption">{alt}</figcaption>}
    </figure>
  )
}

// ─── Block Renderer ──────────────────────────────────────────────────────────

export interface BlockRendererProps {
  block: Block
  className?: string
  /** Render mode: "reader" | "print" | "export" */
  mode?: "reader" | "print" | "export"
  /** Block ID for cross-referencing / TOC */
  blockIndex?: number
}

/**
 * Shared Block Renderer
 *
 * One component per Block — the same code path used by:
 *   - Web Reader (DualPaneReader → DocumentView)
 *   - Print / PDF layout (@media print)
 *   - SSR HTML export pipeline
 */
export function BlockRenderer({ block, className, mode = "reader", blockIndex = 0 }: BlockRendererProps) {
  const prefix = `b${blockIndex}`

  switch (block.type) {
    // ── Heading ──────────────────────────────────────────────────
    case "heading": {
      const level = Math.min(block.level, 6)
      const Tag = `h${level}` as keyof React.JSX.IntrinsicElements
      const id = block.id || `toc-heading-${blockIndex}`
      return (
        <Tag id={id} className={cn("heading-block", `h${level}`, "keep-with-next", className)}>
          {renderInlines(block.inlines, prefix)}
        </Tag>
      )
    }

    // ── Paragraph ─────────────────────────────────────────────────
    case "paragraph":
      return (
        <p className={cn("paragraph-block", className)}>
          {renderInlines(block.inlines, prefix)}
        </p>
      )

    // ── Code Block ─────────────────────────────────────────────────
    case "code_block": {
      const lang = block.lang || ""
      return (
        <pre className={cn("code-block", lang && `language-${lang}`, className)}>
          <code className={lang ? `language-${lang}` : ""}>
            {block.content}
          </code>
        </pre>
      )
    }

    // ── Math Block ─────────────────────────────────────────────────
    case "math_block":
      return (
        <DisplayMath
          content={block.content}
          info={block.info}
          className={className}
        />
      )

    // ── Bullet / Ordered Lists ─────────────────────────────────────
    case "bullet_list": {
      const ListTag = "ul"
      return (
        <ListTag className={cn("list-block bullet-list", block.tight && "list-tight", className)}>
          {block.children.map((item, i) => (
            <li key={`${prefix}bi${i}`} className="list-item">
              <BlockRenderer block={{ ...item, type: "list_item" }} mode={mode} blockIndex={i} />
            </li>
          ))}
        </ListTag>
      )
    }

    case "ordered_list": {
      const ListTag = "ol"
      return (
        <ListTag
          className={cn("list-block ordered-list", block.tight && "list-tight", className)}
          start={block.start}
        >
          {block.children.map((item, i) => (
            <li key={`${prefix}oi${i}`} className="list-item">
              <BlockRenderer block={{ ...item, type: "list_item" }} mode={mode} blockIndex={i} />
            </li>
          ))}
        </ListTag>
      )
    }

    case "list_item":
      return <>{renderInlines(block.inlines, prefix)}</>

    // ── Blockquote ─────────────────────────────────────────────────
    case "blockquote":
      return (
        <blockquote className={cn("blockquote-block", className)}>
          {block.children.map((child, i) => (
            <BlockRenderer key={`${prefix}bq${i}`} block={child} mode={mode} blockIndex={i} />
          ))}
        </blockquote>
      )

    // ── Table ──────────────────────────────────────────────────────
    case "table": {
      if (!block.rows.length) return null
      const [header, ...body] = block.rows
      return (
        <div className={cn("table-wrapper", className)}>
          <table className="doc-table">
            {header && (
              <thead>
                <tr>
                  {header.map((cell, ci) => (
                    <th key={`${prefix}h${ci}`} className={cellAlignClass(block.aligns[ci])}>
                      {renderInlines(cell, `${prefix}h${ci}`)}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {body.map((row, ri) => (
                <tr key={`${prefix}r${ri}`}>
                  {row.map((cell, ci) => (
                    <td key={`${prefix}r${ri}c${ci}`} className={cellAlignClass(block.aligns[ci])}>
                      {renderInlines(cell, `${prefix}r${ri}c${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    // ── Thematic Break ─────────────────────────────────────────────
    case "thematic_break":
      return <hr className={cn("thematic-break", className)} />

    // ── HTML Block (passthrough) ───────────────────────────────────
    case "html_block":
      return (
        <div
          className={cn("html-block", className)}
          dangerouslySetInnerHTML={{ __html: block.content }}
        />
      )

    // ── Figure ─────────────────────────────────────────────────────
    case "figure": {
      const fm = block.figureMeta
      return (
        <figure className={cn("figure-block", className)}>
          {fm && (
            <img
              src={fm.src}
              alt={fm.caption || fm.label}
              width={fm.width}
              height={fm.height}
              loading="lazy"
            />
          )}
          {(fm?.caption || fm?.label) && (
            <figcaption className="figure-caption">
              <span className="figure-label">{fm?.label}</span>
              {fm?.caption}
            </figcaption>
          )}
        </figure>
      )
    }

    // ── Citation ───────────────────────────────────────────────────
    case "citation": {
      const refs = block.citationRefs || []
      return (
        <span className="citation-ref">
          [{refs.map((r) => r.index).join(",")}]
        </span>
      )
    }

    case "citation_list":
      return (
        <section className={cn("citation-list", className)}>
          <h2 className="citation-heading">References</h2>
          <ol>
            {(block.citationRefs || []).map((ref) => (
              <li key={ref.id} className="citation-item">
                {ref.authors} ({ref.year}). <em>{ref.title}</em>. {ref.venue}.
                {ref.doi && <> DOI: <a href={`https://doi.org/${ref.doi}`}>{ref.doi}</a></>}
              </li>
            ))}
          </ol>
        </section>
      )

    // ── Footnote ───────────────────────────────────────────────────
    case "footnote":
      return (
        <span className="footnote-block" id={`fn-${block.id || blockIndex}`}>
          <sup>{block.content}</sup>
        </span>
      )

    // ── TOC ────────────────────────────────────────────────────────
    case "toc":
      return (
        <nav className={cn("toc-block", className)}>
          <h2 className="toc-heading">Table of Contents</h2>
          {block.children.map((child, i) => (
            <BlockRenderer key={`${prefix}toc${i}`} block={child} mode={mode} blockIndex={i} />
          ))}
        </nav>
      )

    // ── Page Break ─────────────────────────────────────────────────
    case "page_break":
      return <div className={cn("page-break", className)} />

    // ── Column Layout ──────────────────────────────────────────────
    case "column_layout":
      return (
        <div className={cn("column-layout", block.meta.columns === 2 ? "two-column" : "single-column", className)}>
          {block.children.map((child, i) => (
            <BlockRenderer key={`${prefix}col${i}`} block={child} mode={mode} blockIndex={i} />
          ))}
        </div>
      )

    // ── Image Block ────────────────────────────────────────────────
    case "image":
      return (
        <figure className={cn("image-block", className)}>
          <img src={block.meta.url as string || ""} alt={block.content} loading="lazy" />
          {block.content && <figcaption className="figure-caption">{block.content}</figcaption>}
        </figure>
      )

    default:
      return block.content ? (
        <div className={cn(className)}>{block.content}</div>
      ) : null
  }
}

// ─── Display Math Block ──────────────────────────────────────────────────────

function DisplayMath({ content, info, className }: { content: string; info: string; className?: string }) {
  const html = React.useMemo(() => {
    try {
      let math = content
      // Strip LaTeX env wrappers for katex but keep info
      const envMatch = math.match(/^\\begin\{([^}]*)\}/)
      if (envMatch) {
        const envEnd = math.lastIndexOf(`\\end{${envMatch[1]}}`)
        if (envEnd > -1) {
          math = math.slice(envMatch[0].length, envEnd).trim()
        }
      } else {
        math = math.replace(/^\$\$|\$\$$/g, "").replace(/^\\\[|\\\]$/g, "")
      }
      return katex.renderToString(math.trim(), {
        displayMode: true,
        throwOnError: false,
        trust: true,
        strict: false,
      })
    } catch {
      return `<pre class="math-fallback">${esc(content)}</pre>`
    }
  }, [content])

  return (
    <div className={cn("math-block math-display", className)}>
      {info && <div className="math-env-label">{info}</div>}
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  )
}

// ─── Cell alignment helper ───────────────────────────────────────────────────

function cellAlignClass(align?: string): string {
  switch (align) {
    case "center": return "text-center"
    case "right": return "text-right"
    default: return "text-left"
  }
}

// ─── Document Renderer (all blocks) ──────────────────────────────────────────

export interface DocumentRendererProps {
  blocks: Block[]
  mode?: "reader" | "print" | "export"
  className?: string
}

export function DocumentRenderer({ blocks, mode = "reader", className }: DocumentRendererProps) {
  return (
    <article className={cn("document-renderer", `mode-${mode}`, className)}>
      {blocks.map((block, i) => (
        <BlockRenderer key={block.id || `block-${i}`} block={block} mode={mode} blockIndex={i} />
      ))}
    </article>
  )
}