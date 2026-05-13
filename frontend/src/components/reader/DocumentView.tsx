"use client"

import React, { useMemo } from "react"
import { cn } from "@/lib/utils"
import katex from "katex"

interface DocumentViewProps {
  content: string
  className?: string
  fontSize?: number
  lineHeight?: number
}

function esc(s: unknown): string {
  if (typeof s !== "string") return ""
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

function tex(math: string, display: boolean): string {
  try {
    return katex.renderToString(math.trim(), {
      displayMode: display,
      throwOnError: false,
      trust: true,
      strict: false,
    })
  } catch {
    return `<span class="italic text-accent-500 font-mono">${esc(math)}</span>`
  }
}

function inlineMathToHtml(text: string): string {
  if (typeof text !== "string") return ""
  if (!text.includes("$")) {
    if (text.includes("<") || text.includes(">") || text.includes("&")) return esc(text)
    return text
  }
  const out: string[] = []
  let last = 0
  const re = /\$([^$]+)\$/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      const plain = text.slice(last, m.index)
      out.push(plain.includes("<") || plain.includes(">") || plain.includes("&") ? esc(plain) : plain)
    }
    out.push(tex(m[1], false))
    last = m.index + m[0].length
  }
  if (last < text.length) {
    const tail = text.slice(last)
    out.push(tail.includes("<") || tail.includes(">") || tail.includes("&") ? esc(tail) : tail)
  }
  return out.join("")
}

function renderInlineMathInHtml(html: string): string {
  if (typeof html !== "string") return ""
  return html.replace(/>([^<>]*?)</g, (_full, text: string) => {
    if (!text.includes("$")) return `>${text}<`
    return `>${inlineMathToHtml(text)}<`
  })
}

function renderContentToHtml(raw: unknown): string {
  if (typeof raw !== "string" || !raw) return ""

  let hIdx = 0

  const dmCache: string[] = []
  let body = raw.replace(/\$\$([\s\S]*?)\$\$/g, (_mm, math: string) => {
    dmCache.push(tex(math, true))
    return `\x00DM${dmCache.length - 1}\x00`
  })

  const restoreDM = (s: string) =>
    s.replace(/\x00DM(\d+)\x00/g, (_mm, i: string) =>
      `<div class="math-display">${dmCache[parseInt(i)]}</div>`
    )

  const blocks = body.split(/\n\n+/)
  const out: string[] = []

  for (const block of blocks) {
    const t = block.trim()
    if (!t) continue

    const firstLine = t.split("\n")[0]
    const hMatch = firstLine.match(/^(#{1,4})\s+(.+)/)
    if (hMatch) {
      const level = hMatch[1].length
      const title = inlineMathToHtml(hMatch[2])
      const rest = t.slice(firstLine.length).trim()
      out.push(`<h${level} id="toc-heading-${hIdx}" data-toc-id="toc-heading-${hIdx}">${title}</h${level}>`)
      hIdx++
      if (rest) out.push(`<p>${restoreDM(inlineMathToHtml(rest))}</p>`)
      continue
    }

    if (/^<[a-zA-Z/!]/.test(t)) {
      if (/^<(table|div|img|figure|blockquote|pre|ul|ol|dl)/i.test(t)) {
        let restored = restoreDM(t)
        restored = renderInlineMathInHtml(restored)
        if (/^<table/i.test(t)) {
          out.push(`<div class="table-wrapper">${restored}</div>`)
        } else {
          out.push(restored)
        }
      } else if (/^<tr[\s>]/i.test(t)) {
        let restored = restoreDM(t)
        restored = renderInlineMathInHtml(restored)
        out.push(`<div class="table-wrapper"><table><tbody>${restored}</tbody></table></div>`)
      } else {
        out.push(t)
      }
      continue
    }

    const lines = t.split("\n").map(l => l.trim()).filter(Boolean)

    const allBullet = lines.every(l => /^[-*]\s/.test(l))
    if (allBullet && lines.length > 0) {
      const items = lines.map(l => `<li>${inlineMathToHtml(l.slice(2))}</li>`)
      out.push(`<ul>${items.join("")}</ul>`)
      continue
    }

    const allNumbered = lines.every(l => /^\d+[.)]\s/.test(l))
    if (allNumbered && lines.length > 0) {
      const items = lines.map(l => `<li>${inlineMathToHtml(l.replace(/^\d+[.)]\s+/, ""))}</li>`)
      out.push(`<ol>${items.join("")}</ol>`)
      continue
    }

    const html = restoreDM(inlineMathToHtml(t))
    if (html.includes('<div class="math-display"')) {
      out.push(html)
    } else {
      out.push(`<p>${html}</p>`)
    }
  }

  return out.join("\n")
}

export function DocumentView({ content, className, fontSize, lineHeight }: DocumentViewProps) {
  const html = useMemo(() => {
    if (typeof content !== "string" || !content) return ""
    return renderContentToHtml(content)
  }, [content])

  if (!html) return null

  const style: React.CSSProperties = {}
  if (fontSize) style.fontSize = `${fontSize}px`
  if (lineHeight) style.lineHeight = lineHeight

  return (
    <div
      className={cn("doc-content animate-fade-in", className)}
      style={style}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
