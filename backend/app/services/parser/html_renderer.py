from __future__ import annotations
from typing import List, Optional, Set
from app.models.block_schema import (
    Block, BlockType, InlineNode, InlineType,
    Document, TableAlign
)


class HTMLRenderer:

    def render(self, document: Document) -> str:
        parts: List[str] = []
        for block in document.blocks:
            rendered = self._render_block(block)
            if rendered is not None:
                parts.append(rendered)
        return '\n'.join(parts)

    def _render_block(self, block: Block) -> Optional[str]:
        if block.type == BlockType.heading:
            text = self._render_inlines(block.inlines)
            cls = ' class="keep-with-next"' if block.level <= 3 else ''
            return f'<h{block.level}{cls}>{text}</h{block.level}>'

        elif block.type == BlockType.paragraph:
            text = self._render_inlines(block.inlines)
            if not text.strip():
                return None
            return f'<p>{text}</p>'

        elif block.type == BlockType.code_block:
            lang = block.lang or ""
            lang_cls = f' class="language-{lang}"' if lang else ''
            escaped = self._escape_html(block.content)
            return f'<pre><code{lang_cls}>{escaped}</code></pre>'

        elif block.type == BlockType.math_block:
            return f'<div class="math-block">\\[{block.content}\\]</div>'

        elif block.type == BlockType.bullet_list:
            items: List[str] = []
            for child in block.children:
                text = self._render_inlines(child.inlines)
                items.append(f'<li>{text}</li>')
            return '<ul>\n' + '\n'.join(items) + '\n</ul>'

        elif block.type == BlockType.ordered_list:
            items: List[str] = []
            for child in block.children:
                text = self._render_inlines(child.inlines)
                items.append(f'<li>{text}</li>')
            start_attr = f' start="{block.start}"' if block.start != 1 else ''
            return f'<ol{start_attr}>\n' + '\n'.join(items) + '\n</ol>'

        elif block.type == BlockType.blockquote:
            inner = ''
            for child in block.children:
                rendered = self._render_block(child)
                if rendered:
                    inner += rendered + '\n'
            return f'<blockquote>\n{inner.rstrip()}\n</blockquote>'

        elif block.type == BlockType.table:
            return self._render_table(block)

        elif block.type == BlockType.thematic_break:
            return '<hr />'

        elif block.type == BlockType.html_block:
            return block.content

        return None

    def _render_table(self, block: Block) -> str:
        if not block.rows:
            return ''

        aligns = block.aligns or []

        rows_html: List[str] = []

        header_cells = block.rows[0]
        header_html = ''.join(
            f'<th>{self._render_inlines(cell)}</th>'
            for cell in header_cells
        )
        rows_html.append(f'<thead>\n<tr>\n{header_html}\n</tr>\n</thead>')

        if len(block.rows) > 1:
            body_rows: List[str] = []
            for row in block.rows[1:]:
                cells_html = ''
                for ci, cell in enumerate(row):
                    align = aligns[ci] if ci < len(aligns) else None
                    cls = ''
                    if align == TableAlign.center:
                        cls = ' class="text-center"'
                    elif align == TableAlign.right:
                        cls = ' class="text-right"'
                    cells_html += f'<td{cls}>{self._render_inlines(cell)}</td>'
                body_rows.append(f'<tr>\n{cells_html}\n</tr>')
            rows_html.append(f'<tbody>\n' + '\n'.join(body_rows) + '\n</tbody>')

        return '<div class="table-wrapper">\n<table>\n' + '\n'.join(rows_html) + '\n</table>\n</div>'

    def _render_inlines(self, nodes: List[InlineNode]) -> str:
        parts: List[str] = []
        for node in nodes:
            parts.append(self._render_inline(node))
        return ''.join(parts)

    def _render_inline(self, node: InlineNode) -> str:
        if node.type == InlineType.text:
            return self._escape_html(node.content)

        elif node.type == InlineType.bold:
            inner = self._render_inlines(node.children) if node.children else self._escape_html(node.content)
            return f'<strong>{inner}</strong>'

        elif node.type == InlineType.italic:
            inner = self._render_inlines(node.children) if node.children else self._escape_html(node.content)
            return f'<em>{inner}</em>'

        elif node.type == InlineType.underline:
            return f'<u>{self._escape_html(node.content)}</u>'

        elif node.type == InlineType.strikethrough:
            return f'<s>{self._escape_html(node.content)}</s>'

        elif node.type == InlineType.code:
            return f'<code>{self._escape_html(node.content)}</code>'

        elif node.type == InlineType.math:
            return f'<span class="math-inline">\\({node.content}\\)</span>'

        elif node.type == InlineType.link:
            inner = self._render_inlines(node.children) if node.children else self._escape_html(node.content)
            url = self._escape_html_attr(node.url)
            return f'<a href="{url}">{inner}</a>'

        elif node.type == InlineType.image:
            alt = self._escape_html_attr(node.alt or '')
            src = self._escape_html_attr(node.url)
            return f'<figure class="figure"><img src="{src}" alt="{alt}" /></figure>'

        elif node.type == InlineType.soft_break:
            return '<br />'

        return self._escape_html(node.content or '')

    def _escape_html(self, text: str) -> str:
        return (
            text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )

    def _escape_html_attr(self, text: str) -> str:
        return (
            text.replace('&', '&amp;')
            .replace('"', '&quot;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )


def render_to_html(document: Document) -> str:
    renderer = HTMLRenderer()
    return renderer.render(document)