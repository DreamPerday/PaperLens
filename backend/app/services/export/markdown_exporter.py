import re
from typing import Optional, Dict
from .asset_manager import AssetManager

class MarkdownExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
    
    def _protect_math(self, content: str):
        math_pattern = r'(\\begin\{[^}]*\}[\s\S]*?\\end\{[^}]*\}|\\\[[\s\S]*?\\\]|\$\$[\s\S]*?\$\$|\\\([\s\S]*?\\\)|(?<!\$)\$(?!\$)[^$]+(?<!\$)\$(?!\$))'
        math_blocks = []
        
        def replace_match(match):
            idx = len(math_blocks)
            math_blocks.append(match.group(1))
            return f"__MATH_BLOCK_{idx}__"
        
        protected = re.sub(math_pattern, replace_match, content)
        return protected, math_blocks
    
    def _restore_math(self, content: str, math_blocks: list) -> str:
        for idx, block in enumerate(math_blocks):
            content = content.replace(f"__MATH_BLOCK_{idx}__", block)
        return content
    
    def _strip_html_tags(self, content: str) -> str:
        content = re.sub(r'<pre[^>]*>(.*?)</pre>', r'\n```\n\1\n```\n', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', content, flags=re.IGNORECASE)
        content = re.sub(r'<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>', r'**\1**', content, flags=re.IGNORECASE)
        content = re.sub(r'<(?:em|i)[^>]*>(.*?)</(?:em|i)>', r'*\1*', content, flags=re.IGNORECASE)
        content = re.sub(r'<(/?(?:p|div|span|h\d|ul|ol|li|table|tr|td|th|tbody|thead|section|article|header|footer|main|nav|aside|figure|figcaption|strong|em|b|i|u|s|sub|sup|code|pre|blockquote|dd|dt|dl|a|form|input|button|label|select|option|textarea|fieldset|legend)[^>]*)>', '', content)
        return content
    
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
        
        # Process <img> tags (from original HTML content)
        def replace_html_img(match):
            src = match.group(2)
            alt = match.group(3) or ""
            new_src = self._image_to_base64_data_uri(src)
            return f"![{alt}]({new_src})"

        html_img_pattern = r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"[^>]*\/?>|<img[^>]*alt="([^"]*)"[^>]*src="([^"]+)"[^>]*\/?>|<img[^>]*src="([^"]+)"[^>]*\/?>'
        def replace_any_html_img(match):
            groups = match.groups()
            if groups[0] is not None:
                src = groups[0]
                alt = groups[1] or ""
            elif groups[3] is not None:
                src = groups[3]
                alt = groups[2] or ""
            else:
                src = groups[4]
                alt = ""
            new_src = self._image_to_base64_data_uri(src)
            return f"![{alt}]({new_src})"
        
        content = re.sub(html_img_pattern, replace_any_html_img, content)
        
        # Process markdown ![]() images (from enriched translation)
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
        
        if include_original:
            original_protected, math_blocks = self._protect_math(original_text)
            original_stripped = self._strip_html_tags(original_protected)
            original_processed = self._process_images(original_stripped, doc_id, embed_images)
            original_final = self._restore_math(original_processed, math_blocks)
            lines.append("# Original")
            lines.append("")
            lines.append(original_final)
        
        if include_translation:
            if include_original:
                lines.append("")
            translated_protected, math_blocks = self._protect_math(translated_text)
            translated_stripped = self._strip_html_tags(translated_protected)
            translated_processed = self._process_images(translated_stripped, doc_id, embed_images)
            translated_final = self._restore_math(translated_processed, math_blocks)
            lines.append("# Translation")
            lines.append("")
            lines.append(translated_final)
        
        content = "\n".join(lines)
        self.asset_manager.clear_cache()
        
        return {
            "content": content,
            "mime": "text/markdown; charset=utf-8",
            "extension": ".md"
        }