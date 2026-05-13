from typing import Dict, Optional, Tuple, List
from .asset_manager import AssetManager
from .template_manager import TemplateManager
from app.services.parser import MarkdownParser, render_to_html


class HTMLExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
        self.template_manager = TemplateManager()

    def _generate_toc(self, content: str) -> str:
        toc_items = []
        heading_pattern = r'<h([1-3])[^>]*>([^<]+)</h[1-3]>'

        for match in __import__('re').finditer(heading_pattern, content):
            level = int(match.group(1))
            text = match.group(2).strip()
            anchor = __import__('re').sub(r'[^a-z0-9-]', '', text.lower().replace(" ", "-"))
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

    async def export(self, original_text: str, translated_text: str, doc_id: str, title: str = "Translation",
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, theme: str = "academic", page_size: str = "A4",
                    font_size: int = 12, include_toc: bool = False, watermark: Optional[str] = None,
                    watermark_pos: str = "bottom", cover_page: bool = False, subtitle: str = "",
                    watermark_tiled: bool = False, **kwargs) -> Dict[str, str]:

        if embed_images:
            original_text = await self.asset_manager.embed_images(original_text, doc_id)
            self.asset_manager.clear_processed_only()
            translated_text = await self.asset_manager.embed_images(translated_text, doc_id)

        parser = MarkdownParser()

        original_html = ""
        if original_text:
            ast_doc = parser.parse(original_text)
            original_html = render_to_html(ast_doc)

        translated_html = ""
        if translated_text:
            ast_doc = parser.parse(translated_text)
            translated_html = render_to_html(ast_doc)

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