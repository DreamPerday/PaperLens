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
        img_tags = []
        def save_img(m):
            idx = len(img_tags)
            img_tags.append(m.group(0))
            return f"__IMG_{idx}__"
        content = re.sub(r'<img[^>]+>', save_img, content, flags=re.IGNORECASE)
        content = re.sub(r'<[^>]+>', '', content)
        for idx, tag in enumerate(img_tags):
            content = content.replace(f"__IMG_{idx}__", tag)
        return content
    
    def _add_formatted_paragraph(self, doc, text):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        p.paragraph_format.line_spacing = Pt(18)
        self._add_formatted_runs(p, text, doc)
        return p
    
    def _add_formatted_runs(self, p, text, doc=None):
        inline_pattern = re.compile(
            r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([\s\S]*?\\\)|(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$)|'
            r'!\[([^\]]*)\]\(([^)]+)\)|'
            r'\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`|__([^_]+)__)'
        )
        
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
                        if doc:
                            doc.add_picture(img_stream, width=Inches(4))
                    else:
                        if src.startswith("/"):
                            full_path = self.asset_manager.base_path / src.lstrip("/")
                        else:
                            full_path = self.asset_manager.base_path / src
                        if full_path.exists() and doc:
                            doc.add_picture(str(full_path), width=Inches(4))
                except Exception:
                    pass
            
            elif matched.startswith("**") and matched.endswith("**"):
                inner = groups[4]
                run = p.add_run(inner)
                run.bold = True
                run.font.size = Pt(12)
            
            elif matched.startswith("*") and matched.endswith("*") and not matched.startswith("**"):
                inner = groups[5]
                if inner:
                    run = p.add_run(inner)
                    run.italic = True
                    run.font.size = Pt(12)
            
            elif matched.startswith("`"):
                inner = groups[6]
                run = p.add_run(inner)
                run.font.name = "Consolas"
                run.font.size = Pt(10)
            
            elif matched.startswith("__") and matched.endswith("__"):
                inner = groups[7]
                run = p.add_run(inner)
                run.underline = True
                run.font.size = Pt(12)
            
            last_end = match.end()
        
        if last_end < len(text):
            run = p.add_run(text[last_end:])
            run.font.size = Pt(12)
        
        return p
    
    def _parse_content(self, content, doc, doc_id):
        content = re.sub(
            r'<img[^>]+src="([^"]+)"[^>]*\/?>',
            r'![](\1)',
            content,
            flags=re.IGNORECASE
        )
        content = re.sub(r'<[^>]+>', '', content)
        lines = content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith("\\[") or line.startswith("$$"):
                closer = "\\]" if line.startswith("\\[") else "$$"
                if line.endswith(closer):
                    inner = line[len(closer):-len(closer)].strip() if closer == "$$" else line[2:-2].strip()
                else:
                    inner_lines = []
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith(closer):
                        inner_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        last_line = lines[i].strip()
                        inner_lines.append(last_line[:-len(closer)])
                    inner = "\n".join(inner_lines).strip()
                p = doc.add_paragraph()
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(12)
                run = p.add_run(f"[ {inner} ]")
                run.font.size = Pt(12)
                run.font.italic = True
                i += 1
                continue
            
            if line.startswith("\\(") or (line.startswith("$") and not line.startswith("$$")):
                if line.startswith("\\("):
                    closer = "\\)"
                    if line.endswith(closer):
                        inner = line[2:-2].strip()
                        p = doc.add_paragraph()
                        run = p.add_run(f"({inner})")
                        run.font.size = Pt(12)
                        run.font.italic = True
                elif line.startswith("$"):
                    if line.endswith("$") and not line.endswith("$$"):
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
                self._add_formatted_runs(p, line[2:], doc)
                i += 1
                continue
            
            if line.startswith("- ") or line.startswith("* "):
                p = doc.add_paragraph(style="List Bullet")
                self._add_formatted_runs(p, line[2:], doc)
                i += 1
                continue
            
            if line.startswith("1. ") or line.startswith("1) "):
                p = doc.add_paragraph(style="List Number")
                self._add_formatted_runs(p, line[3:], doc)
                i += 1
                continue
            
            md_img_match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if md_img_match and not re.search(r'[a-zA-Z\u4e00-\u9fff]', line[:md_img_match.start()].strip()) and not re.search(r'[a-zA-Z\u4e00-\u9fff]', line[md_img_match.end():].strip()):
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
