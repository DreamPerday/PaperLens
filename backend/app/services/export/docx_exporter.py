from io import BytesIO
from typing import Dict, Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from .asset_manager import AssetManager
from app.services.parser import MarkdownParser, DocxRenderer


class DOCXExporter:
    def __init__(self):
        self.asset_manager = AssetManager()

    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True, **kwargs) -> Dict[str, bytes]:

        doc = Document()

        section = doc.sections[0]
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)

        style = doc.styles['Normal']
        font = style.font
        font.name = 'Times New Roman'
        font.size = Pt(12)

        if title:
            title_para = doc.add_paragraph(title)
            title_para.runs[0].font.size = Pt(16)
            title_para.runs[0].font.bold = True
            title_para.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            title_para.paragraph_format.space_after = Pt(12)

        docx_renderer = DocxRenderer(asset_base_path=self.asset_manager.base_path)
        parser = MarkdownParser()

        if include_original:
            heading = doc.add_heading("Original", level=1)
            heading.runs[0].font.size = Pt(12)
            heading.runs[0].font.bold = True
            heading.paragraph_format.space_after = Pt(6)
            ast_doc = parser.parse(original_text)
            for block in ast_doc.blocks:
                docx_renderer._render_block_to_docx(doc, block)

        if include_translation:
            if include_original:
                doc.add_page_break()
            heading = doc.add_heading("Translation", level=1)
            heading.runs[0].font.size = Pt(12)
            heading.runs[0].font.bold = True
            heading.paragraph_format.space_after = Pt(6)
            ast_doc = parser.parse(translated_text)
            for block in ast_doc.blocks:
                docx_renderer._render_block_to_docx(doc, block)

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return {
            "content": buffer.read(),
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "extension": ".docx"
        }