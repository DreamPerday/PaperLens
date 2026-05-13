"use client"

import React, { useEffect, useRef } from "react"
import katex from "katex"

interface MathRendererProps {
  content: string
  display?: boolean
}

export function MathRenderer({ content, display = false }: MathRendererProps) {
  const containerRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      try {
        katex.render(content, containerRef.current, {
          displayMode: display,
          throwOnError: false,
          trust: true,
          macros: {
            "\\R": "\\mathbb{R}",
            "\\N": "\\mathbb{N}",
            "\\Z": "\\mathbb{Z}",
          },
        })
      } catch {
        if (containerRef.current) {
          containerRef.current.textContent = content
        }
      }
    }
  }, [content, display])

  return <span ref={containerRef} />
}

export function renderMathInText(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = []
  const regex = /\$\$([\s\S]*?)\$\$|\$([^$\n]*?)\$/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }

    if (match[1]) {
      parts.push(<MathRenderer key={`math-${key++}`} content={match[1].trim()} display />)
    } else if (match[2]) {
      parts.push(<MathRenderer key={`math-${key++}`} content={match[2].trim()} />)
    }

    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }

  return parts.length > 0 ? parts : [text]
}
