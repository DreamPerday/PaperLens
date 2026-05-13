from io import BytesIO
from typing import Dict, Optional
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_LINE_SPACING
from docx.enum.section import WD_ORIENT
from .asset_manager import AssetManager
import re

class DOCXExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
    
    def _add_heading(self, doc, text, level):
        heading = doc.add_heading(text, level=level)
        heading.runs[0].font.size = Pt(12 + (4 - level) * 2)
        heading.runs[0].font.bold = True
        heading.paragraph_format.space_after = Pt(6)
    
    def _add_image(self, doc, image_path, doc_id):
        from docx.shared import Inches
        try:
            if image_path.startswith("data:image/") or image_path.startswith("data:"):
                import base64
                data = image_path.split(",")[1]
                img_bytes = base64.b64decode(data)
                img_stream = BytesIO(img_bytes)
                doc.add_picture(img_stream, width=Inches(4))
            else:
                if image_path.startswith("/"):
                    full_path = self.asset_manager.base_path / image_path.lstrip("/")
                else:
                    full_path = self.asset_manager.base_path / image_path
                if full_path.exists():
                    doc.add_picture(str(full_path), width=Inches(4))
        except Exception:
            pass
    
    def _strip_html(self, content: str) -> str:
        return re.sub(r'<[^>]+>', '', content)
    
    def _add_formatted_paragraph(self, doc, text):
        inline_pattern = re.compile(
            r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|\$[^$]+\$|'
            r'!\[([^\]]*)\]\(([^)]+)\)|<img[^>]+src="([^"]+)"[^>]*\/?>|'
            r'\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|__([^_]+)__)'
        )
        
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p.paragraph_format.line_spacing = Pt(18)
        
        last_end = 0
        for match in inline_pattern.finditer(text):
            start = match.start()
            if start > last_end:
                run = p.add_run(text[last_end:start])
                run.font.size = Pt(12)
            
            groups = match.groups()
            matched = match.group(0)
            
            if matched.startswith("\\[") or matched.startswith("$$"):
                inner = matched[2:-2].strip() if matched.startswith("\\[") else matched[2:-2].strip()
                run = p.add_run(f"  [{inner}]  ")
                run.font.size = Pt(12)
                run.font.italic = True
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            
            elif matched.startswith("\\(") or (matched.startswith("$") and not matched.startswith("$$")):
                inner = matched[2:-2].strip() if matched.startswith("\\(") else matched[1:-1].strip()
                run = p.add_run(f"({inner})")
                run.font.size = Pt(12)
                run.font.italic = True
            
            elif matched.startswith("!["):
                from docx.shared import Inches
                src = match.group(3)
                try:
                    if src.startswith("data:"):
                        import base64
                        img_data = src.split(",")[1]
                        img_stream = BytesIO(base64.b64decode(img_data))
                        doc.add_picture(img_stream, width=Inches(4))
                    else:
                        if src.startswith("/"):
                            full_path = self.asset_manager.base_path / src.lstrip("/")
                        else:
                            full_path = self.asset_manager.base_path / src
                        if full_path.exists():
                            doc.add_picture(str(full_path), width=Inches(4))
                except Exception:
                    pass
            
            elif matched.startswith("<img"):
                img_match = re.search(r'src="([^"]+)"', matched)
                if img_match:
                    src = img_match.group(1)
                    try:
                        if src.startswith("data:"):
                            import base64
                            img_data = src.split(",")[1]
                            img_stream = BytesIO(base64.b64decode(img_data))
                            doc.add_picture(img_stream, width=Inches(4))
                        else:
                            if src.startswith("/"):
                                full_path = self.asset_manager.base_path / src.lstrip("/")
                            else:
                                full_path = self.asset_manager.base_path / src
                            if full_path.exists():
                                doc.add_picture(str(full_path), width=Inches(4))
                    except Exception:
                        pass
            
            elif matched.startswith("**") and matched.endswith("**"):
                inner = groups[5]
                run = p.add_run(inner)
                run.bold = True
                run.font.size = Pt(12)
            
            elif matched.startswith("*") and matched.endswith("*") and not matched.startswith("**"):
                inner = groups[6]
                if inner:
                    run = p.add_run(inner)
                    run.italic = True
                    run.font.size = Pt(12)
            
            elif matched.startswith("`"):
                inner = groups[7]
                run = p.add_run(inner)
                run.font.name = "Consolas"
                run.font.size = Pt(10)
            
            elif matched.startswith("__") and matched.endswith("__"):
                inner = groups[8]
                run = p.add_run(inner)
                run.underline = True
                run.font.size = Pt(12)
            
            last_end = match.end()
        
        if last_end < len(text):
            run = p.add_run(text[last_end:])
            run.font.size = Pt(12)
        
        return p
    
    def _parse_content(self, content, doc, doc_id):
        content = self._strip_html(content)
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("\\[") and line.endswith("\\]"):
                math_content = line[2:-2].strip()
                p = doc.add_paragraph()
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(12)
                run = p.add_run(f"[ {math_content} ]")
                run.font.size = Pt(12)
                run.font.italic = True
                i += 1
                continue
            
            if (line.startswith("$$") and line.endswith("$$")):
                math_content = line[2:-2].strip()
                p = doc.add_paragraph()
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(12)
                run = p.add_run(f"[ {math_content} ]")
                run.font.size = Pt(12)
                run.font.italic = True
                i += 1
                continue
            
            if (line.startswith("\\(") and line.endswith("\\)")) or (line.startswith("$") and line.endswith("$")):
                if line.startswith("\\("):
                    inner = line[2:-2].strip()
                else:
                    inner = line[1:-1].strip()
                p = doc.add_paragraph()
                run = p.add_run(f"({inner})")
                run.font.size = Pt(12)
                run.font.italic = True
                i += 1
                continue
            
            if line.startswith("# "):
                self._add_heading(doc, line[2:], level=1)
                i += 1
                continue
            
            if line.startswith("## "):
                self._add_heading(doc, line[3:], level=2)
                i += 1
                continue
            
            if line.startswith("### "):
                self._add_heading(doc, line[4:], level=3)
                i += 1
                continue
            
            if line.startswith("```"):
                code_block = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_block.append(lines[i])
                    i += 1
                i += 1
                code_text = "\n".join(code_block)
                p = doc.add_paragraph(code_text)
                p.style = "No Spacing"
                for run in p.runs:
                    run.font.name = "Consolas"
                    run.font.size = Pt(10)
                continue
            
            if line.startswith("> "):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.5)
                p.style = "Quote"
                run = p.add_run(line[2:])
                run.font.size = Pt(12)
                i += 1
                continue
            
            if line.startswith("- ") or line.startswith("* "):
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(line[2:])
                run.font.size = Pt(12)
                i += 1
                continue
            
            if line.startswith("1. ") or line.startswith("1) "):
                p = doc.add_paragraph(style="List Number")
                run = p.add_run(line[3:])
                run.font.size = Pt(12)
                i += 1
                continue
            
            html_img_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*\/?>', line)
            if html_img_match:
                self._add_image(doc, html_img_match.group(1), doc_id)
                i += 1
                continue
            
            md_img_match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if md_img_match:
                self._add_image(doc, md_img_match.group(2), doc_id)
                i += 1
                continue
            
            if line:
                self._add_formatted_paragraph(doc, line)
            i += 1
    
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
        
        if include_original:
            self._add_heading(doc, "Original", level=1)
            self._parse_content(original_text, doc, doc_id)
        
        if include_translation:
            if include_original:
                doc.add_page_break()
            self._add_heading(doc, "Translation", level=1)
            self._parse_content(translated_text, doc, doc_id)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return {
            "content": buffer.read(),
            "mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "extension": ".docx"
        }
