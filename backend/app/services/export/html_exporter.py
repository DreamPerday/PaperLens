from typing import Dict, Optional, Tuple, List
from .asset_manager import AssetManager
from .template_manager import TemplateManager
import markdown as md_lib
import re

class HTMLExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
        self.template_manager = TemplateManager()
    
    def _protect_math(self, content: str) -> Tuple[str, List[str]]:
        math_pattern = r'(\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([^)]+\\\)|\$[^$\n]+\$)'
        math_blocks = []
        def replace_match(match):
            idx = len(math_blocks)
            math_blocks.append(match.group(1))
            return f"@@MATH_{idx}@@"
        protected = re.sub(math_pattern, replace_match, content)
        return protected, math_blocks
    
    def _restore_math_html(self, content: str, math_blocks: List[str]) -> str:
        for idx, block in enumerate(math_blocks):
            if block.startswith("$$"):
                inner = block[2:-2].strip()
                html_block = f'<div class="math-block">\\[{inner}\\]</div>'
            elif block.startswith("\\["):
                inner = block[2:-2].strip()
                html_block = f'<div class="math-block">\\[{inner}\\]</div>'
            elif block.startswith("\\("):
                inner = block[2:-2].strip()
                html_block = f'<span class="math-inline">\\({inner}\\)</span>'
            else:
                inner = block[1:-1].strip()
                html_block = f'<span class="math-inline">\\({inner}\\)</span>'
            content = content.replace(f"@@MATH_{idx}@@", html_block)
        return content
    
    def _markdown_to_html(self, content: str) -> str:
        protected, math_blocks = self._protect_math(content)
        md_extensions = ['extra', 'codehilite', 'sane_lists', 'tables']
        html = md_lib.markdown(protected, extensions=md_extensions)
        html = re.sub(r'<h(\d+)>', r'<h\1 class="keep-with-next">', html)
        html = self._restore_math_html(html, math_blocks)
        return html
    
    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, theme: str = "academic", page_size: str = "A4",
                    font_size: int = 12, include_toc: bool = False, watermark: Optional[str] = None,
                    watermark_pos: str = "bottom", cover_page: bool = False, subtitle: str = "",
                    watermark_tiled: bool = False, **kwargs) -> Dict[str, str]:
        
        if embed_images:
            original_text = await self.asset_manager.embed_images(original_text, doc_id)
            self.asset_manager.clear_cache()
            translated_text = await self.asset_manager.embed_images(translated_text, doc_id)
        
        original_html = self._markdown_to_html(original_text) if original_text else ""
        translated_html = self._markdown_to_html(translated_text) if translated_text else ""
        
        toc_content = self._generate_toc(original_html + translated_html) if include_toc else ""
        
        template_name = f"{theme}.html"
        content = self.template_manager.render(
            template_name,
            title=title,
            subtitle=subtitle,
            original_content=original_html,
            translated_content=translated_html,
            include_original=include_original,
            include_translation=include_translation,
            page_size=page_size,
            font_size=font_size,
            include_toc=include_toc,
            toc=toc_content,
            watermark=watermark,
            watermark_pos=watermark_pos,
            cover_page=cover_page,
            watermark_tiled=watermark_tiled
        )
        
        self.asset_manager.clear_cache()
        
        return {
            "content": content,
            "mime": "text/html; charset=utf-8",
            "extension": ".html"
        }
    
    def _generate_toc(self, content: str) -> str:
        toc_items = []
        heading_pattern = r'<h([1-3])[^>]*>([^<]+)</h[1-3]>'
        
        for match in re.finditer(heading_pattern, content):
            level = int(match.group(1))
            text = match.group(2).strip()
            anchor = text.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
            toc_items.append((level, text, anchor))
        
        toc_html = '<ul>'
        current_level = 1
        for level, text, anchor in toc_items:
            while level > current_level:
                toc_html += '<ul>'
                current_level += 1
            while level < current_level:
                toc_html += '</ul></li>'
                current_level -= 1
            toc_html += f'<li><a href="#{anchor}">{text}</a>'
        
        while current_level > 0:
            toc_html += '</ul>'
            current_level -= 1
        
        return toc_html
