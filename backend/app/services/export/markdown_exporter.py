from typing import Optional, Dict
from .asset_manager import AssetManager
from app.services.parser import MarkdownParser, render_document


class MarkdownExporter:
    def __init__(self):
        self.asset_manager = AssetManager()

    def _image_to_base64_data_uri(self, src: str) -> str:
        if src.startswith("data:image/"):
            return src
        if src.startswith("/"):
            full_path = self.asset_manager.base_path / src.lstrip("/")
        else:
            full_path = self.asset_manager.base_path / src
        if full_path.exists():
            return self.asset_manager.image_to_base64(str(full_path))
        return src

    def _process_images(self, content: str, doc_id: str, embed_images: bool = True) -> str:
        if not embed_images:
            return content

        import re

        md_img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = list(re.finditer(md_img_pattern, content))

        for match in matches:
            alt_text = match.group(1)
            src = match.group(2)
            if src.startswith("data:image/"):
                continue
            new_src = self._image_to_base64_data_uri(src)
            if new_src != src:
                content = content.replace(match.group(0), f"![{alt_text}]({new_src})")

        return content

    async def export(self, original_text: str, translated_text: str, doc_id: str,
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True, **kwargs) -> Dict[str, str]:
        lines = []

        parser = MarkdownParser()

        if include_original:
            original_rendered = render_document(parser.parse(original_text))
            original_processed = self._process_images(original_rendered, doc_id, embed_images)
            lines.append("# Original")
            lines.append("")
            lines.append(original_processed)

        if include_translation:
            if include_original:
                lines.append("")
            translated_rendered = render_document(parser.parse(translated_text))
            translated_processed = self._process_images(translated_rendered, doc_id, embed_images)
            lines.append("# Translation")
            lines.append("")
            lines.append(translated_processed)

        content = "\n".join(lines)
        self.asset_manager.clear_cache()

        return {
            "content": content,
            "mime": "text/markdown; charset=utf-8",
            "extension": ".md"
        }