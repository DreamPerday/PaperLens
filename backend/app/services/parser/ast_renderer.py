from __future__ import annotations
from typing import List, Optional
from app.models.block_schema import (
    Block, BlockType, InlineNode, InlineType,
    Document, TableAlign
)


class MarkdownRenderer:

    def render(self, document: Document) -> str:
        parts: List[str] = []
        for block in document.blocks:
            rendered = self._render_block(block)
            if rendered is not None:
                parts.append(rendered)
        return '\n\n'.join(parts)

    def _render_block(self, block: Block, indent: str = "") -> Optional[str]:
        if block.type == BlockType.heading:
            prefix = '#' * block.level
            text = self._render_inlines(block.inlines)
            return f'{prefix} {text}'

        elif block.type == BlockType.paragraph:
            return self._render_inlines(block.inlines)

        elif block.type == BlockType.code_block:
            lang = block.lang or ""
            return f'```{lang}\n{block.content}\n```'

        elif block.type == BlockType.math_block:
            return block.content

        elif block.type == BlockType.bullet_list:
            items: List[str] = []
            for child in block.children:
                text = self._render_inlines(child.inlines)
                items.append(f'{indent}- {text}')
            return '\n'.join(items)

        elif block.type == BlockType.ordered_list:
            items: List[str] = []
            for idx, child in enumerate(block.children):
                text = self._render_inlines(child.inlines)
                items.append(f'{indent}{block.start + idx}. {text}')
            return '\n'.join(items)

        elif block.type == BlockType.blockquote:
            inner = ''
            for child in block.children:
                rendered = self._render_block(child)
                if rendered:
                    inner += rendered + '\n\n'
            inner = inner.strip()
            lines = inner.split('\n')
            quoted = '\n'.join(f'> {line}' for line in lines)
            return quoted

        elif block.type == BlockType.table:
            return self._render_table(block)

        elif block.type == BlockType.thematic_break:
            return '---'

        elif block.type == BlockType.html_block:
            return block.content

        elif block.type == BlockType.image:
            alt = block.content or ""
            url = block.meta.get("url", "")
            return f"![{alt}]({url})"

        elif block.type == BlockType.list_item:
            return self._render_inlines(block.inlines)

        return None

    def _render_table(self, block: Block) -> str:
        if not block.rows:
            return ''

        rows_data = block.rows
        header_str = '| ' + ' | '.join(
            self._render_inlines(cell) for cell in rows_data[0]
        ) + ' |'

        sep_cells: List[str] = []
        aligns = block.aligns or [TableAlign.left] * len(rows_data[0])
        for align in aligns:
            if align == TableAlign.center:
                sep_cells.append(':---:')
            elif align == TableAlign.right:
                sep_cells.append('---:')
            else:
                sep_cells.append(':---')

        sep_str = '| ' + ' | '.join(sep_cells) + ' |'

        body_lines: List[str] = []
        for row in rows_data[1:]:
            body_lines.append('| ' + ' | '.join(
                self._render_inlines(cell) for cell in row
            ) + ' |')

        return '\n'.join([header_str, sep_str] + body_lines)

    def _render_inlines(self, nodes: List[InlineNode]) -> str:
        parts: List[str] = []
        for node in nodes:
            parts.append(self._render_inline(node))
        return ''.join(parts)

    def _render_inline(self, node: InlineNode) -> str:
        if node.type == InlineType.text:
            return node.content

        elif node.type == InlineType.bold:
            inner = self._render_inlines(node.children) or node.content
            return f'**{inner}**'

        elif node.type == InlineType.italic:
            inner = self._render_inlines(node.children) or node.content
            return f'*{inner}*'

        elif node.type == InlineType.code:
            return f'`{node.content}`'

        elif node.type == InlineType.math:
            return f'${node.content}$'

        elif node.type == InlineType.link:
            inner = self._render_inlines(node.children) or node.content
            return f'[{inner}]({node.url})'

        elif node.type == InlineType.image:
            return f'![{node.alt}]({node.url})'

        elif node.type == InlineType.soft_break:
            return '\n'

        return node.content or ''


def render_document(document: Document) -> str:
    renderer = MarkdownRenderer()
    return renderer.render(document)