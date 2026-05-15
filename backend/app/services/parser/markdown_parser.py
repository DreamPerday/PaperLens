from __future__ import annotations
import re
from typing import List, Optional, Tuple
from app.models.block_schema import (
    Block, BlockType, InlineNode, InlineType,
    Document, TableAlign
)


MATH_BLOCK_PATTERN = re.compile(
    r'(\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\}|'
    r'\\\[[\s\S]*?\\\]|'
    r'\$\$[\s\S]*?\$\$)',
    re.MULTILINE
)

MATH_INLINE_PATTERN = re.compile(
    r'(\\\([\s\S]*?\\\)|(?<!\$)\$(?!\$)[^\n$]+(?<!\$)\$(?!\$))'
)

FENCED_CODE_PATTERN = re.compile(
    r'^(`{3,}|~{3,})(\w*)\s*\n([\s\S]*?)\n\1\s*$',
    re.MULTILINE
)

HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

THEMATIC_BREAK_PATTERN = re.compile(r'^([-*_]){3,}\s*$', re.MULTILINE)

BLOCKQUOTE_PATTERN = re.compile(r'^>\s?(.*)$', re.MULTILINE)

UNORDERED_LIST_PATTERN = re.compile(r'^[-*+]\s+(.+)$', re.MULTILINE)
ORDERED_LIST_PATTERN = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)

TABLE_PATTERN = re.compile(
    r'^\|(.+)\|\s*\n\|([-:\s|]+)\|\s*\n((?:\|.+\|\s*\n?)*)$',
    re.MULTILINE
)

HTML_TAG_PATTERN = re.compile(r'^<(p|div|pre|table|section|article|header|footer|main|nav|aside|figure|form)[\s>]', re.IGNORECASE)

STANDALONE_IMG_MD = re.compile(r'^!\[([^\]]*)\]\(([^)]+)\)$')
STANDALONE_IMG_HTML = re.compile(r'^<img\s+[^>]*?src="([^"]+)"[^>]*?/?>$', re.IGNORECASE)


class MarkdownParser:

    def parse(self, text: str) -> Document:
        blocks = self._parse_blocks(text)
        return Document(blocks=blocks, source_text=text)

    def _parse_blocks(self, text: str) -> List[Block]:
        blocks: List[Block] = []
        lines = text.split('\n')
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            block, consumed = self._try_parse_math_block(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            block, consumed = self._try_parse_fenced_code(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            match = HEADING_PATTERN.match(line)
            if match:
                level = len(match.group(1))
                heading_text = match.group(2)
                inlines = self._parse_inlines(heading_text)
                blocks.append(Block(
                    type=BlockType.heading,
                    level=level,
                    inlines=inlines,
                    content=heading_text
                ))
                i += 1
                continue

            match = THEMATIC_BREAK_PATTERN.match(stripped)
            if match:
                blocks.append(Block(type=BlockType.thematic_break))
                i += 1
                continue

            block, consumed = self._try_parse_table(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            block, consumed = self._try_parse_blockquote(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            block, consumed = self._try_parse_list(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            block, consumed = self._try_parse_html_block(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            img_match = STANDALONE_IMG_MD.match(stripped)
            if img_match:
                blocks.append(Block(
                    type=BlockType.image,
                    content=img_match.group(1),
                    meta={"url": img_match.group(2), "alt": img_match.group(1)}
                ))
                i += 1
                continue

            img_match = STANDALONE_IMG_HTML.match(stripped)
            if img_match:
                src = img_match.group(1)
                alt_match = re.search(r'alt="([^"]*)"', stripped)
                alt = alt_match.group(1) if alt_match else ""
                blocks.append(Block(
                    type=BlockType.image,
                    content=alt,
                    meta={"url": src, "alt": alt}
                ))
                i += 1
                continue

            block, consumed = self._try_parse_paragraph(lines, i)
            if block:
                blocks.append(block)
                i += consumed
                continue

            i += 1

        return blocks

    def _try_parse_math_block(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        text_block = '\n'.join(lines[start:start + 100])
        match = MATH_BLOCK_PATTERN.search(text_block)
        if not match:
            return None, 0

        match_start_line = text_block[:match.start()].count('\n')
        if match_start_line != 0:
            return None, 0

        consumed_lines = text_block[:match.end()].count('\n') + 1
        raw = match.group(0)

        env_match = re.match(r'\\begin\{([^}]*)\}', raw)
        env_name = env_match.group(1) if env_match else ""

        return Block(
            type=BlockType.math_block,
            content=raw,
            info=env_name
        ), consumed_lines

    def _try_parse_fenced_code(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        line = lines[start]
        stripped = line.rstrip()
        match = re.match(r'^(```|~~~)(\w*)\s*$', stripped)
        if not match:
            return None, 0

        fence = match.group(1)
        lang = match.group(2)
        code_lines: List[str] = []
        i = start + 1
        while i < len(lines):
            if lines[i].rstrip() == fence:
                i += 1
                break
            code_lines.append(lines[i])
            i += 1

        return Block(
            type=BlockType.code_block,
            content='\n'.join(code_lines),
            lang=lang,
            info=lang
        ), i - start

    def _try_parse_table(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        if start + 2 >= len(lines):
            return None, 0

        header_line = lines[start].strip()
        if not header_line.startswith('|') or not header_line.endswith('|'):
            return None, 0

        sep_line = lines[start + 1].strip()
        if not sep_line.startswith('|'):
            return None, 0

        sep_cells = [c.strip() for c in sep_line.split('|') if c.strip()]
        if not all(re.match(r'^:?-+:?$', c) for c in sep_cells if c):
            return None, 0

        aligns: List[TableAlign] = []
        for c in sep_cells:
            if c.startswith(':') and c.endswith(':'):
                aligns.append(TableAlign.center)
            elif c.startswith(':'):
                aligns.append(TableAlign.left)
            elif c.endswith(':'):
                aligns.append(TableAlign.right)
            else:
                aligns.append(TableAlign.left)

        header_cells = [c.strip() for c in header_line.split('|')]
        header_cells = [c for c in header_cells if c or c == '']
        if header_cells and not header_cells[0]:
            header_cells = header_cells[1:]
        if header_cells and not header_cells[-1]:
            header_cells = header_cells[:-1]

        header_cells_inlines = [self._parse_inlines(c) for c in header_cells]

        body_rows: List[List[List[InlineNode]]] = []
        i = start + 2
        while i < len(lines):
            row_line = lines[i].strip()
            if not row_line.startswith('|'):
                break

            cells = [c.strip() for c in row_line.split('|')]
            cells = [c for c in cells if c or c == '']
            if cells and not cells[0]:
                cells = cells[1:]
            if cells and not cells[-1]:
                cells = cells[:-1]

            row_cells = [self._parse_inlines(c) for c in cells]
            body_rows.append(row_cells)
            i += 1

        all_rows: List[List[List[InlineNode]]] = []
        all_rows.append(header_cells_inlines)
        all_rows.extend(body_rows)

        return Block(
            type=BlockType.table,
            rows=all_rows,
            aligns=aligns
        ), i - start

    def _try_parse_blockquote(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        if not lines[start].lstrip().startswith('> '):
            return None, 0

        quote_lines: List[str] = []
        i = start
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('> '):
                quote_lines.append(stripped[2:])
                i += 1
            elif stripped == '>':
                quote_lines.append('')
                i += 1
            else:
                break

        quote_text = '\n'.join(quote_lines)
        inner_blocks = self._parse_blocks(quote_text)
        return Block(
            type=BlockType.blockquote,
            children=inner_blocks,
            content=quote_text
        ), i - start

    def _try_parse_list(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        line = lines[start]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        unordered_match = UNORDERED_LIST_PATTERN.match(stripped)
        ordered_match = ORDERED_LIST_PATTERN.match(stripped)

        if not unordered_match and not ordered_match:
            return None, 0

        is_ordered = ordered_match is not None
        items: List[str] = []
        i = start

        while i < len(lines):
            current = lines[i]
            current_stripped = current.lstrip()
            current_indent = len(current) - len(current_stripped)

            ul_match = UNORDERED_LIST_PATTERN.match(current_stripped)
            ol_match = ORDERED_LIST_PATTERN.match(current_stripped)

            if ul_match and not is_ordered and current_indent >= indent:
                items.append(ul_match.group(1))
                i += 1
            elif ol_match and is_ordered and current_indent >= indent:
                items.append(ol_match.group(1))
                i += 1
            elif current_stripped == '' and i < len(lines) - 1:
                next_stripped = lines[i + 1].lstrip()
                next_ul = UNORDERED_LIST_PATTERN.match(next_stripped)
                next_ol = ORDERED_LIST_PATTERN.match(next_stripped)
                if (next_ul and not is_ordered) or (next_ol and is_ordered):
                    items.append('')
                    i += 1
                else:
                    break
            else:
                break

        item_blocks: List[Block] = []
        for item_text in items:
            inlines = self._parse_inlines(item_text)
            item_blocks.append(Block(
                type=BlockType.list_item,
                inlines=inlines,
                content=item_text
            ))

        return Block(
            type=BlockType.ordered_list if is_ordered else BlockType.bullet_list,
            children=item_blocks,
            ordered=is_ordered
        ), i - start

    def _try_parse_html_block(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        line = lines[start].strip()
        match = HTML_TAG_PATTERN.match(line)
        if not match:
            return None, 0

        tag_name = match.group(1)
        closer = f'</{tag_name}>'
        html_lines: List[str] = []
        i = start

        while i < len(lines):
            html_lines.append(lines[i])
            if closer in lines[i]:
                i += 1
                break
            i += 1

        return Block(
            type=BlockType.html_block,
            content='\n'.join(html_lines)
        ), i - start

    def _try_parse_paragraph(self, lines: List[str], start: int) -> Tuple[Optional[Block], int]:
        para_lines: List[str] = []
        i = start

        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                break

            if UNORDERED_LIST_PATTERN.match(stripped) or ORDERED_LIST_PATTERN.match(stripped):
                break
            if stripped.startswith('> '):
                break
            if HEADING_PATTERN.match(stripped):
                break
            if THEMATIC_BREAK_PATTERN.match(stripped):
                break
            if stripped.startswith('```') or stripped.startswith('~~~'):
                break
            if stripped.startswith('|'):
                break
            if MATH_BLOCK_PATTERN.match(stripped):
                break
            if STANDALONE_IMG_MD.match(stripped) or STANDALONE_IMG_HTML.match(stripped):
                break
            if re.match(r'^\s*$', lines[i]):
                break

            para_lines.append(lines[i])
            i += 1

        if not para_lines:
            return None, 0

        text = '\n'.join(para_lines)
        text = text.strip()
        inlines = self._parse_inlines(text)

        return Block(
            type=BlockType.paragraph,
            inlines=inlines,
            content=text
        ), i - start

    def _parse_inlines(self, text: str) -> List[InlineNode]:
        if not text:
            return [InlineNode(type=InlineType.text, content='')]

        nodes: List[InlineNode] = []
        pos = 0

        patterns = [
            (self._try_parse_inline_math, None),
            (self._try_parse_inline_code, None),
            (self._try_parse_image, None),
            (self._try_parse_link, None),
            (self._try_parse_bold, None),
            (self._try_parse_italic, None),
        ]

        while pos < len(text):
            remaining = text[pos:]
            matched = False

            for parser_func, _ in patterns:
                result, consumed = parser_func(remaining)
                if result is not None:
                    if pos > 0 and nodes and nodes[-1].type == InlineType.text:
                        pass
                    nodes.append(result)
                    pos += consumed
                    matched = True
                    break

            if not matched:
                end = pos + 1
                while end < len(text):
                    next_chunk = text[end:]
                    would_match = False
                    for parser_func, _ in patterns:
                        r, _ = parser_func(next_chunk)
                        if r is not None:
                            would_match = True
                            break
                    if would_match:
                        break
                    end += 1

                chunk = text[pos:end]
                if nodes and nodes[-1].type == InlineType.text:
                    nodes[-1].content += chunk
                else:
                    nodes.append(InlineNode(type=InlineType.text, content=chunk))
                pos = end

        return nodes

    def _try_parse_bold(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'\*\*(.+?)\*\*(?!\*)', text)
        if not match:
            match = re.match(r'__(.+?)__', text)
        if match:
            inner = match.group(1)
            children = self._parse_inlines(inner)
            return InlineNode(
                type=InlineType.bold,
                content=inner,
                children=children,
                bold=True
            ), match.end()
        return None, 0

    def _try_parse_italic(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'(?<!\*)\*(?!\*)([^*]+?)(?<!\*)\*(?!\*)', text)
        if not match:
            match = re.match(r'(?<!_)_(?!_)([^_]+?)(?<!_)_(?!_)', text)
        if match:
            inner = match.group(1)
            children = self._parse_inlines(inner)
            return InlineNode(
                type=InlineType.italic,
                content=inner,
                children=children,
                italic=True
            ), match.end()
        return None, 0

    def _try_parse_inline_code(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'`([^`]+)`', text)
        if match:
            return InlineNode(
                type=InlineType.code,
                content=match.group(1),
                code=True
            ), match.end()
        return None, 0

    def _try_parse_inline_math(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'\\\(([\s\S]*?)\\\)', text)
        if match:
            return InlineNode(
                type=InlineType.math,
                content=match.group(1)
            ), match.end()
        match = re.match(r'(?<!\$)\$(?!\$)([^\n$]+?)(?<!\$)\$(?!\$)', text)
        if match:
            return InlineNode(
                type=InlineType.math,
                content=match.group(1)
            ), match.end()
        return None, 0

    def _try_parse_link(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'\[([^\]]*)\]\(([^)]+)\)', text)
        if match:
            inner = match.group(1)
            url = match.group(2)
            children = self._parse_inlines(inner)
            return InlineNode(
                type=InlineType.link,
                content=inner,
                url=url,
                children=children
            ), match.end()
        return None, 0

    def _try_parse_image(self, text: str) -> Tuple[Optional[InlineNode], int]:
        match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', text)
        if match:
            alt = match.group(1)
            url = match.group(2)
            return InlineNode(
                type=InlineType.image,
                content=alt,
                alt=alt,
                url=url
            ), match.end()
        match = re.match(r'<img\s+[^>]*?src="([^"]+)"[^>]*?/?>', text, re.IGNORECASE)
        if match:
            src = match.group(1)
            alt_match = re.search(r'alt="([^"]*)"', match.group(0))
            alt = alt_match.group(1) if alt_match else ""
            return InlineNode(
                type=InlineType.image,
                content=alt,
                alt=alt,
                url=src
            ), match.end()
        return None, 0


def parse_document(text: str) -> Document:
    parser = MarkdownParser()
    return parser.parse(text)