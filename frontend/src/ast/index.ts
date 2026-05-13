/** AST module barrel export */

export * from "./block-schema"
export { BlockRenderer, DocumentRenderer, renderInlines } from "./block-renderer"
export type { BlockRendererProps, DocumentRendererProps } from "./block-renderer"

// Re-export Katex to guarantee same version across web/print/export
export { default as katex } from "katex"