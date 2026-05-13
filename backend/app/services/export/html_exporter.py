from typing import Dict, Optional
from .asset_manager import AssetManager
from .template_manager import TemplateManager

class HTMLExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
        self.template_manager = TemplateManager()
    
    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, theme: str = "academic", page_size: str = "A4",
                    font_size: int = 12, include_toc: bool = False, watermark: Optional[str] = None) -> Dict[str, str]:
        
        if embed_images:
            original_text = await self.asset_manager.embed_images(original_text, doc_id)
            translated_text = await self.asset_manager.embed_images(translated_text, doc_id)
        
        toc_content = self._generate_toc(original_text + translated_text) if include_toc else ""
        
        template_name = f"{theme}.html"
        content = self.template_manager.render(
            template_name,
            title=title,
            original_content=original_text,
            translated_content=translated_text,
            include_original=include_original,
            include_translation=include_translation,
            page_size=page_size,
            font_size=font_size,
            include_toc=include_toc,
            toc=toc_content,
            watermark=watermark
        )
        
        self.asset_manager.clear_cache()
        
        return {
            "content": content,
            "mime": "text/html; charset=utf-8",
            "extension": ".html"
        }
    
    def _generate_toc(self, content: str) -> str:
        import re
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
