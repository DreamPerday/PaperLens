from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from .schemas import DocumentType


class InlineType(str, Enum):
    text = "text"
    bold = "bold"
    italic = "italic"
    underline = "underline"
    strikethrough = "strikethrough"
    code = "code"
    math = "math"
    link = "link"
    image = "image"
    soft_break = "soft_break"


class InlineNode(BaseModel):
    type: InlineType = InlineType.text
    content: str = ""
    children: List[InlineNode] = []
    url: str = ""
    alt: str = ""
    bold: bool = False
    italic: bool = False
    code: bool = False


class BlockType(str, Enum):
    document = "document"
    heading = "heading"
    paragraph = "paragraph"
    code_block = "code_block"
    math_block = "math_block"
    image = "image"
    bullet_list = "bullet_list"
    ordered_list = "ordered_list"
    list_item = "list_item"
    blockquote = "blockquote"
    table = "table"
    table_row = "table_row"
    table_cell = "table_cell"
    thematic_break = "thematic_break"
    html_block = "html_block"


class TableAlign(str, Enum):
    left = "left"
    center = "center"
    right = "right"


class Block(BaseModel):
    type: BlockType = BlockType.paragraph
    level: int = 0
    content: str = ""
    info: str = ""
    lang: str = ""
    children: List[Block] = []
    inlines: List[InlineNode] = []
    rows: List[List[List[InlineNode]]] = []
    aligns: List[TableAlign] = []
    ordered: bool = False
    start: int = 1
    tight: bool = False
    meta: dict = {}


class Document(BaseModel):
    blocks: List[Block] = []
    metadata: dict = {}
    doc_type: Optional[DocumentType] = None
    source_text: str = ""


DOCUMENT_AST_VERSION = "1.0.0"