import re
from typing import Optional, Dict
from .asset_manager import AssetManager

class MarkdownExporter:
    def __init__(self):
        self.asset_manager = AssetManager()
    
    def _protect_math(self, content: str) -> str:
        math_pattern = r'(\$\$[\s\S]*?\$\$|\$[^$]+\$)'
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
    
    def _process_images(self, content: str, doc_id: str, embed_images: bool = True) -> str:
        if not embed_images:
            return content
        
        img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        matches = list(re.finditer(img_pattern, content))
        
        for match in matches:
            alt_text = match.group(1)
            src = match.group(2)
            
            if src.startswith("data:image/"):
                continue
            
            if src.startswith("/"):
                full_path = self.asset_manager.static_dir / src.lstrip("/")
            else:
                full_path = self.asset_manager.static_dir / "images" / doc_id / src
            
            if full_path.exists():
                base64_data = self.asset_manager.image_to_base64(str(full_path))
                content = content.replace(match.group(0), f"![{alt_text}]({base64_data})")
        
        return content
    
    async def export(self, original_text: str, translated_text: str, doc_id: str, 
                    include_original: bool = True, include_translation: bool = True,
                    embed_images: bool = True) -> Dict[str, str]:
        lines = []
        
        if include_original:
            original_protected, math_blocks = self._protect_math(original_text)
            original_processed = self._process_images(original_protected, doc_id, embed_images)
            original_final = self._restore_math(original_processed, math_blocks)
            lines.append("# Original")
            lines.append("")
            lines.append(original_final)
        
        if include_translation:
            if include_original:
                lines.append("")
            translated_protected, math_blocks = self._protect_math(translated_text)
            translated_processed = self._process_images(translated_protected, doc_id, embed_images)
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
